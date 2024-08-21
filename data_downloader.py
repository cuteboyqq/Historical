import os
import time
from scp import SCPClient, SCPException
from data_tools.data_transfer import DataTransfer
from utils.connection_handler import ConnectionHandler

class DataDownloader(DataTransfer):
    def __init__(self, connection_handler, config):
        """
        Initialize the DataDownloader class.

        Args:
            connection_handler (ConnectionHandler): Handler for remote connections.
            config (object): Configuration object containing necessary settings.
        """
        # Initialize DataTransfer
        super().__init__(connection_handler, config)
        # Initialize variables
        self.remote_img_dir_name = self._select_remote_image_folder()
        self.remote_img_dir = os.path.join(self.remote_img_root, self.remote_img_dir_name)
        # Select the corresponding CSV file based on the selected image folder
        self.remote_log_dir = self._select_remote_csv_folder()
        # Compress the directory on the remote device
        self.remote_img_compressed_download_path = os.path.join(self.remote_img_root, f"{self.remote_img_dir_name}_img.tar.gz")
        self.remote_log_compressed_download_path = os.path.join(self.remote_log_root, f"{self.remote_img_dir_name}_log.tar.gz")

        # Check if the operating system is Windows
        if os.name == 'nt':  # 'nt' is the name for Windows systems
            # Replace backslashes with forward slashes for Windows compatibility
            self.remote_img_dir_name = self.remote_img_dir_name.replace('\\', '/')
            self.remote_img_dir = self.remote_img_dir.replace('\\', '/')
            self.remote_img_compressed_download_path = self.remote_img_compressed_download_path.replace('\\', '/')
            self.remote_log_compressed_download_path = self.remote_log_compressed_download_path.replace('\\', '/')

    def _select_remote_image_folder(self):
        """
        Select a folder to download from the remote path.

        Returns:
            str: The name of the selected folder.
        """
        try:
            # List all folders in the remote path
            stdin, stdout, stderr = self.ssh.client.exec_command(f'ls -d {self.remote_img_root}/*/')
            folders = stdout.read().decode().strip().split('\n')

            # Extract folder names from full paths
            folder_names = [os.path.basename(folder.rstrip('/')) for folder in folders]

            if not folder_names:
                self.display.show_warning(self.remote_role, "No folders found in the remote path.")
                print()
                return None

            return self._select_folder(folder_names, "remote")

        except Exception as e:
            self.display.show_status(self.remote_role, f"Error selecting remote folder: {str(e)}", False)
            print()
            return None

    def _select_remote_csv_folder(self):
        """
        Select the corresponding CSV file based on the selected image folder.

        Returns:
            list: A list of matching CSV file names.
        """
        if not self.remote_img_dir_name:
            self.display.show_warning(self.remote_role, "No image folder selected. Please select an image folder first.")
            return None
        try:
            # Check if the directory exists
            remote_log_dir = os.path.join(self.remote_log_root, self.remote_img_dir_name)
            if os.name == 'nt':
                remote_log_dir = remote_log_dir.replace('\\', '/')
            stdout = self.ssh.execute_command(f'test -d {remote_log_dir} && echo "exists"')
            if stdout == "exists":
                # List all files in the directory
                files_str = self.ssh.execute_command(f'ls -1 {remote_log_dir}')
                files = files_str.strip().split('\n')
                return remote_log_dir
            else:
                self.display.show_warning(self.remote_role, f"Directory not found: {remote_log_dir}")
                print()
                return None

        except Exception as e:
            self.display.show_status(self.remote_role, f"Error selecting CSV file: {str(e)}", False)
            print()
            return None

    def compress_remote_images(self):
        """
        Compress the directory on the remote device.

        Returns:
            bool: True if compression is successful, False otherwise.
        """
        try:
            # Get total size of files to compress
            du_cmd = f"du -s {self.remote_img_dir} | cut -f1"
            stdin, stdout, stderr = self.ssh.client.exec_command(du_cmd)
            total_size = int(stdout.read().decode().strip())

            # Prepare compression command
            cmd = (f'tar cvf {self.remote_img_compressed_download_path} '
                    f'-C {self.remote_img_root} '
                    f'{self.remote_img_dir_name}')

            # Execute command and capture output
            stdin, stdout, stderr = self.ssh.client.exec_command(cmd)

            # Monitor the size of the output file
            while not stdout.channel.exit_status_ready():
                # Check the size of the output file
                stdin, stdout_size, stderr = self.ssh.client.exec_command(f'du {self.remote_img_compressed_download_path} | cut -f1')
                self.display.print_progress(f"🗜️ Compressing \033[1;37;42m {self.remote_img_compressed_download_path} \033[0m...")
            print()

            # Wait for the command to complete
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                self.display.show_status(self.remote_role, "Compression completed", True)
                print()
                return True
            else:
                error = stderr.read().decode()
                self.display.show_status(self.remote_role, f"Error compressing files: {error}", False)
                print()
                return False
        except Exception as e:
            print(f"Error during remote compression: {str(e)}")
            return False

    def compress_remote_logs(self):
        """
        Compress the directory on the remote device.

        Returns:
            bool: True if compression is successful, False otherwise.
        """
        try:
            # Get total size of files to compress
            du_cmd = f"du -s {self.remote_log_dir} | cut -f1"
            stdin, stdout, stderr = self.ssh.client.exec_command(du_cmd)
            total_size = int(stdout.read().decode().strip())

            # Prepare compression command
            cmd = (f'tar cvf {self.remote_log_compressed_download_path} '
                    f'-C {self.remote_log_root} '
                    f'{self.remote_img_dir_name}')

            # Execute command and capture output
            stdin, stdout, stderr = self.ssh.client.exec_command(cmd)

            # Monitor the size of the output file
            while not stdout.channel.exit_status_ready():
                # Check the size of the output file
                stdin, stdout_size, stderr = self.ssh.client.exec_command(f'du {self.remote_log_compressed_download_path} | cut -f1')
                self.display.print_progress(f"🗜️ Compressing \033[1;37;42m {self.remote_log_compressed_download_path} \033[0m...")
            print()

            # Wait for the command to complete
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                self.display.show_status(self.remote_role, "Compression completed", True)
                print()
                return True
            else:
                error = stderr.read().decode()
                self.display.show_status(self.remote_role, f"Error compressing files: {error}", False)
                print()
                return False
        except Exception as e:
            print(f"Error during remote compression: {str(e)}")
            return False

    def download_compressed_images(self):
        """
        Download the compressed file from the remote device.

        Returns:
            bool: True if download is successful, False otherwise.
        """
        try:
            with SCPClient(self.ssh.get_transport(), progress=self._download_progress) as scp:
                scp.get(self.remote_img_compressed_download_path, self.local_img_root)
            self.display.show_status(self.role,
                f"Downloaded compressed images to \033[1;37;42m {os.path.join(self.local_img_root, self.remote_img_dir_name)}_img.tar.gz \033[0m", True)
            print()
            return True
        except SCPException as e:
            self.display.show_status(self.role, f"SCP file transfer failed: {str(e)}", False)
            print()
            return False
        except IOError as e:
            self.display.show_status(self.role, f"I/O error: {str(e)}", False)
            print()
            return False

    def download_compressed_logs(self):
        """
        Download the compressed file from the remote device.

        Returns:
            bool: True if download is successful, False otherwise.
        """
        try:
            with SCPClient(self.ssh.get_transport(), progress=self._download_progress) as scp:
                scp.get(self.remote_log_compressed_download_path, self.local_img_root)
            self.display.show_status(self.role,
                f"Downloaded compressed logs to \033[1;37;42m {os.path.join(self.local_img_root, self.remote_img_dir_name)}_log.tar.gz \033[0m", True)
            print()
            return True
        except SCPException as e:
            self.display.show_status(self.role, f"SCP file transfer failed: {str(e)}", False)
            print()
            return False
        except IOError as e:
            self.display.show_status(self.role, f"I/O error: {str(e)}", False)
            print()
            return False

    def _download_progress(self, filename, size, sent):
        """
        Display progress of file transfer using a progress bar.

        Args:
            filename (str): Name of the file being transferred.
            size (int): Total size of the file.
            sent (int): Amount of data sent so far.
        """
        from tqdm import tqdm

        if not hasattr(self, '_pbar'):
            self._pbar = tqdm(total=size, unit='B', unit_scale=True,
                desc=f"📥 Downloading")

        self._pbar.update(sent - self._pbar.n)

        if sent == size:
            self._pbar.close()
            delattr(self, '_pbar')


if __name__ == "__main__":
    import yaml
    from config.args import Args

    def load_config(config_file):
        """
        Load the YAML configuration file and return its content as a dictionary.

        Args:
            config_file (str): Path to the YAML configuration file.

        Returns:
            dict: Configuration settings loaded from the YAML file.
        """
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    # Load configuration settings from the specified YAML file
    config_yaml = load_config('config/config.yaml')

    # Initialize Args object with the loaded configuration
    config = Args(config_yaml)

    # Initialize ConnectionHandler
    connection_handler = ConnectionHandler(config)
    if connection_handler.is_setup_success():
        # Initialize DataDownloader
        data_downloader = DataDownloader(connection_handler, config)

        # Test download workflow
        data_downloader.compress_remote_images()
        data_downloader.download_compressed_images()

        data_downloader.compress_remote_logs()
        data_downloader.download_compressed_logs()

        #
        connection_handler.close_connection()
