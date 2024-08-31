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
        self.adas_stop_cmd = "killall -9 cardv"

        self.remote_config_path = config.remote_adas_config_path
        self.backup_config_path = config.backup_adas_config_path
        self.remote_img_root = config.camera_rawimages_dir
        self.img_format = config.image_format
        self.remote_role = "Device"
        self.connect = connection_handler

    def run_adas(self):
        """Execute the ADAS startup process on the remote device.

        Returns:
            bool: True if ADAS started successfully, False otherwise.
        """
        # Get the initial PID of cardv process
        initial_pid = self.connect.remote_ssh.execute_command("ps | grep /bootconfig/bin/cardv | grep -v grep | grep -v logger | awk '{print $1}'").strip()

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
            current_pid = self.connect.remote_ssh.execute_command("ps | grep /bootconfig/bin/cardv | grep -v grep | grep -v logger | awk '{print $1}'").strip()
            if len(current_pid) == 0:
                self.display.print_progress(f"⚠️ Initialize ADAS...")
                continue
            else:
                current_pid = current_pid.split()[0]
                print()

            # If PID is different, end the loop
            if current_pid != initial_pid:
                self.display.show_message(self.remote_role, f"New cardv process started with PID: \033[1;37;42m {current_pid} \033[0m")
                self.connect.remote_ssh.execute_command("echo adas status 1 > /tmp/cardv_fifo")

                # Countdown before starting ADAS
                for i in range(2, 0, -1):
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
                            image_folder_path_for_historical_mode=None,
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

            _input_mode = input_mode

            _visualize_mode = "2" # Disable visualization mode by default
            if input_mode == "0":
                _visualize_mode = "0" if enable_visualize else "2"
            elif input_mode == "2":
                _visualize_mode = "0" if enable_visualize else "2"

            _debug_save_raw_images = "0"
            if enable_save_raw_images:
                _debug_save_raw_images = "1"

            _show_debug_profiling = "0"
            if enable_show_debug_profiling:
                _show_debug_profiling = "1"

            _image_folder_path_for_historical_mode = ""
            if image_folder_path_for_historical_mode:
                _image_folder_path_for_historical_mode = image_folder_path_for_historical_mode

            _image_folder_path_for_historical_mode = f"{self.remote_img_root}/{_image_folder_path_for_historical_mode}"
            if os.name == 'nt':
                _image_folder_path_for_historical_mode.replace('\\', '/')

            _server_ip = "192.168.1.10"
            if server_ip:
                _server_ip = server_ip

            _server_port = "8080"
            if server_port:
                _server_port = server_port

            _start_frame = "0"
            _end_frame = "99999"

            config_file_path = self.remote_config_path

            commands = (
                f"sed -i 's/^InputMode = [0-9]*/InputMode = {_input_mode}/' {config_file_path} && "
                f"sed -i 's|^RawImageDir = .*|RawImageDir = {_image_folder_path_for_historical_mode}|' {config_file_path} && "
                f"sed -i 's/^ImageModeStartFrame = [0-9]*/ImageModeStartFrame = {_start_frame}/' {config_file_path} && "
                f"sed -i 's/^ImageModeEndFrame = [0-9]*/ImageModeEndFrame = {_end_frame}/' {config_file_path} && "
                f"sed -i 's/^ServerPort = [0-9]*/ServerPort = {_server_port}/' {config_file_path} && "
                f"sed -i 's/^ServerIP = .*/ServerIP = {_server_ip}/' {config_file_path} && "
                f"sed -i 's/^VisualizeMode = [0-2]*/VisualizeMode = {_visualize_mode}/' {config_file_path} && "
                f"sed -i 's/^DebugSaveRawImages = [0-1]*/DebugSaveRawImages = {_debug_save_raw_images}/' {config_file_path} && "
                f"sed -i 's/^ShowDebugProfiling = [0-1]*/ShowDebugProfiling = {_show_debug_profiling}/' {config_file_path}"
            )

            self.connect.remote_ssh.execute_command(commands)

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
        
    def check_port_availability(self, port):

        """Check if a port is available on the remote server."""
        command = f"lsof -i:{port}"
        print(f"command : {command}")
        stdin, stdout, stderr = self.connect.remote_ssh.execute_command(command)
        output = stdout.read().decode().strip()
        return len(output) == 0
