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
global index
index  = 0

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Connection(BaseDataset):

    def __init__(self, args):
        """
        Initialize the Connection object.

        Args:
            args: Arguments containing connection details and configuration.
        """
        super().__init__(args)
        self.hostname = args.host_name
        self.port = args.port
        self.username = args.user_name
        self.password = args.password
        self.tftpserver_dir = args.tftpserver_dir
        self.server_port = args.server_port
        self.display_parameters()

        self.Drawer = Drawer(args)

    def display_parameters(self):
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

    def start_server(self):
        """
        Start a TCP server to listen for incoming client connections.

        The server accepts connections, receives JSON log data, and processes it.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((self.tftp_ip, self.server_port))
        except PermissionError as e:
            logging.error(f"PermissionError: {e}")
            return
        except Exception as e:
            logging.error(f"Error: {e}")
            return

        server_socket.listen(5)
        logging.info(f"Server started on {self.tftp_ip}:{self.server_port}")

        while True:
            client_socket, addr = server_socket.accept()
            logging.info(f"Connection from {addr}")

            # Receive JSON log data
            json_data = b''
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                json_data += data
                if b'\r\n\r\n' in data:
                    break

            try:
                json_data = json_data.decode('utf-8')
                self.Drawer.process_json_log(json_data)
            except UnicodeDecodeError as e:
                logging.error(f"UnicodeDecodeError: {e} - Raw data: {json_data}")
            except Exception as e:
                logging.error(f"Error: {e}")

            client_socket.close()

    def start_server_ver2(self):
        """
        Start an improved version of the TCP server to handle image and JSON log reception.

        This method listens for incoming connections, receives image data and JSON logs,
        and saves the images locally.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((self.tftp_ip, self.server_port))
        except PermissionError as e:
            logging.info(f"PermissionError: {e}")
            return
        except Exception as e:
            logging.info(f"Error: {e}")
            return

        server_socket.listen(5)
        logging.info(f"Server started on {self.tftp_ip}:{self.server_port}")
        os.makedirs(f'{self.im_dir}', exist_ok=True)

        while True:
            client_socket, addr = server_socket.accept()
            logging.info(f"Connection from {addr}")
            self.receive_image_and_log(client_socket)
            client_socket.close()

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
            logging.info(f'hostname:{self.hostname}')
            logging.info(f'port:{self.port}')
            logging.info(f'username:{self.username}')
            logging.info(f'password:{self.password}')
            ssh.connect(self.hostname, self.port, self.username, self.password)
            print(f"Connected to {self.hostname}")

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
                # Print final output
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
            logging.error(f"An error occurred: {e}")
            logging.error("Output:")
            logging.error(e.stdout.decode())
            logging.error("Errors:")
            logging.error(e.stderr.decode())

    def receive_image_and_log(self, client_socket):
        """
        Receive image data and JSON logs from a client connection.

        Args:
            client_socket (socket.socket): The socket object for the client connection.

        This method processes and saves the received image and JSON log data.
        """
        try:
            # Receive the frame_index
            frame_index_data = client_socket.recv(4)
            if not frame_index_data:
                logging.error("Failed to receive frame index.")
                return

            frame_index = int.from_bytes(frame_index_data, byteorder='big')
            logging.info(f"Received frame index: {frame_index}")

            # Receive the size of the image
            size_data = client_socket.recv(4)
            if not size_data:
                logging.error("Failed to receive image size.")
                return

            size = int.from_bytes(size_data, byteorder='big')
            logging.info(f"Expected image size: {size} bytes")

            # Receive the image data
            buffer = b''
            while len(buffer) < size:
                data = client_socket.recv(min(size - len(buffer), 4096))
                if not data:
                    break
                buffer += data

            if len(buffer) != size:
                logging.error(f"Failed to receive the complete image data. Received {len(buffer)} bytes out of {size}")
                return

            logging.info(f"Successfully received the complete image data. Total bytes: {len(buffer)}")

            # Save the image to a file
            image_path = f'{self.im_dir}/{self.image_basename}{frame_index}.{self.image_format}'

            with open(image_path, 'wb') as file:
                file.write(buffer)

            # Read the remaining data for JSON log
            json_data = b''
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                json_data += data
                if b'\r\n\r\n' in data:
                    break

            json_data = json_data.decode('utf-8')

            # Process the JSON log
            self.Drawer.process_json_log(json_data)
           
        except Exception as e:
            logging.error(f"Error: {e} - An unexpected error occurred.")








    
    
            
