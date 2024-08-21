import os
import sys
import time
from visualize_tools.visualizer import Visualizer
from utils.adas_runner import AdasRunner

class VisualizerSemiOnline(Visualizer):
    def __init__(self, conntion, config):
        """Initialize the VisualizerSemiOnline.

        Args:
            config: Configuration object containing necessary parameters.
        """
        # Initialize the parent Visualizer class
        super().__init__(conntion, config)

        # Initialize AdasRunner
        self.adas_runner = AdasRunner(connection, config)

        # Remote paths for ADAS script and configurations
        self.remote_adas_script_path = config.remote_adas_script_path
        self.remote_config_path = config.remote_adas_config_path
        self.backup_config_path = config.backup_adas_config_path

        # Initialize connection handler as None (will be set up later)
        self.connect = None

        # Initialize Server IP and port
        self.server_ip = config.server_ip
        self.server_port = config.server_port

    def run(self):
        """Run the VisualizerSemiOnline.

        This method orchestrates the entire process of establishing a connection,
        modifying remote configurations, checking for remote images,
        running the remote ADAS script, and handling the data reception.

        Returns:
            bool: True if the process completes successfully, False otherwise.
        """
        self.display.print_header("Starting visualize execution...")

        # Stop ADAS
        if not self.adas_runner.stop_adas():
            self.display.show_status(self.role, "Failed to stop ADAS", False)
            return False

        # Modify remote config
        if not self.adas_runner.modify_remote_config(
            input_mode="2",
            enable_visualize=True,
            server_ip=self.server_ip,
            server_port=self.server_port):
            self.display.show_status(self.role, "Failed to modify remote config", False)
            return False

        # Check if remote images exist
        if not self._is_remote_image_exists():
            self.display.show_message(self.role, "No remote images found", False)
            return False

        # Run remote ADAS script
        if not self.adas_runner.run_adas():
            self.display.show_status(self.role, "Failed to run remote ADAS script", False)
            return False

        # Start the server to receive data
        self.connect.start_server()

        # Wait for the server to be ready
        while not self.connect.server_is_ready():
            self.display.print_progress(f"🔌 Socket server is listening for Go-Focus...")
        print('\n')

        try:
            # Continuously receive and process data while the server is running
            while self.connect.server_is_running():
                self._receive_log(self.connect.get_data())
        except Exception as e:
            self.display.show_message(self.role, f"Data reception: {str(e)}", False)
        finally:
            # Ensure the remote config is restored even if an exception occurs
            if not self.adas_runner.modify_remote_config(
                input_mode="0",
                enable_visualize=False,
                server_ip=self.server_ip,
                server_port=self.server_port):
                self.display.show_status(self.role, "Failed to modify remote config", False)
                return False

        # Stop the server
        self.connect.stop_server()
        return True

    def _is_remote_image_exists(self):
        """Check if image files exist in the remote device's specified directory.

        Returns:
            bool: True if .png files exist, False otherwise.
        """
        try:
            remote_image_dir = self.config.camera_rawimages_dir #TODO: better naming rule
            command = f"ls {remote_image_dir}*.png 2>/dev/null | wc -l"

            if os.name == 'nt':
                command = command.replace('\\', '/')

            result = self.connect.remote_ssh.execute_command(command)

            if result:
                file_count = int(result)
                return file_count > 0
            else:
                self.display.show_message(self.role, "Failed to check remote images", False)
                return False
        except Exception as e:
            self.display.show_message(self.role, f"Error checking remote images: {str(e)}", False)
            return False