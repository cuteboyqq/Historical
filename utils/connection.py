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
import threading
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
        self.Drawer = Drawer(args)

    def display_parameters(self):
        """
        Log parameters for the connection configuration.
        
        This method extends the base class method to include specific details for the Connection class.
        """
        # ASCII art for headers
        connection_art = """
        ____  _       ____  _   _  _____ _   _ _   _ ____  
        / ___|| |_   _| __ )| | | | |_ _| \ | | | | |  _ \ 
        \___ \| | | | |  _ \| | | |  | ||  \| | | | | |_) |
        ___) | | |_| | |_) | |_| |  | || |\  | |_| |  __/ 
        |____/|_|\__, |____/ \___/  |___|_| \_|\___/|_|    
                |___/                                    
        """
        camera_art = """
        ____                                     
        / ___| ___ _ __ ___  _   _ _ __ __ _ _ __  
        | |  _ / _ \ '__/ _ \| | | | '__/ _` | '_ \ 
        | |_| |  __/ | | (_) | |_| | | | (_| | | | |
        \____|\___|_|  \___/ \__,_|_|  \__,_|_| |_| 
        """
        tftp_art = """
        _____ _____ ____ _____  _____ ____  
        |_   _|_   _/ ___|_   _|/  ___/ ___| 
        | |   | || |     | | | |   \___ \ 
        | |   | || |___  | | | |___ ___) |
        |_|   |_| \____| |_|  \____|____/ 
        """

        print(connection_art)
        logging.info("🎯 Connection Class Information 🎯")
        logging.info(f"📦 Class Name: {self.__class__.__name__}")
        logging.info(f"📝 Documentation: {self.__class__.__doc__}")
        logging.info(f"🔧 Module: {self.__module__}")
        logging.info(f"💡 Base Class: {self.__class__.__bases__}")
        logging.info("\n" + "="*40)
        
        print(camera_art)
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
        
        print(tftp_art)
        logging.info(f"💾 TFTP SERVER")
        logging.info(f"   📂 Directory: {self.tftpserver_dir}")
        logging.info(f"   🚪 Port: {self.server_port}")
        logging.info("="*40 + "\n")



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
            logging.error(f"❌ PermissionError: {e} - You may need root privileges to use this port.")
            return
        except Exception as e:
            logging.error(f"⚠️ Error: {e} - Could not bind to {self.tftp_ip}:{self.server_port}.")
            return

        server_socket.listen(5)
        logging.info(f"✅ Server started and listening on {self.tftp_ip}:{self.server_port}")

        while True:
            client_socket, addr = server_socket.accept()
            logging.info(f"🔗 Connection established with {addr}")

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
                logging.info(f"📥 Received JSON data from {addr}")
                self.Drawer.process_json_log(json_data)
                logging.info(f"✅ Successfully processed data from {addr}")
            except UnicodeDecodeError as e:
                logging.error(f"❌ UnicodeDecodeError: {e} - Raw data: {json_data}")
            except Exception as e:
                logging.error(f"⚠️ Error: {e} - Failed to process data from {addr}")

            client_socket.close()
            logging.info(f"🔒 Connection closed with {addr}")



    def start_server_ver2(self,custom_directory=None):
        """
        Start an improved version of the TCP server to handle image and JSON log reception.
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
        
        # Run below will restart the info from frame_ID : 0
        # logging.info(f"🟢 ADAS started on...")
        # self.run_the_adas()

        while True:
            try:
                client_socket, addr = server_socket.accept()
                # logging.info(f"🌐 Connection from {addr}")
                if mode == '🔴 Live Mode':
                    self.receive_image_and_log(client_socket,custom_directory)
                elif mode == '📚 Historical Mode':
                    self.receive_image_and_log_and_imgpath(client_socket)
                client_socket.close()
            except socket.timeout:
                # Timeout exception allows the loop to periodically check the stop flag
                continue
            except Exception as e:
                logging.error(f"❌ Error: {e} - Server loop encountered an issue")

    def run_the_adas(self):
        """
        Execute the ADAS script and manage process cleanup.
        """
        try:
            remote_command = (
                f"cd / && "
                # "ps -a | grep run_script | awk '{print $1}' | xargs -r kill -9 && "  # Use -r to avoid xargs error if no process is found
                "cd /customer && "
                "./run_script"
            )
            
            output = self.execute_remote_command_with_progress_ver2(remote_command)
            
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")


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
            result = self.execute_remote_command_with_progress_ver2(check_command)

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



    def start_server_ver3(self, custom_directory=None):
        """
        Start the third version of the TCP server to handle image and JSON log reception.
        
        This version includes improved logging and graceful shutdown handling.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((self.tftp_ip, self.server_port))
            server_socket.listen(5)
            logging.info(f"🟢 Server started and listening on {self.tftp_ip}:{self.server_port}")
            os.makedirs(f'{self.im_dir}', exist_ok=True)
        except Exception as e:
            logging.error(f"❌ Server failed to start: {e}")
            return

        while not self.stop_server.is_set():  # Check if the stop signal is set
            try:
                client_socket, addr = server_socket.accept()
                # logging.info(f"🔗 Connection established with {addr}")

                self.receive_image_and_log_and_imgpath(client_socket)
                # logging.info(f"📥 Data received and processed from {addr}")

                client_socket.close()
                # logging.info(f"🔒 Connection closed with {addr}")
            except socket.timeout:
                continue  # Allow the loop to check for the stop signal
            except Exception as e:
                logging.error(f"❌ Error in server loop: {e}")
                break

        logging.info("⏹️ Server is shutting down")
        server_socket.close()


    def check_csv_for_completion(self):
        """
        Check the remote CSV file to see if the last line contains the end-of-processing message.
        """
        try:
            # Check if the CSV file path is set
            if not self.remote_csv_file_path:
                logging.error("Remote CSV file path is not set.")
                return False

            # Command to get the last line of the CSV file
            command = f"tail -n 1 {self.remote_csv_file_path}"
            
            # Execute the command and capture the output
            last_line = self.execute_remote_command_with_progress_ver2(command)
            
            # Ensure the output is properly stripped of leading/trailing whitespace
            last_line = last_line.strip() if last_line else ""

            logging.info(f"last_line : {last_line}")

            # Check for the specific error message in the last line
            error_message = "libpng error: Read Error"
            if error_message in last_line:
                logging.info("Processing complete: Error message  libpng error: Read Error found.")
              
                return True
            else:
                logging.info("Processing not complete: Error message not found.")
                return False

        except Exception as e:
            logging.error(f"An error occurred while checking the CSV file: {e}")
            return False


    def end_frame_processing(self):
        """
        Method to signal the server to stop after processing is complete.
        """
        self.stop_event.set()
        logging.info("Signaled server to stop.")


    def create_server_socket(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.tftp_ip, self.server_port))
            server_socket.listen(5)
            return server_socket
        except Exception as e:
            logging.error(f"Error creating server socket: {e}")
            return None


    def check_for_libpng_error(self):
        # Define the path to the CSV file on the device
        csv_file_path = '/logging/video-adas/177_video-adas_2024-08-15.csv'

        while True:
            # Fetch the CSV file from the device
            self.remote_commands = f"cat {csv_file_path}"
            csv_content = self.execute_remote_command_with_progress_ver2(self.remote_commands)
            
            # Get the last line from the CSV content
            if csv_content is not None:
                lines = csv_content.splitlines()
                if lines:
                    last_line = lines[-1].strip()
                    # logging.info(f"last_line : {last_line}")
                    if last_line.endswith('" libpng error: Read Error"'):
                        self.stop_server_flag.set()
                        logging.info("Found '\" libpng error: Read Error\"' at the end of the last line in CSV file. Stopping visualization.")
                        return True
                    else:
                        logging.info("No keyword libpng error: Read Error")
            
            
            # Sleep for a short interval before checking again
            time.sleep(10)

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
            logging.info(f'hostname:{self.camera_host_name}')
            logging.info(f'port:{self.camera_port}')
            logging.info(f'username:{self.camera_user_name}')
            logging.info(f'password:{self.camera_password}')
            ssh.connect(self.camera_host_name, self.camera_port, self.camera_user_name, self.camera_password)
            print(f"Connected to {self.camera_host_name}")

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


    def execute_remote_command_async(self, command):
        """
        Execute a remote command asynchronously.
        """
        # def target():
        #     self.execute_remote_command_with_progress(command)
        def target():
            # while True:
                # Simulate command execution progress
            logging.info("Executing command:", command)
            self.execute_remote_command_with_progress_ver2(command)
            time.sleep(1)  # Simulate work by sleeping
                
                # You could add actual command execution logic here
                # For example, self.execute_command(command)
                
                # if self.stop_thread_event.is_set():
                #     print("Stopping execution.")
                #     break
        
        thread = threading.Thread(target=target)
        thread.start()
        return thread
    
    def execute_local_command_async(self, command):
        """
        Execute a remote command asynchronously.
        """
        def target():
            self.execute_local_command(command)
        
        thread = threading.Thread(target=target)
        thread.start()
        return thread
    
    def execute_remote_command_with_progress_ver2(self, command):
        """
        Execute a remote command via SSH and monitor its progress.

        Args:
            command (str): The command to be executed on the remote server.

        Returns:
            str: The complete output from the command.
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.camera_host_name, self.camera_port, self.camera_user_name, self.camera_password)
            logging.info(f"🚀  Connected to IP:{self.camera_host_name} port:{self.camera_port} user:{self.camera_user_name} password:{self.camera_password}")

            # Execute the command with a timeout
            stdin, stdout, stderr = ssh.exec_command(command, timeout=10)  # Set an appropriate timeout
            logging.info(f"✅ Finished executing command: {command}")

            final_output = []
            final_errors = []

            # Continuously check if the command has finished
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.readline()
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')
                    final_output.append(line.strip())
                
                if stderr.channel.recv_ready():
                    error_line = stderr.readline()
                    if isinstance(error_line, bytes):
                        error_line = error_line.decode('utf-8')
                    final_errors.append(error_line.strip())
                
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

    def receive_image_and_log(self, client_socket, custom_directory):
        """
        Receive image data and JSON logs from a client connection.

        Args:
            client_socket (socket.socket): The socket object for the client connection.
            custom_directory: Custom directory to save the received data.

        This method processes and saves the received image and JSON log data.
        """
        try:
            # Receive the frame_index
            frame_index_data = client_socket.recv(4)
            if not frame_index_data:
                logging.error("❌ Failed to receive frame index.")
                return

            frame_index = int.from_bytes(frame_index_data, byteorder='big')
            # logging.info(f"📥 Received frame index: {frame_index}")

            # Receive the size of the image
            size_data = client_socket.recv(4)
            if not size_data:
                logging.error("❌ Failed to receive image size.")
                return

            size = int.from_bytes(size_data, byteorder='big')
            # logging.info(f"📏 Expected image size: {size} bytes")

            # Receive the image data
            buffer = b''
            while len(buffer) < size:
                data = client_socket.recv(min(size - len(buffer), 4096))
                if not data:
                    break
                buffer += data

            if len(buffer) != size:
                logging.error(f"❌ Failed to receive the complete image data. Received {len(buffer)} bytes out of {size}")
                return

            # logging.info(f"✅ Successfully received the complete image data. Total bytes: {len(buffer)}")

            # Save the image to a file
            image_path = f'{self.im_dir}/{self.image_basename}{frame_index}.{self.image_format}'
            with open(image_path, 'wb') as file:
                file.write(buffer)
            # logging.info(f"💾 Image saved at {image_path}")

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
            self.Drawer.process_json_log(json_data, custom_directory)
            # logging.info("📜 JSON log processed successfully")

        except Exception as e:
            logging.error(f"❌ Error: {e} - An unexpected error occurred.")



    def receive_fixed_size_data(self, sock, size):
        data = b''
        while len(data) < size:
            packet = sock.recv(size - len(data))
            if not packet:
                logging.error(f"❌ Received incomplete data. Total received: {len(data)} bytes.")
                raise ConnectionError("❌ Failed to receive enough data.")
            data += packet
            logging.debug(f"Received packet: {packet.hex()} (Total: {len(data)}/{size} bytes)")
        return data

    def get_input_mode_value(self):
        # Ensure you have the correct path to the config file
        config_file_path = os.path.join(self.camera_config_dir,'config.txt')

        # Command to get the value of InputMode from the config file
        command = f"grep '^InputMode' {config_file_path} | awk -F ' = ' '{{print $2}}'"
        
        logging.info(f"Retrieving InputMode value with command: {command}")
        
        # Execute the command and capture the output
        stdin, stdout, stderr = self.execute_remote_command_with_progress_ver2(command)
        
        # Read the output from stdout
        input_mode_value = stdout.read().strip()
        
        logging.info(f"InputMode value retrieved: {input_mode_value}")
        
        return input_mode_value
    

    def receive_image_and_log_and_imgpath(self, client_socket):
        """
        Receives image data, JSON logs, and the image path from a client connection.

        Args:
            client_socket (socket.socket): The socket object for the client connection.
            
        Process:
            1. Receives the frame index as a 4-byte integer.
            2. Receives the size of the image data in bytes (4-byte integer).
            3. Receives the image data based on the received size.
            4. Saves the received image data to a file.
            5. Receives the length of the image path (4-byte integer).
            6. Receives the image path data based on the received length.
            7. Receives the JSON log data until a termination sequence is detected.
            8. Passes the JSON log and image path to the `Drawer.process_json_log` method for further processing.
        
        Exceptions:
            Logs any errors that occur during the process and stops further execution.
        """
        try:
            # logging.info("------------------------------------------------------------------------------------")
            # Receive the frame_index
            frame_index_data = client_socket.recv(4)
            if not frame_index_data:
                logging.error("❌ Failed to receive frame index.")
                return

            frame_index = int.from_bytes(frame_index_data, byteorder='big')
            # logging.info(f"📥 Received frame index: {frame_index}")

            # Receive the size of the image
            size_data = client_socket.recv(4)
            if not size_data:
                logging.error("❌ Failed to receive image size.")
                return

            size = int.from_bytes(size_data, byteorder='big')
            # logging.info(f"Received image size: {size} bytes")

            # Receive the image data
            buffer = b''
            while len(buffer) < size:
                data = client_socket.recv(min(size - len(buffer), 4096))
                if not data:
                    break
                buffer += data

            if len(buffer) != size:
                logging.error(f"❌ Failed to receive the complete image data. Received {len(buffer)} bytes out of {size}")
                return

            # logging.info(f"✅ Successfully received the complete image data. Total bytes: {len(buffer)}")

            # Save the image to a file
            image_path = f'{self.im_dir}/{self.image_basename}{frame_index}.{self.image_format}'

            with open(image_path, 'wb') as file:
                file.write(buffer)
            # logging.info(f"💾 Image saved at {image_path}")

            # Receive the length of the image path
            path_length_data = client_socket.recv(4)
            if not path_length_data:
                logging.error("❌ Failed to receive image path length.")
                return
            # logging.info(f"📏 Received image path length: {path_length} bytes")

            path_length = int.from_bytes(path_length_data, byteorder='big')
            # logging.info(f"📏 Received image path length: {path_length} bytes")

            

            # Start receiving the image path
            # logging.info(f"Attempting to receive {path_length} bytes for image path")
            image_path_data = self.receive_fixed_size_data(client_socket, path_length)

            image_path = image_path_data.decode('utf-8')
            # logging.info(f"🛤️ Received image path: {image_path_data.decode('utf-8')}")

            # Receive the JSON log
            json_data = b''
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                json_data += data
                if b'\r\n\r\n' in data:
                    break

            json_data = json_data.decode('utf-8')
            # logging.info(f"📜 Received JSON log")

          
         
            self.Drawer.process_json_log(json_data,image_path)
            # logging.info("✅ JSON log processed successfully")

        except Exception as e:
            logging.error(f"❌ Error: {e} - An unexpected error occurred.")



