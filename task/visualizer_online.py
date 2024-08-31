import os
import sys
import time
import signal
# from visualize_tools.visualizer import Visualizer
from task.visualizer import Visualizer
from utils.adas_runner import AdasRunner
from utils.socket import RemoteSocket
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

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
        self.remote_img_root = config.camera_rawimages_dir

        # Initialize Server IP and port
        self.server_ip = config.server_ip
        self.server_port = config.server_port

        self.config =config

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

        # is_in_use, pid, process_name = self.check_local_port_in_use(self.server_port)

        # if is_in_use:
        #     print(f"⚠️ Port {self.server_port} is in use by process '{process_name}' with PID {pid}.")
        #     # Kill the process if you want
        #     kill_result = self.kill_local_process(pid)
        #     print(kill_result)
        #     if self.config.visualize_mode == "online" and self.config.device_mode == 'live':
        #         recv_data_keys = ["frame_index", "image", "log"]
        #     elif self.config.visualize_mode == "online" and self.config.device_mode == 'historical':
        #         recv_data_keys = ["frame_index", "image", "image_path", "log"]
        #     else:
        #         recv_data_keys = ["log"]
        #     self.connect.remote_socket = RemoteSocket(
        #     server_ip=self.connect.server_ip,
        #     server_port=self.connect.server_port,
        #     recv_data_keys=recv_data_keys)
        # else:
        #     print(f"✅ Port {self.server_port} is available.")



        if self.re_start_adas:
            # Stop ADAS
            if not self.adas_runner.stop_adas():
                self.display.show_status(self.role, "Failed to stop ADAS", False)
                return False


        # 🚀 Check if the server port is in use and get process details if so
        is_in_use, pid, process_name = self.connect.check_process_using_port(self.connect.server_port)
        is_in_use_1st = is_in_use
        logging.info(f"✅ Port :{self.connect.server_port} is in use :{is_in_use}")
        while is_in_use:
            logging.info(f"⚠️ Port {self.connect.server_port} is in use by process {process_name} with PID {pid}.")
            # If in use, kill the process remotely via SSH
            kill_result = self.connect.kill_process_remotely(pid)
            logging.info(f"🛑 Kill result: {kill_result}")
            
            # Increment port number to check the next one
            # self.connect.port += 1
            self.connect.server_port += 1
            self.server_port += 1

            # Check the new port status
            is_in_use, pid, process_name = self.connect.check_process_using_port(self.connect.server_port)

        logging.info(f"✅ Port {self.connect.server_port} is available.")

        # if self.connect.setup():
        #     logging.info(f"✅ connect is_setup_success is success")
        # else:
        #     logging.info(f"🛑 connect is_setup_success is failed")
        if is_in_use_1st:
            if self.config.visualize_mode == "online" and self.config.device_mode == 'live':
                recv_data_keys = ["frame_index", "image", "log"]
            elif self.config.visualize_mode == "online" and self.config.device_mode == 'historical':
                recv_data_keys = ["frame_index", "image", "image_path", "log"]
            else:
                recv_data_keys = ["log"]

        
            self.connect.remote_socket = RemoteSocket(
                server_ip=self.connect.server_ip,
                server_port=self.connect.server_port,
                recv_data_keys=recv_data_keys)

        # Modify remote config
        input_mode = '0' if self.config.device_mode == 'live' else '2'

        if self.re_start_adas or self.config.device_mode == 'historical' or is_in_use_1st:
            if self.config.device_mode == 'historical':
                img_folder_path_for_historical_mode = self._select_remote_image_folder()
            else:
                img_folder_path_for_historical_mode = None

         
            if not self.adas_runner.modify_remote_config(
                input_mode=input_mode,
                image_folder_path_for_historical_mode=img_folder_path_for_historical_mode,
                enable_visualize=True,
                server_ip=self.connect.server_ip,
                server_port=self.connect.server_port):
                self.display.show_status(self.role, "Failed to modify remote config", False)
                return False

        # Start the server to receive data
        self.connect.start_server() 
        

        if self.re_start_adas or self.config.device_mode == 'historical': # or is_in_use_1st:
            # Run remote ADAS script
            if not self.adas_runner.run_adas():
                self.display.show_status(self.role, "Failed to run remote ADAS script", False)
                return False

        # if self.re_start_adas or self.config.device_mode == 'historical':
        #     # Wait for the server to be ready
        #     while not self.connect.server_is_ready() and not self.stop:
        #         self.display.print_progress(f"🔌 Socket server is listening for Go-Focus...")
        #     print('\n')
        try:
            # Continuously receive and process data while the server is running
            while self.connect.server_is_running() and not self.stop:
                if self.config.device_mode == 'live':
                    self._receive_image_and_log(self.connect.get_data())
                else:
                    self._receive_image_and_log_and_image_path(self.connect.get_data())
        except Exception as e:
            self.display.show_status(self.role, f"Data reception: {str(e)}", False)
        # finally:
        #     # Ensure the remote config is restored even if an exception occurs
        #     if not self.adas_runner.modify_remote_config(
        #         input_mode='0',
        #         enable_visualize=False,
        #         server_ip=self.server_ip,
        #         server_port=self.server_port):
        #         self.display.show_status(self.role, "Failed to modify remote config", False)
        #         return False

        # Stop the server
        self.connect.stop_server()
        return True

    def _select_remote_image_folder(self):
        """
        Select a folder to download from the remote path.

        Returns:
            str: The name of the selected folder.
        """
        try:
            # List all folders in the remote path
            stdin, stdout, stderr = self.connect.remote_ssh.client.exec_command(f'ls -d {self.remote_img_root}/*/')
            folders = stdout.read().decode().strip().split('\n')

            # Extract folder names from full paths
            folder_names = [os.path.basename(folder.rstrip('/')) for folder in folders]

            if not folder_names:
                self.display.show_warning(self.role, "No folders found in the remote path.")
                return None

            return self._select_folder(folder_names, "remote")

        except Exception as e:
            self.display.show_status(self.role, f"Error selecting remote folder: {str(e)}", False)
            return None

    def _select_folder(self, folder_names, location):
        """
        Helper method to select a folder from a list.

        Args:
            folder_names (list): List of folder names to choose from.
            location (str): 'remote' or 'local' to indicate the folder location.

        Returns:
            str: The name of the selected folder.
        """
        # Display available folders
        self.display.print_header(f"Available {location} folders:")
        for i, folder in enumerate(folder_names, 1):
            print(f"{i}. {folder}")

        # Ask user to select a folder
        while True:
            try:
                choice = int(input(f"\nEnter the number of the {location} folder you want to select: "))
                if 1 <= choice <= len(folder_names):
                    selected_folder = folder_names[choice - 1]
                    self.display.show_status(self.role, f"Selected {location} folder: {selected_folder}", True)
                    return selected_folder
                else:
                    self.display.show_warning(self.role, "Invalid choice. Please try again.")
            except ValueError:
                self.display.show_warning(self.role, "Invalid input. Please enter a number.")

    def _signal_handler(self, signum, frame):
        """
        Handle interrupt signals to gracefully shut down the server.

        Args:
            signum (int): The signal number.
            frame (frame): The current stack frame.
        """
        print("\nReceived interrupt signal. Shutting down...")
        self.stop = True