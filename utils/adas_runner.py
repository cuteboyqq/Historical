import os
import sys
import time
from utils.display import DisplayUtils

class AdasRunner():
    def __init__(self, connection_handler, config):
        """Initialize the AdasRunner.

        Args:
            connection_handler: Handler for remote connections.
            config: Configuration object containing ADAS settings.
        """
        self.display = DisplayUtils()
        self.adas_start_script = config.remote_adas_script_path
        self.adas_stop_cmd = "killall -9 cardv && killall -9 bootconfig/bin/cardv"

        self.remote_config_path = config.remote_adas_config_path
        self.backup_config_path = config.backup_adas_config_path
        self.img_format = config.image_format
        self.remote_role = "Device"
        self.connect = connection_handler

    def run_adas(self):
        """Execute the ADAS startup process on the remote device.

        Returns:
            bool: True if ADAS started successfully, False otherwise.
        """
        # Get the initial PID of cardv process
        initial_pid = self.connect.remote_ssh.execute_command("ps | grep cardv | grep -v grep | awk '{print $1}'").strip()
        if len(initial_pid) == 0:
            self.display.show_message(self.remote_role, f"No cardv is running")
        else:
            initial_pid = initial_pid.split()[0]
            self.display.show_message(self.remote_role, f"Initial cardv PID: \033[1;37;42m {initial_pid} \033[0m")

        self.display.show_message(self.remote_role, "Starting ADAS...")

        import threading
        def run_adas_command():
            cmd = f"cd / && {self.adas_start_script}"
            self.connect.remote_ssh.execute_command(cmd)

        # Create and start a new thread to run the ADAS command
        adas_thread = threading.Thread(target=run_adas_command)
        adas_thread.start()

        # Wait for the script to complete
        max_wait_time = 20  # Maximum wait time in seconds
        start_time = time.time()

        while True:
            # Continuously check for new cardv PID
            current_pid = self.connect.remote_ssh.execute_command("ps | grep cardv | grep -v grep | awk '{print $1}'").strip()
            if len(current_pid) == 0:
                self.display.print_progress(f"⚠️ Initialize ADAS...")
                continue
            else:
                current_pid = current_pid.split()[0]

            # If PID is different, end the loop
            if current_pid != initial_pid:
                self.display.show_message(self.remote_role, f"New cardv process started with PID: \033[1;37;42m {current_pid} \033[0m")
                self.connect.remote_ssh.execute_command("echo adas status 1 > /tmp/cardv_fifo")

                # Countdown before starting ADAS
                for i in range(3, 0, -1):
                    self.display.print_progress(f"🚀 Starting ADAS in {i} seconds...")
                    time.sleep(1)
                print()
                break


            if time.time() - start_time > max_wait_time:
                self.display.show_message(self.remote_role, "Timeout: ADAS failed to start within the expected time.")
                return False

            time.sleep(1)

        adas_thread.join(timeout=5)
        print()
        self.display.show_status(self.remote_role, "ADAS startup process", True)
        return True

    def stop_adas(self):
        """Stop the ADAS process on the remote device.

        Returns:
            bool: True if ADAS was stopped successfully, False otherwise.
        """
        try:
            stop_command = f"{self.adas_stop_cmd}"
            self.connect.remote_ssh.execute_command(stop_command)
            self.display.show_status(self.remote_role, "Stop ADAS", True)
            return True
        except Exception as e:
            self.display.show_status(self.remote_role, "Stop ADAS", False)
            return False

    def modify_remote_config(self,
                            input_mode="0",
                            enable_visualize=False,
                            enable_save_raw_images=False,
                            enable_show_debug_profiling=False,
                            server_ip=None,
                            server_port=None):
        """Modifies the config file on the remote device.

        This method backs up the original config, modifies it with new settings,
        and writes it back to the remote device.

        Args:
            enable_visualize (bool): Whether to enable visualization mode.
            enable_save_raw_images (bool): Whether to enable saving raw images.

        Returns:
            bool: True if the modification is successful, False otherwise.
        """
        try:
            # First, backup the original config
            self.connect.remote_ssh.execute_command(f"cp {self.remote_config_path} {self.backup_config_path}")

            # Read the current config
            config_content = self._get_remote_config()
            if not config_content:
                return False

            # Modify the config
            new_lines = []
            for line in config_content.splitlines():
                if line.startswith("InputMode"):
                    line = f"InputMode = 0"
                elif line.startswith("VisualizeMode"):
                    if input_mode == "0":   # Live mode
                        line = f"VisualizeMode = {0 if enable_visualize else 2}"
                    elif input_mode == "2": # Historical mode
                        line = f"VisualizeMode = {0 if enable_visualize else 2}"
                elif line.startswith("DebugSaveRawImages"):
                    line = f"DebugSaveRawImages = {1 if enable_save_raw_images else 0}"
                elif line.startswith("ShowDebugProfiling"):
                    line = f"ShowDebugProfiling = {1 if enable_show_debug_profiling else 0}"
                elif line.startswith("ServerIP") and server_ip:
                    line = f"ServerIP = {server_ip}"
                elif line.startswith("ServerPort") and server_port:
                    line = f"ServerPort = {server_port}"
                new_lines.append(line)

            # Write the modified config back to the remote device
            modified_content = "\n".join(new_lines)
            self.connect.put_file(self.remote_config_path, modified_content)

            self.display.show_status(self.remote_role, "Modify remote ADAS config", True)
            return True
        except Exception as e:
            self.display.show_status(self.remote_role, "Modify remote ADAS config", False)
            return False

    def _get_remote_config(self):
        """Retrieves the config file from the remote device.

        Returns:
            str: The content of the remote config file, or None if retrieval fails.
        """
        try:
            content = self.connect.get_file(self.remote_config_path)
            self.display.show_status(self.remote_role, "Read remote ADAS config", True)
            return content
        except Exception as e:
            self.display.show_status(self.remote_role, "Read remote ADAS config", False)
            return None

    def _restore_remote_config(self):
        """Restores the backed-up config file on the remote device.

        Returns:
            bool: True if the restoration is successful, False otherwise.
        """
        try:
            self.connect.remote_ssh.execute_command(f"mv {self.backup_config_path} {self.remote_config_path}")
            self.display.show_status(self.remote_role, "Restore remote ADAS config", True)
            return True
        except Exception as e:
            self.display.show_status(self.remote_role, "Restore remote ADAS config", False)
            return False
