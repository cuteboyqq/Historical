# from config.config import get_connection_args
from tqdm import tqdm
import paramiko
import time
import subprocess
from scp import SCPClient
import os
import re
import json
import cv2
import pandas as pd
import logging
import socket
from engine.BaseDataset import BaseDataset
from utils.drawer import Drawer
from utils.saver import ImageSaver
import threading
import numpy as np
import queue
import psutil
global index
index  = 0
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



class SOCKET:
    def __init__(self,args):
        """
        Initialize the SOCKET class with configuration details.

        Args:
            tftp_ip (str): The IP address for the TFTP server.
            server_port (int): The port to listen on for incoming connections.
            im_dir (str): Directory to save received images.
            image_basename (str): Base name for the saved image files.
            image_format (str): Format of the saved image files.
            Drawer: An instance of a class that processes JSON logs.
        """
        self.tftp_ip = args.tftp_ip
        self.server_port = args.server_port
        self.save_rawimages = args.save_rawimages
        self.im_dir = args.im_dir
        os.makedirs(self.im_dir,exist_ok=True)
        self.image_basename = args.image_basename
        self.image_format = args.image_format
        self.Drawer = Drawer(args)
        self.saver = ImageSaver(args)
        self.stop_server = threading.Event()
        # Data management
        self.data_queue = queue.Queue()  # Queue to store received data

    def receive_frame_index(self, client_socket):
        frame_index_data = client_socket.recv(4)
        if not frame_index_data:
            logging.error("❌ Failed to receive frame index.")
            raise ValueError("Failed to receive frame index.")
        return int.from_bytes(frame_index_data, byteorder='big')


    def receive_image_size(self, client_socket):
        size_data = client_socket.recv(4)
        if not size_data:
            logging.error("❌ Failed to receive image size.")
            raise ValueError("Failed to receive image size.")
        return int.from_bytes(size_data, byteorder='big')


    def receive_image_data(self, client_socket, size):
        buffer = b''
        while len(buffer) < size:
            data = client_socket.recv(min(size - len(buffer), 4096))
            if not data:
                break
            buffer += data
        if len(buffer) != size:
            logging.error(f"❌ Failed to receive the complete image data. Received {len(buffer)} bytes out of {size}")
            raise ValueError("Failed to receive complete image data.")
        return buffer


    def save_image(self, image_data, frame_index):
        image_path = f'{self.im_dir}/{self.image_basename}{frame_index}.{self.image_format}'
        with open(image_path, 'wb') as file:
            file.write(image_data)
        # logging.info(f"💾 Image saved at {image_path}")


    def receive_image_path_length(self, client_socket):
        path_length_data = client_socket.recv(4)
        if not path_length_data:
            logging.error("❌ Failed to receive image path length.")
            raise ValueError("Failed to receive image path length.")
        return int.from_bytes(path_length_data, byteorder='big')


    def receive_image_path(self, client_socket, path_length):
        path_data = self.receive_fixed_size_data(client_socket, path_length)
        return path_data.decode('utf-8')


    def receive_json_log(self, client_socket):
        json_data = b''
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            json_data += data
            if b'\r\n\r\n' in data:
                break
        return json_data.decode('utf-8')


    def receive_fixed_size_data(self, client_socket, size):
        buffer = b''
        while len(buffer) < size:
            data = client_socket.recv(min(size - len(buffer), 4096))
            if not data:
                break
            buffer += data
        if len(buffer) != size:
            raise ValueError("Failed to receive the complete fixed-size data.")
        return buffer
    

    def receive_image_and_log(self, client_socket, draw_jsonlog, custom_directory=None):
        try:
            frame_index = self.receive_frame_index(client_socket)
            size = self.receive_image_size(client_socket)
            buffer = self.receive_image_data(client_socket, size)
            if self.save_rawimages:
                self.save_image(buffer, frame_index)
            np_arr = np.frombuffer(buffer, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image from buffer.")
            json_data = self.receive_json_log(client_socket)
            self.Drawer.process_json_log(json_data, image)
        except Exception as e:
            logging.error(f"❌ Error: {e} - An unexpected error occurred.")

    # def receive_image_and_log(self, client_socket, draw_jsonlog, custom_directory=None):
    #     recv_data = {
    #         'frame_index': None,
    #         'image': None,
    #         'log': None
    #     }
    #     try:
    #         recv_data['frame_index'] = self.receive_frame_index(client_socket)
    #         size = self.receive_image_size(client_socket)
    #         recv_data['image'] = self.receive_image_data(client_socket, size)
    #         if self.save_rawimages:
    #             self.save_image(recv_data['image'], recv_data['frame_index'])
    #         np_arr = np.frombuffer(recv_data['image'], np.uint8)
    #         image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    #         if image is None:
    #             raise ValueError("Failed to decode image from buffer.")
    #         recv_data['log'] = self.receive_json_log(client_socket)
    #         # self.Drawer.process_json_log(recv_data['log'], image)
    #         return recv_data
    #     except Exception as e:
    #         logging.error(f"❌ Error: {e} - An unexpected error occurred.")


    def receive_image_and_log_and_imgpath(self, client_socket):
        try:
            frame_index = self.receive_frame_index(client_socket)
            size = self.receive_image_size(client_socket)
            buffer = self.receive_image_data(client_socket, size)
            if self.save_rawimages:
                self.save_image(buffer, frame_index)
            np_arr = np.frombuffer(buffer, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image from buffer.")
            path_length = self.receive_image_path_length(client_socket)
            image_path = self.receive_image_path(client_socket, path_length)
            json_data = self.receive_json_log(client_socket)
            self.Drawer.process_json_log(json_data, image, image_path)
            # logging.info("✅ JSON log processed successfully")
        except Exception as e:
            logging.error(f"❌ Error: {e} - An unexpected error occurred.")


    def _create_server_socket(self):
        """
        Create and return a server socket instance.

        Returns:
            socket.socket: The server socket ready for binding.

        Raises:
            RuntimeError: If there is an error creating the server socket.
        """
        try:
            # Create a server socket instance
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set socket options to reuse address
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Return the server socket
            return server_socket

        except socket.error as e:
            # Log the error and raise an exception
            logging.error(f"❌ Socket error: {e}")
            raise RuntimeError(f"Failed to create server socket: {e}")

        except Exception as e:
            # Log any other unexpected errors
            logging.error(f"❌ Unexpected error: {e}")
            raise RuntimeError(f"Failed to create server socket: {e}")



    def _bind_server_socket(self, server_socket):
        """
        Bind the server socket to the specified IP address and port.

        Args:
            server_socket (socket.socket): The server socket to bind.

        Raises:
            PermissionError: If there is a permission issue with binding.
            Exception: For other binding errors.
        """
        try:
            server_socket.bind((self.tftp_ip, self.server_port))
        except PermissionError as e:
            logging.error(f"❌ PermissionError: {e} - You may need root privileges to use this port.")
            raise
        except Exception as e:
            logging.error(f"⚠️ Error: {e} - Could not bind to {self.tftp_ip}:{self.server_port}.")
            raise


    def _receive_json_data(self, client_socket):
        """
        Receive JSON log data from a client socket.

        Args:
            client_socket (socket.socket): The client socket to receive data from.

        Returns:
            str: The received JSON data.
        """
        json_data = b''
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            json_data += data
            if b'\r\n\r\n' in data:
                break

        return json_data


    def _process_json_data(self, json_data, addr, draw_jsonlog=True, save_folder=None):
        """
        Process received JSON data.

        Args:
            json_data (bytes): The received JSON data.
            addr (tuple): The address of the client that sent the data.

        Raises:
            UnicodeDecodeError: If decoding JSON data fails.
            Exception: For other processing errors.
        """
        try:
            json_data = json_data.decode('utf-8')
            # logging.info(f"📥 Received JSON data {json_data}")
            if draw_jsonlog:
                self.Drawer.process_json_log(json_data)

            # logging.info(f"save_folder:{save_folder}")
            if save_folder is not None:
                current_directory = os.getcwd()
                # logging.info(f"📁 Current Directory: {current_directory}")
                save_jsonlog_dir = f"{current_directory}/runs/{save_folder}"
                os.makedirs(save_jsonlog_dir, exist_ok=True)
                file_path = os.path.join(save_jsonlog_dir,f"{save_folder}.txt")
                json_data = json.loads(json_data)
                with open(file_path, 'a') as file:
                    json.dump(json_data, file)
                    file.write("\n")  # Add a newline after each JSON log entry for separation
                # logging.info(f"✅ Successfully processed data from {addr}")
        except UnicodeDecodeError as e:
            logging.error(f"❌ UnicodeDecodeError: {e} - Raw data: {json_data}")
        except Exception as e:
            logging.error(f"⚠️ Error: {e} - Failed to process data from {addr}")



    def _receive_client_data(self, client_socket, mode, custom_directory):
        """
        Handle data reception from the client based on the mode.

        Args:
            client_socket (socket.socket): The client socket to receive data from.
            mode (str): The mode of the server ('🔴 Live Mode' or '📚 Historical Mode').
            custom_directory: Custom directory to save the received data.

        Raises:
            Exception: For issues during data reception.
        """
        try:
            if mode == '🔴 Live Mode':
                self.receive_image_and_log(client_socket, custom_directory)
            elif mode == '📚 Historical Mode':
                self.receive_image_and_log_and_imgpath(client_socket)
        except Exception as e:
            logging.error(f"❌ Error: {e} - Failed to process data from client.")



    def _handle_client_connection(self, client_socket, draw_jsonlog, save_folder, device_mode, visual_mode, custom_directory=None):
        """
        Handle an incoming client connection based on the mode.

        Args:
            client_socket (socket.socket): The client socket to handle.
            mode (str): The operating mode of the server ('json', 'image_log', 'image_log_path').
            custom_directory (str): Custom directory for saving data, if applicable.
        """
        if visual_mode == 'semi-online':
            json_data = self._receive_json_data(client_socket)
            self._process_json_data(json_data, None, draw_jsonlog, save_folder,)
        elif visual_mode == 'online' and device_mode == 0: # Device live mode
            self.receive_image_and_log(client_socket, draw_jsonlog, custom_directory=None)
        elif visual_mode == 'online' and device_mode == 2: # Device historical mode
            self.receive_image_and_log_and_imgpath(client_socket)
        else:
            logging.error(f"⚠️ Unknown visual_mode: {visual_mode} & device_mode:{device_mode}")

    # def _handle_client_connection(self, client_socket, draw_jsonlog, save_folder, device_mode, visual_mode, custom_directory=None):
    #     """
    #     Handle an incoming client connection based on the mode.

    #     Args:
    #         client_socket (socket.socket): The client socket to handle.
    #         mode (str): The operating mode of the server ('json', 'image_log', 'image_log_path').
    #         custom_directory (str): Custom directory for saving data, if applicable.
    #     """
    #     if visual_mode == 'semi-online':
    #         json_data = self._receive_json_data(client_socket)
    #         self._process_json_data(json_data, None, draw_jsonlog, save_folder,)
    #     elif visual_mode == 'online' and device_mode == 0: # Device live mode
    #         recv_data = self.receive_image_and_log(client_socket, draw_jsonlog, custom_directory=None)
    #         self.data_queue.put(recv_data)
    #     elif visual_mode == 'online' and device_mode == 2: # Device historical mode
    #         self.receive_image_and_log_and_imgpath(client_socket)
    #     else:
    #         logging.error(f"⚠️ Unknown visual_mode: {visual_mode} & device_mode:{device_mode}")


  
class SSH:
    def __init__(self, args):
        """
        Initialize the SSH class with connection details.

        Args:
            host_name (str): The hostname or IP address of the remote server.
            port (int): The port to connect to on the remote server.
            user_name (str): The username for authentication.
            password (str): The password for authentication.
        """
        self.host_name = args.camera_host_name
        self.port = args.camera_port
        self.user_name = args.camera_user_name
        self.password = args.camera_password

    def _create_ssh_client(self):
        """
        Create and return an SSH client instance.

        Returns:
            paramiko.SSHClient: An SSH client connected to the server.
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host_name, self.port, self.user_name, self.password)
        logging.info(f"🚀 Connected to IP:{self.host_name} port:{self.port} user:{self.user_name} password:{self.password}")
        return ssh

    def execute_remote_command_with_progress_ver3(self, command):
        """
        Execute a remote command via SSH and monitor its progress.

        Args:
            command (str): The command to be executed on the remote server.

        Returns:
            str: The complete output from the command.
        """
        try:
            ssh = self._create_ssh_client()

            # Execute the command with a timeout
            stdin, stdout, stderr = ssh.exec_command(command, timeout=10)  # Set an appropriate timeout
            logging.info(f"✅ Finished executing command: {command}")

            final_output = []
            final_errors = []

            # Continuously check if the command has finished
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.readline().strip()  # No need to decode
                    final_output.append(line)
                
                if stderr.channel.recv_ready():
                    error_line = stderr.readline().strip()  # No need to decode
                    final_errors.append(error_line)
                
                time.sleep(0.1)  # Prevent high CPU usage

            # Read remaining output and errors after command execution
            stdout_data = stdout.read().strip()  # No need to decode
            stderr_data = stderr.read().strip()  # No need to decode

            if stdout_data:
                final_output.append(stdout_data)
            if stderr_data:
                final_errors.append(stderr_data)

            # Log final outputs and errors
            if final_errors:
                logging.error(f"❌ Final Errors: {''.join(final_errors)}")
            if final_output:
                logging.info(f"🚀 Final Output: {''.join(final_output)}")

            return ''.join(final_output).strip() if final_output else None

        except paramiko.ssh_exception.AuthenticationException as auth_err:
            logging.error(f"❌ Authentication failed: {auth_err}")
            return None
        except paramiko.ssh_exception.SSHException as ssh_err:
            logging.error(f"❌ SSH error: {ssh_err}")
            return None
        except Exception as e:
            logging.error(f"❌ An error occurred: {e}")
            return None
        finally:
            ssh.close()

    def execute_remote_command_with_progress_ver2(self, command):
        """
        Execute a remote command via SSH and monitor its progress.

        Args:
            command (str): The command to be executed on the remote server.

        Returns:
            str: The complete output from the command.
        """
        try:
            ssh = self._create_ssh_client()

            # Execute the command with a timeout
            stdin, stdout, stderr = ssh.exec_command(command, timeout=10)  # Set an appropriate timeout
            logging.info(f"✅ Finished executing command: {command}")

            final_output = []
            final_errors = []

            # Continuously check if the command has finished
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.readline().decode('utf-8').strip()
                    final_output.append(line)
                
                if stderr.channel.recv_ready():
                    error_line = stderr.readline().decode('utf-8').strip()
                    final_errors.append(error_line)
                
                time.sleep(0.1)  # Prevent high CPU usage

            # Read remaining output and errors after command execution
            stdout_data = stdout.read().decode('utf-8').strip()
            stderr_data = stderr.read().decode('utf-8').strip()

            if stdout_data:
                final_output.append(stdout_data)
            if stderr_data:
                final_errors.append(stderr_data)

            # Log final outputs and errors
            if final_errors:
                logging.error(f"❌ Final Errors: {''.join(final_errors)}")
            if final_output:
                logging.info(f"🚀 Final Output: {''.join(final_output)}")

            return ''.join(final_output).strip() if final_output else None

        except paramiko.ssh_exception.AuthenticationException as auth_err:
            logging.error(f"❌ Authentication failed: {auth_err}")
            return None
        except paramiko.ssh_exception.SSHException as ssh_err:
            logging.error(f"❌ SSH error: {ssh_err}")
            return None
        except Exception as e:
            logging.error(f"❌ An error occurred: {e}")
            return None
        finally:
            ssh.close()

    # def execute_remote_command_with_progress(self, command):
    #     """
    #     Execute a remote command via SSH and monitor its progress.

    #     Args:
    #         command (str): The command to be executed on the remote server.

    #     This method provides simulated progress feedback and logs output and errors.
    #     """
    #     try:
    #         ssh = paramiko.SSHClient()
    #         ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #         logging.info(f'hostname: {self.host_name}')
    #         logging.info(f'port: {self.port}')
    #         logging.info(f'username: {self.user_name}')
    #         logging.info(f'password: {self.password}')
    #         ssh.connect(self.host_name, self.port, self.user_name, self.password)
    #         print(f"Connected to {self.host_name}")

    #         # Execute the command
    #         stdin, stdout, stderr = ssh.exec_command(command)

    #         # Simulate progress (use file size or an estimate if possible)
    #         file_size = 100  # Replace with actual file size or an estimated number of steps
    #         with tqdm(total=file_size, desc="Processing", unit="B", dynamic_ncols=True) as pbar:
    #             while not stdout.channel.exit_status_ready():
    #                 line = stdout.readline().strip()
    #                 if line:
    #                     logging.info(f"Output: {line}")  # Log each line (if any) from the command
    #                     pbar.update(1)  # Simulated update - replace with logic based on actual progress
    #                 time.sleep(1)

    #             # Read final output and errors
    #             final_output = stdout.read().decode().strip()
    #             final_errors = stderr.read().decode().strip()
    #             logging.info(f"Final Output: {final_output}")
    #             logging.error(f"Final Errors: {final_errors}")

    #         ssh.close()
    #     except paramiko.ssh_exception.AuthenticationException as auth_err:
    #         logging.error(f"Authentication failed: {auth_err}")
    #     except paramiko.ssh_exception.SSHException as ssh_err:
    #         logging.error(f"SSH error: {ssh_err}")
    #     except Exception as e:
    #         logging.error(f"An error occurred: {e}")

    def execute_remote_command_with_progress(self, command):
        """
        Execute a remote command via SSH and monitor its progress.

        Args:
            command (str): The command to be executed on the remote server.

        This method provides real-time progress feedback and logs output and errors.
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logging.info(f'hostname:{self.host_name}')
            logging.info(f'port:{self.port}')
            logging.info(f'username:{self.user_name}')
            logging.info(f'password:{self.password}')
            ssh.connect(self.host_name, self.port, self.user_name, self.password)
            print(f"Connected to {self.host_name}")

            # Execute the command
            stdin, stdout, stderr = ssh.exec_command(command)

            # Initialize progress bar
            with tqdm(total=100, desc="Processing", unit="%", dynamic_ncols=True) as pbar:
                while not stdout.channel.exit_status_ready():
                    line = stdout.readline().strip()
                    if line:
                        pbar.set_description(f"Progress: {line}")
                        pbar.update(1)
                    time.sleep(1) 
              
                final_output = stdout.read().strip()
                final_errors = stderr.read().strip()
                logging.info(f"Final Output: {final_output}")
                logging.error(f"Final Errors: {final_errors}")

            ssh.close()
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
            logging.error(f"❌ An error occurred: {e}")
            logging.error("Output:")
            logging.error(e.stdout.decode())
            logging.error("Errors:")
            logging.error(e.stderr.decode())


    def run_the_adas(self):
        """
        Execute the ADAS script and manage process cleanup.
        """
        remote_command = self._construct_run_adas_command()
        
        try:
            output = self.execute_remote_command_with_progress(remote_command)
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌ An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")


    def _construct_run_adas_command(self):
        """
        Construct the ADAS execution command.

        Returns:
            str: The command to execute ADAS.
        """
        return (
            "cd / && "
            # "ps -a | grep run_script | awk '{print $1}' | xargs -r kill -9 && "  # Optional: Kill existing processes
            "cd /customer && "
            "./run_adas"
        )


    

class Connection(BaseDataset):

    def __init__(self, args):
        """
        Initialize the Connection object.

        Args:
            args: Arguments containing connection details and configuration.
        """
        super().__init__(args)
        # Camera setting
        self.camera_rawimages_dir = args.camera_rawimages_dir
        self.camera_csvfile_dir = args.camera_csvfile_dir
        self.camera_host_name = args.camera_host_name
        self.camera_port = args.camera_port
        self.camera_user_name = args.camera_user_name
        self.camera_password = args.camera_password
        self.camera_config_dir = args.camera_config_dir

        self.tftpserver_dir = args.tftpserver_dir
        self.server_port = args.server_port
        self.stop_server_flag = threading.Event()
        self.server_socket = None
        self.stop_event = threading.Event()
        self.stop_server = threading.Event()
        self.display_parameters()
        self.remote_csv_file_path = args.remote_csv_file_path
        # self.Drawer = Drawer(args)

        # Alister add 2024-08-24
        self.SSH = SSH(args)
        self.SOCKET = SOCKET(args)

    def display_parameters(self):
        """
        Log parameters for the connection configuration.
        
        This method extends the base class method to include specific details for the Connection class.
        """
        logging.info("🎯 Connection Class Information 🎯")
        logging.info(f"📦 Class Name: {self.__class__.__name__}")
        logging.info(f"📝 Documentation: {self.__class__.__doc__}")
        logging.info(f"🔧 Module: {self.__module__}")
        logging.info(f"💡 Base Class: {self.__class__.__bases__}")
        logging.info("\n" + "="*40)
        
        logging.info("🔌 Connection Configuration:")
        logging.info("="*40)
        logging.info(f"📷 CAMERA SETTINGS")
        logging.info(f"   📂 Raw Images Directory: {self.camera_rawimages_dir}")
        logging.info(f"   📂 CSV File Directory: {self.camera_csvfile_dir}")
        logging.info(f"   🌐 Hostname: {self.camera_host_name}")
        logging.info(f"   🚪 Port: {self.camera_port}")
        logging.info(f"   👤 Username: {self.camera_user_name}")
        logging.info(f"   🔑 Password: {self.camera_password}")
        logging.info(f"   🛠️  Config Directory: {self.camera_config_dir}")
        logging.info("="*40)
        
        logging.info(f"💾 TFTP SERVER")
        logging.info(f"   📂 Directory: {self.tftpserver_dir}")
        logging.info(f"   🚪 Port: {self.server_port}")
        logging.info("="*40 + "\n")


    def start_server(self, draw_jsonlog = False, save_folder=None, visual_mode='online', custom_directory=None):
        """
        Start the TCP server with configurable handling modes.

        Args:
            mode (str): The visual_mode of operation ('online', 'semi-online').
            custom_directory (str): Custom directory for saving data, if applicable.
        """

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((self.tftp_ip, self.server_port))
        except PermissionError as e:
            logging.error(f"❌ PermissionError: {e} - Server cannot bind to {self.server_port}")
            return
        except Exception as e:
            logging.error(f"❌ Error: {e} - Server failed to start on {self.tftp_ip}:{self.server_port}")
            return

        device_input_mode = self.check_device_input_mode()
        if device_input_mode == 0:
            mode = '🔴 Live Mode'
        else:
            mode = '📚 Historical Mode'

        logging.info(f"🔍 Device LI80 input mode is {device_input_mode} : {mode}")
        server_socket.listen(5)
        logging.info(f"🟢 Server started on {self.tftp_ip}:{self.server_port}")
        os.makedirs(f'{self.im_dir}', exist_ok=True)

        try:
           
            while not self.stop_server.is_set():  # Check if the stop signal is set
                try:
                    client_socket, addr = server_socket.accept()
                    # logging.info(f"🔗 Connection established with {addr}")
                    self.SOCKET._handle_client_connection(client_socket, draw_jsonlog, save_folder, device_input_mode, visual_mode, custom_directory)
                    client_socket.close()
                    # logging.info(f"🔒 Connection closed with {addr}")

                except socket.timeout:
                    continue  # Allow the loop to check for the stop signal
                except Exception as e:
                    logging.error(f"❌ Error in server loop: {e}")
                    break

        except Exception as e:
            logging.error(f"❌ Error: {e} - Server encountered an issue.")
        finally:
            server_socket.close()
            logging.info("🔒 Server socket closed.")
        
        print("🏁 ADAS visualization stopped")


    def check_device_input_mode(self):
        """
        Checks the value of InputMode in the device's /customer/adas/config/config.txt file and returns it.
        Adds emojis to the logging messages for better visual context.

        Returns:
            int: The value of InputMode (0 or 2). Returns -1 if InputMode is not found or an error occurs.
        """
        # Construct the command to read the InputMode value from the config file
        check_command = 'grep "^InputMode\s*=" /customer/adas/config/config.txt | awk -F "=" \'{print $2}\' | awk \'{print $1}\''

        try:
            # Execute the remote command
            result = self.SSH.execute_remote_command_with_progress_ver2(check_command)

            # Check if result is not None
            if result is not None:
                # Clean up the result by stripping extra spaces and newlines
                result = result.strip()
                # Log the raw result for debugging
                logging.info(f"📜 Raw result from remote command: '{result}'")

                # Check if the result is a valid InputMode value
                if result in ["0", "2"]:
                    input_mode = int(result)
                    logging.info(f"✅ InputMode value is {input_mode}.")
                    return input_mode
                else:
                    logging.warning(f"⚠️ InputMode value is neither 0 nor 2. Result: '{result}'")
                    return -1
            else:
                logging.error("❌ No result returned from remote command.")
                return -1

        except Exception as e:
            logging.error(f"🚨 Error executing remote command: {e}")
            return -1


    def check_process_using_port(self,port):
        """
        Check if a port is in use on the local machine and return the process using it.

        Args:
            port (int): The port number to check.

        Returns:
            tuple: A tuple containing a boolean indicating if the port is in use, the process ID (pid), and the process name.
        """
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                pid = conn.pid
                process_name = psutil.Process(pid).name()
                return (True, pid, process_name)  # Return tuple with details
        return (False, None, None)  # Port is available
    

    def kill_process_remotely(self, process_id):
        """
        Kill a process on a remote machine using SSH.

        Args:
            hostname (str): The IP or hostname of the remote machine.
            port (int): The SSH port number.
            username (str): The SSH username.
            password (str): The SSH password.
            process_id (int): The process ID to be killed.

        Returns:
            str: A message indicating the result of the kill command.
        """
        try:
            # Connect to the remote machine via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
            
            # Kill the process using the 'kill' command
            kill_command = f"kill -9 {process_id}"
            stdin, stdout, stderr = ssh.exec_command(kill_command)

            # Read the output and errors
            stdout_output = stdout.read().decode().strip()
            stderr_output = stderr.read().decode().strip()

            ssh.close()

            if stderr_output:
                return f"Error killing process: {stderr_output}"
            return f"Process {process_id} killed successfully."
        except paramiko.ssh_exception.AuthenticationException as auth_err:
            return f"Authentication failed: {auth_err}"
        except paramiko.ssh_exception.SSHException as ssh_err:
            return f"SSH error: {ssh_err}"
        except Exception as e:
            return f"An error occurred: {e}"
        

