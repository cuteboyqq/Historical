import sys
import time
import logging
import threading
from tqdm import tqdm
from utils.display import DisplayUtils
import paramiko
# from utils.connections.remote_ssh import RemoteSSH
# from utils.connections.remote_socket import RemoteSocket
from utils.socket import RemoteSocket
from utils.ssh import RemoteSSH
import socket
import psutil


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


        self.hostname=config.camera_host_name
        self.username=config.camera_user_name
        self.password=config.camera_password
        self.port=config.camera_port

        # Alister add 2024-08-31
        self.server_port = self.config.server_port
        self.server_ip = self.config.server_ip

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
        if self.config.visualize_mode == "online" and self.config.device_mode == 'live':
            recv_data_keys = ["frame_index", "image", "log"]
        elif self.config.visualize_mode == "online" and self.config.device_mode == 'historical':
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


    def is_remote_port_available(self, check_port):
        """
        Check if a specific port is available on a remote machine via SSH.

        Args:
            host (str): The IP address of the remote machine.
            port (int): The SSH port (default is usually 22).
            user (str): The SSH username.
            password (str): The SSH password.
            check_port (int): The port to check for availability.

        Returns:
            bool: True if the port is available, False otherwise.
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logging.info(f'🚀 Connecting to IP:{self.hostname} port:{self.port} user:{self.username} password:{self.password}')
            ssh.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)

            # Command to check if the port is in use
            command = f"ss -tuln | grep :{check_port}"

            logging.info(f"🚀 Executing command to check port availability: {command}")
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # Read the command output and error
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            # If the output is empty, the port is available
            if not output:
                logging.info(f"✅ Port {check_port} is available on the remote device.")
                return True
            else:
                logging.info(f"❌ Port {check_port} is already in use on the remote device.")
                return False

        except paramiko.ssh_exception.AuthenticationException as auth_err:
            logging.error(f"❌ Authentication failed: {auth_err}")
        except paramiko.ssh_exception.SSHException as ssh_err:
            logging.error(f"❌ SSH error: {ssh_err}")
        except Exception as e:
            logging.error(f"❌ An error occurred: {e}")
        finally:
            ssh.close()

        return False
    
    def is_local_port_available(self,port):
        """
        Check if a specific port is available on the local machine.

        Args:
            port (int): The port number to check.

        Returns:
            bool: True if the port is available, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.connect_ex(('0.0.0.0', port))
            if result == 0:
                logging.info(f"❌ Port {port} is already in use on the local machine.")
                return False
            else:
                logging.info(f"✅ Port {port} is available on the local machine.")
                return True
            

    # def check_process_using_port(port):
    #     """
    #     Check which process is using a specific port on the local machine.

    #     Args:
    #         port (int): The port number to check.

    #     Returns:
    #         None
    #     """
    #     try:
    #         result = subprocess.run(['lsof', '-i', f':{port}'], stdout=subprocess.PIPE, text=True)
    #         logging.info(result.stdout)
    #     except Exception as e:
    #         logging.error(f"Error checking process using port: {e}")


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
        
    import paramiko

    def check_port_and_kill_remotely(self,port):
        """
        Check if a port is in use on a remote machine, and kill the process if it is.

        Args:
            hostname (str): The IP or hostname of the remote machine.
            ssh_port (int): The SSH port number.
            username (str): The SSH username.
            password (str): The SSH password.
            port (int): The port to check.

        Returns:
            str: A message indicating the status of the port and the result of the kill command.
        """
        try:
            # 🚀 Connect to the remote machine via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
            print(f"🌐 Connected to {self.hostname} via SSH on port {self.port}.")

            # 🔍 Check for the process using the port
            check_command = f"ss -tuln | grep :{port}"
            stdin, stdout, stderr = ssh.exec_command(check_command)
            output = stdout.read().decode().strip()
            stderr_output = stderr.read().decode().strip()

            if not output:
                ssh.close()
                print(f"✅ Port {port} is available on the remote machine.")
                return f"✅ Port {port} is available on the remote machine."

            # 🔍 Extract the process ID (PID) from the output if the port is in use
            get_pid_command = f"lsof -i :{port} | awk 'NR>1 {{print $2}}'"
            stdin, stdout, stderr = ssh.exec_command(get_pid_command)
            pid = stdout.read().decode().strip()

            if pid:
                # 🛑 Kill the process using the 'kill' command
                kill_command = f"kill -9 {pid}"
                stdin, stdout, stderr = ssh.exec_command(kill_command)
                stderr_output = stderr.read().decode().strip()

                ssh.close()

                if stderr_output:
                    print(f"❌ Error killing process on the remote machine: {stderr_output}")
                    return f"❌ Error killing process on the remote machine: {stderr_output}"
                
                print(f"🗑️ Process {pid} using port {port} killed successfully on the remote machine.")
                return f"🗑️ Process {pid} using port {port} killed successfully on the remote machine."
            else:
                ssh.close()
                print(f"🚫 Unable to find process using port {port} on the remote machine.")
                return f"🚫 Unable to find process using port {port} on the remote machine."
        except paramiko.ssh_exception.AuthenticationException as auth_err:
            print(f"🔑 Authentication failed: {auth_err}")
            return f"🔑 Authentication failed: {auth_err}"
        except paramiko.ssh_exception.SSHException as ssh_err:
            print(f"⚠️ SSH error: {ssh_err}")
            return f"⚠️ SSH error: {ssh_err}"
        except Exception as e:
            print(f"❗ An error occurred: {e}")
            return f"❗ An error occurred: {e}"

# # Usage example
# hostname = "192.168.1.1"
# ssh_port = 22
# username = "root"
# password = "ALUDS$#q"
# port = 2511

# result = check_port_and_kill_remotely(hostname, ssh_port, username, password, port)
# print(result)


