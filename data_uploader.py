import os
import sys
from scp import SCPClient, SCPException
from data_tools.data_transfer import DataTransfer
from utils.connection_handler import ConnectionHandler

class DataUploader(DataTransfer):
    """
    A class for uploading data to a remote server.
    Inherits from DataTransfer.
    """

    def __init__(self, connection_handler, config):
        """
        Initialize the DataUploader.

        Args:
            connection_handler (ConnectionHandler): Handler for remote connections.
            config (object): Configuration object containing necessary settings.
        """
        # Initialize DataTransfer
        super().__init__(connection_handler, config)
        # Select local image folder
        self.local_img_dir_name = self._select_local_image_folder()
        if self.local_img_dir_name is None:
            sys.exit(0)
        # Create local compressed path
        self.local_compressed_path = os.path.join(self.local_img_root, f"{self.local_img_dir_name}.tar.gz")
        # Create remote compressed path
        self.remote_upload_compressed_path = os.path.join(self.remote_img_root, f"{self.local_img_dir_name}.tar.gz")

        # Check if the operating system is Windows
        if os.name == 'nt':  # 'nt' is the name for Windows systems
            self.remote_upload_compressed_path = self.remote_upload_compressed_path.replace('\\', '/')

    def _select_local_image_folder(self):
        """
        Select a folder from the local path.

        Returns:
            str: The name of the selected folder.
        """
        try:
            # List all folders in the local path
            local_folders = [f for f in os.listdir(self.local_img_root) if os.path.isdir(os.path.join(self.local_img_root, f))]

            if not local_folders:
                self.display.show_warning(self.role, "No folders found in the local path.")
                return None

            return self._select_folder(local_folders, "local")

        except Exception as e:
            self.display.show_status(self.role, f"Error selecting local folder: {str(e)}", False)
            return None

    def compress_local_images(self):
        """
        Compress the local images directory with a progress bar.

        Returns:
            bool: True if compression is successful, False otherwise.
        """
        # Check if the compressed file already exists
        if os.path.exists(self.local_compressed_path):
            print(f"🗜️ Compressed file already exists at \033[32m{self.local_compressed_path}\033[0m. Skip compression")
            print()
            return True

        try:
            import tarfile
            from tqdm import tqdm

            print(f"🗜️ Compressing local images \033[32m{self.local_img_dir_name}\033[0m to \033[32m{self.local_compressed_path}\033[0m...")

            source_dir = os.path.join(self.local_img_root, self.local_img_dir_name)
            if os.name == 'nt':
                source_dir = source_dir.replace('\\', '/')

            with tarfile.open(self.local_compressed_path, "w:gz") as tar:
                total_files = sum(len(files) for _, _, files in os.walk(source_dir))
                with tqdm(total=total_files, unit="file", desc="🗜️ Compressing") as pbar:
                    for root, _, files in os.walk(source_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                            tar.add(file_path, arcname=arcname)
                            pbar.update(1)

            self.display.show_status(self.role, f"Compressed local images to \033[32m{self.local_compressed_path}\033[0m", True)
            print()
            return True
        except Exception as e:
            self.display.show_status(self.role, f"Error during local compression: {str(e)}", False)
            print()
            return False

    def upload_local_compressed_images(self):
        """
        Upload the compressed file to the remote device.

        Returns:
            bool: True if upload is successful, False otherwise.
        """
        try:
            with SCPClient(self.ssh.get_transport(), progress=self._upload_progress) as scp:
                scp.put(self.local_compressed_path, self.remote_upload_compressed_path)

            self.display.show_status(self.role, f"Successfully uploaded compressed images to remote device", True)
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

    def decompress_remote_compressed_images(self):
        """
        Decompress the uploaded file on the remote device with a progress bar.
        """
        try:
            # Get the size of the compressed file
            stdin, stdout, stderr = self.ssh.client.exec_command(f"du {self.remote_upload_compressed_path}")
            file_size_str = ''.join(c for c in str(stdout.read()).split('\\t')[0] if c.isdigit())
            file_size = int(file_size_str)

            # Command to decompress the file and show progress
            decompress_command = f"tar -xzvf {self.remote_upload_compressed_path} -C {self.remote_img_root}"

            # Execute the decompression command
            stdin, stdout, stderr = self.ssh.client.exec_command(decompress_command)

            for line in stdout:
                self.display.print_progress(f"🗜️ Decompressing \033[32m{self.remote_upload_compressed_path}\033[0m...")
            print('\n')

            # Check the exit status after the loop
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode().strip()
                self.display.show_status(self.role, f"Decompressing images on remote device: {error}", False)
                print()
            else:
                self.display.show_status(self.role, "Decompressed images on remote device", True)
                print()

        except Exception as e:
            self.display.show_status(self.role, f"Error during remote decompression: {str(e)}", False)
            print()

    def _upload_progress(self, filename, size, sent):
        """
        Display progress of file upload using a progress bar.

        Args:
            filename (str): The name of the file being uploaded.
            size (int): The total size of the file being uploaded.
            sent (int): The number of bytes sent so far.
        """
        from tqdm import tqdm

        if not hasattr(self, '_pbar'):
            self._pbar = tqdm(total=size, unit='B', unit_scale=True, desc=f"📤 Uploading compressed images to \033[32m{self.remote_upload_compressed_path}\033[0m")

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

    # Check if the connection is setup successfully
    if connection_handler.is_setup_success():

        # Initialize DataUploader
        data_uploader = DataUploader(connection_handler, config)

        # Test upload workflow
        data_uploader.compress_local_images()
        data_uploader.upload_local_compressed_images()
        data_uploader.decompress_remote_compressed_images()

        connection_handler.close_connection()