import sys
import time
import signal
from visualize_tools.visualizer import Visualizer
from utils.adas_runner import AdasRunner

class VisualizerOnline(Visualizer):
    def __init__(self, connection, config):
        """Initialize the VisualizerOnline.

        Args:
            config: Configuration object containing necessary parameters.
        """
        # Initialize the parent Visualizer class
        super().__init__(connection, config)

        # Initialize AdasRunner
        self.adas_runner = AdasRunner(connection, config)

        # Remote paths for ADAS script and configurations
        self.remote_adas_script_path = config.remote_adas_script_path
        self.remote_config_path = config.remote_adas_config_path
        self.backup_config_path = config.backup_adas_config_path

        # Initialize Server IP and port
        self.server_ip = config.server_ip
        self.server_port = config.server_port

        # Signal handling
        self.stop = False
        signal.signal(signal.SIGINT, self._signal_handler)  # Register SIGINT handler

    def run(self):
        """Run the VisualizerOnline.

        This method orchestrates the entire process of establishing a connection,
        modifying remote configurations, running the remote ADAS script, and
        handling the data reception.

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
            enable_visualize=True,
            server_ip=self.server_ip,
            server_port=self.server_port):
            self.display.show_status(self.role, "Failed to modify remote config", False)
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
            while self.connect.server_is_running() and not self.stop:
                self._receive_image_and_log(self.connect.get_data())
        except Exception as e:
            self.display.show_status(self.role, f"Data reception: {str(e)}", False)
        finally:
            # Ensure the remote config is restored even if an exception occurs
            if not self.adas_runner.modify_remote_config(
                enable_visualize=False,
                server_ip=self.server_ip,
                server_port=self.server_port):
                self.display.show_status(self.role, "Failed to modify remote config", False)
                return False

        # Stop the server
        self.connect.stop_server()
        return True

    def _signal_handler(self, signum, frame):
        """
        Handle interrupt signals to gracefully shut down the server.

        Args:
            signum (int): The signal number.
            frame (frame): The current stack frame.
        """
        print("\nReceived interrupt signal. Shutting down...")
        self.stop = True