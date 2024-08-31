import os
import time
import signal
from scp import SCPClient, SCPException
from utils.display import DisplayUtils
from utils.connection_handler import ConnectionHandler

class DataTransfer():
    def __init__(self, connection_handler, config):
        """
        Initialize the DataTransfer class.

        Args:
            connection_handler (ConnectionHandler): Handler for remote connections.
            config (object): Configuration object containing necessary settings.
        """
        # Store the configuration object
        self.config = config
        self.role = "Host"
        self.remote_role = "Device"
        self.display = DisplayUtils()

        # Connection-related configurations
        self.connect = connection_handler
        self.ssh = connection_handler.remote_ssh

        # Set image directory paths
        self.img_dir = self.config.im_dir
        self.local_img_root = os.path.dirname(self.img_dir)
        self.remote_img_root = self.config.camera_rawimages_dir
        self.remote_log_root = self.config.camera_csvfile_dir

        # Adjust paths for Windows systems
        if os.name == 'nt':  # 'nt' is the name for Windows systems
            self.remote_log_root = self.remote_log_root.replace('\\', '/')
            self.remote_img_root = self.remote_img_root.replace('\\', '/')

        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)  # Register SIGINT handler

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
                self.display.show_warning(self.role, "No folders found in the remote path.")
                return None

            return self._select_folder(folder_names, "remote")

        except Exception as e:
            self.display.show_status(self.role, f"Error selecting remote folder: {str(e)}", False)
            return None

    def _select_local_image_folder(self):
        """
        Select a folder from the local path.

        Returns:
            str: The name of the selected folder.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

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

    def _select_remote_csv_files(self):
        """
        Select the corresponding CSV file based on the selected image folder.

        Returns:
            list: A list of matching CSV file names.
        """
        if not self.remote_img_dir_name:
            self.display.show_warning(self.role, "No image folder selected. Please select an image folder first.")
            return None

        try:
            # List all CSV files in the remote log directory
            stdin, stdout, stderr = self.ssh.client.exec_command(f'ls {self.remote_log_root}/*.csv*')
            csv_files = stdout.read().decode().strip().split('\n')

            # Filter CSV files that match the image folder name
            # Split the remote folder name and pad the month and day with zeros if needed
            folder_parts = self.remote_img_dir_name.split('-')
            year, month, day = folder_parts[:3]
            month = month.zfill(2)
            day = day.zfill(2)
            log_filename_token = f"{year}-{month}-{day}"

            matching_csv_files = [file for file in csv_files if log_filename_token in file]

            if not matching_csv_files:
                self.display.show_warning(self.role, f"No matching CSV file found for folder: {self.remote_img_dir_name}")
                return None

            return matching_csv_files

        except Exception as e:
            self.display.show_error(self.role, f"Error selecting CSV file: {str(e)}")
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
            cmd = (f'tar cvf {self.remote_compressed_download_path} '
                    f'-C {self.remote_img_root} '
                    f'{self.remote_img_dir_name}')

            print(f"Executing command: {cmd}")

            # Execute command and capture output
            stdin, stdout, stderr = self.ssh.client.exec_command(cmd)

            # Create a progress bar
            from tqdm import tqdm
            pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="🗜️ Compressing")

            # Monitor the size of the output file
            while not stdout.channel.exit_status_ready():
                # Check the size of the output file
                stdin, stdout_size, stderr = self.ssh.client.exec_command(f'du {self.remote_compressed_download_path} | cut -f1')
                try:
                    current_size = int(stdout_size.read().decode().strip())
                    pbar.update(current_size - pbar.n)
                except:
                    continue

                time.sleep(1)  # Wait for a second before checking again

            # Close the progress bar
            pbar.close()

            # Wait for the command to complete
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                self.display.show_status(self.role, "Compression completed", True)
                return True
            else:
                error = stderr.read().decode()
                self.display.show_status(self.role, f"Error compressing files: {error}", False)
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
                scp.get(self.remote_compressed_download_path, self.local_img_root)
            self.display.show_status(self.role, f"Downloaded compressed images to \033[32m{self.local_img_root}\033[0m", True)

            return True
        except SCPException as e:
            self.display.show_status(self.role, f"SCP file transfer failed: {str(e)}", False)
            return False
        except IOError as e:
            self.display.show_status(self.role, f"I/O error: {str(e)}", False)
            return False

    def compress_local_images(self):
        """
        Compress the local images directory with a progress bar.

        Returns:
            bool: True if compression is successful, False otherwise.
        """
        # Check if the compressed file already exists
        if os.path.exists(self.local_compressed_path):
            print(f"🗜️ Compressed file already exists at {self.local_compressed_path}. Skip compression")
            return True

        try:
            import tarfile
            from tqdm import tqdm

            print(f"🗜️ Compressing local images \033[32m{self.img_dir}\033[0m to \033[32m{self.local_compressed_path}\033[0m...")

            source_dir = self.img_dir

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
            return True
        except Exception as e:
            self.display.show_status(self.role, f"Error during local compression: {str(e)}", False)
            return False

    def upload_compressed_images(self):
        """
        Upload the compressed file to the remote device.

        Returns:
            bool: True if upload is successful, False otherwise.
        """
        try:
            with SCPClient(self.ssh.get_transport(), progress=self._upload_progress) as scp:
                scp.put(self.local_compressed_path, self.remote_upload_compressed_path)

            self.display.show_status(self.role, f"Successfully uploaded compressed images to remote device", True)

            return True
        except SCPException as e:
            self.display.show_status(self.role, f"SCP file transfer failed: {str(e)}", False)
            return False
        except IOError as e:
            self.display.show_status(self.role, f"I/O error: {str(e)}", False)
            return False

    def decompress_remote_images(self):
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
            else:
                self.display.show_status(self.role, "Decompressed images on remote device", True)

        except Exception as e:
            self.display.show_status(self.role, f"Error during remote decompression: {str(e)}", False)

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
            self._pbar = tqdm(total=size, unit='B', unit_scale=True, desc=f"📥 Downloading \033[32m{self.remote_compressed_download_path}\033[0m to \033[32m{filename}\033[0m")

        self._pbar.update(sent - self._pbar.n)

        if sent == size:
            self._pbar.close()
            delattr(self, '_pbar')

    def _upload_progress(self, filename, size, sent):
        """
        Display progress of file upload using a progress bar.

        Args:
            filename (str): Name of the file being uploaded.
            size (int): Total size of the file.
            sent (int): Amount of data sent so far.
        """
        from tqdm import tqdm

        if not hasattr(self, '_pbar'):
            self._pbar = tqdm(total=size, unit='B', unit_scale=True, desc=f"📤 Uploading compressed images to \033[32m{self.remote_upload_compressed_path}\033[0m")

        self._pbar.update(sent - self._pbar.n)

        if sent == size:
            self._pbar.close()
            delattr(self, '_pbar')

    def _signal_handler(self, signum, frame):
        """
        Handle interrupt signals to gracefully shut down the server.

        Args:
            signum (int): The signal number.
            frame (frame): The current stack frame.
        """
        print("\nReceived interrupt signal. Shutting down...")
        self.stop = True
        if self.server:
            self.server.close()
        if self.client:
            self.client.close()