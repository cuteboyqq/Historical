import sys
import time
import logging
import threading
from tqdm import tqdm
from utils.display import DisplayUtils
from utils.connections.remote_ssh import RemoteSSH
from utils.connections.remote_socket import RemoteSocket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectionHandler():

    def __init__(self, config):
        """
        Initialize the Connection object.
        """
        # Initialize the configuration object
        self.config = config

        #
        self.display = DisplayUtils()

        # Initialize the objects
        self.remote_ssh = RemoteSSH(
            hostname=config.camera_host_name,
            username=config.camera_user_name,
            password=config.camera_password,
            port=config.camera_port)

        self.remote_socket = None

        # Setup the checker objects
        self.is_setup = self.setup()

    def is_setup_success(self):
        return self.is_setup

    def setup(self):
        """Setup the connection.

        Returns:
            bool: True if the setup is successful, False otherwise
        """
        self.display.print_header("Starting device connection...")

        if not self.remote_ssh.connect():
            return False

        recv_data_keys = []
        if self.config.visualize_mode == "online" and self.config.device_mode=='live':
            recv_data_keys = ["frame_index", "image", "log"]
        elif self.config.visualize_mode == "online" and self.config.device_mode=='historical':
            recv_data_keys = ["frame_index", "image", "image_path", "log"]
        else:
            recv_data_keys = ["log"]

        self.remote_socket = RemoteSocket(
            server_ip=self.config.server_ip,
            server_port=self.config.server_port,
            recv_data_keys=recv_data_keys)

        return True

    def close_connection(self):
        self.remote_ssh.disconnect()

    def start_server(self):
        self.display.print_header("Starting socket connection...")

        start_server = False

        if not self.remote_socket.start_server():
            logging.error("Failed to start socket server")
        else:
            start_server = True

        return start_server

    def stop_server(self):
        self.remote_socket.stop_server()

    def server_is_ready(self):
        return self.remote_socket.is_ready()

    def server_is_running(self):
        return self.remote_socket.is_running()

    def get_data(self):
        return self.remote_socket.get_data()

    def get_file(self, remote_path):
        """
        Retrieves a file from the remote device.

        Args:
            remote_path (str): The path of the file on the remote device.

        Returns:
            str: The content of the file, or None if an error occurred.
        """
        try:
            command = f"cat {remote_path}"
            result = self.remote_ssh.execute_command(command)
            if result:
                return result
            else:
                return None
        except Exception as e:
            # logging.error(f"Error retrieving file from {remote_path}: {str(e)}")
            return None

    def put_file(self, remote_path, content):
        """
        Writes content to a file on the remote device.

        Args:
            remote_path (str): The path of the file on the remote device.
            content (str): The content to write to the file.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Use echo command to write content to file
            escaped_content = content.replace('"', '\\"')  # Escape double quotes
            command = f'echo "{escaped_content}" > {remote_path}'
            self.remote_ssh.execute_command(command)
            return True
        except Exception as e:
            return False

    def execute_remote_command_with_progress(self, command):
        """
        Execute a remote command via SSH and monitor its progress.

        Args:
            command (str): The command to be executed on the remote server.

        This method provides real-time progress feedback and logs output and errors.
        """
        try:
            # Execute the command
            stdin, stdout, stderr = self.remote_ssh.exec_command(command)

            # Initialize progress bar
            with tqdm(total=100, desc="Processing", unit="%", dynamic_ncols=True) as pbar:
                while not stdout.channel.exit_status_ready():
                    line = stdout.readline().strip()
                    if line:
                        pbar.set_description(f"Progress: {line}")
                        pbar.update(1)
                    time.sleep(1)
                # Print final output
                final_output = stdout.read().strip()
                final_errors = stderr.read().strip()
                logging.info(f"Final Output: {final_output}")
                logging.error(f"Final Errors: {final_errors}")

        except paramiko.ssh_exception.AuthenticationException as auth_err:
            logging.error(f"Authentication failed: {auth_err}")
        except paramiko.ssh_exception.SSHException as ssh_err:
            logging.error(f"SSH error: {ssh_err}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    def execute_local_command(self, command):
        """
        Execute a local command and log its output and errors.

        Args:
            command (str): The command to be executed locally.

        This method captures and logs the command's output and errors.
        """
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"Command executed: {command}")
            logging.info("Output:")
            logging.info(result.stdout.decode())
            logging.info("Errors:")
            logging.info(result.stderr.decode())
        except subprocess.CalledProcessError as e:
            logging.error(f"An error occurred: {e}")
            logging.error("Output:")
            logging.error(e.stdout.decode())
            logging.error("Errors:")
            logging.error(e.stderr.decode())

    def _display_parameters(self):
        """
        Log parameters for the connection configuration.

        This method extends the base class method to include specific details for the Connection class.
        """
        super().display_parameters()
        logging.info(f"HOSTNAME: {self.hostname}")
        logging.info(f"PORT: {self.port}")
        logging.info(f"USERNAME: {self.username}")
        logging.info(f"PASSWORD: {self.password}")
        logging.info(f"TFTP SERVER DIR: {self.tftpserver_dir}")
        logging.info(f"SERVER PORT: {self.server_port}")