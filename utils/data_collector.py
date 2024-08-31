import os
import sys
from scp import SCPClient, SCPException
from data_tools.data_transfer import DataTransfer
from utils.connection_handler import ConnectionHandler
from utils.adas_runner import AdasRunner
from datetime import datetime, timedelta
import time

class DataCollector(DataTransfer):
    """
    A class for collecting data from a remote device.

    This class extends DataTransfer and provides functionality to collect
    image and log data from a remote device running ADAS (Advanced Driver Assistance Systems).
    """

    def __init__(self, connection_handler, config):
        """
        Initialize the DataCollector.

        Args:
            connection_handler (ConnectionHandler): Handler for remote connections.
            config (object): Configuration object containing necessary settings.
        """
        super().__init__(connection_handler, config)
        self.adas_runner = AdasRunner(connection_handler, config)
        self.adas_run_duration = config.adas_run_duration
        self.dataset_name = None

        self.remote_img_dir = config.camera_rawimages_dir
        self.remote_log_dir = config.camera_csvfile_dir

        self.img_format = config.image_format

        self.remote_role = "Device"

        self.initial_image_folders = None
        self.initial_log_files = None

    def set_dataset_name(self):
        """
        Prompts the user to input a name for the current dataset.

        This method asks the user to enter a name for the dataset being collected.
        It ensures that a non-empty name is provided.

        Returns:
            str: The name of the dataset provided by the user.
        """
        while True:
            name = input("Please enter a name for this dataset: ").strip()
            if name:
                self.dataset_name = name
                return name
            else:
                print("Dataset name cannot be empty. Please try again.")

    def run(self):
        """
        Run the data collection process.

        This method orchestrates the entire data collection process, including
        stopping ADAS, modifying remote configurations, collecting data, and
        handling the collected data.

        Returns:
            bool: True if the data collection process was successful, False otherwise.
        """
        self.display.print_header("Starting data collection...")

        self.set_dataset_name()

        # Stop ADAS
        if not self.adas_runner.stop_adas():
            self.display.show_status(self.role, "Failed to stop ADAS", False)
            return False

        # Modify remote config
        if not self.adas_runner.modify_remote_config(enable_save_raw_images=True):
            self.display.show_status(self.role, "Failed to modify remote config", False)
            return False

        # Set date on remote device
        if not self._set_remote_next_day():
            self.display.show_status(self.role, "Failed to set remote next date", False)
            return False

        # Save current image folder list
        self.initial_image_folders = self._get_remote_image_folders()

        # Save current log file list
        self.initial_log_files = self._get_remote_log_files()

        # Run ADAS (in data collection mode) for specified duration
        if not self._run_adas_for_duration():
            self.display.show_status(self.role, "Failed to run ADAS", False)
            return False

        # Stop ADAS
        if not self.adas_runner.stop_adas():
            self.display.show_status(self.role, "Failed to stop ADAS", False)
            return False

        # Modify remote config
        if not self.adas_runner.modify_remote_config(enable_save_raw_images=False):
            self.display.show_status(self.role, "Failed to modify remote config", False)
            return False

        # Rename new image folder
        if not self._rename_new_image_folder():
            self.display.show_status(self.role, "Failed to rename new image folder", False)
            return False

        # Create new log folder and move new log files
        if not self._handle_new_log_files():
            self.display.show_status(self.role, "Failed to handle new log files", False)
            return False

        # Get the number of collected images
        image_count_command = f"ls {self.remote_img_dir}/{self.dataset_name}/*.{self.img_format} | wc -l"
        image_count = int(self.connect.remote_ssh.execute_command(image_count_command).strip())

        # Get the number of collected log files
        log_count_command = f"ls {self.remote_log_dir}/{self.dataset_name}/* | wc -l"
        log_count = int(self.connect.remote_ssh.execute_command(log_count_command).strip())
        self.display.show_status(self.role, "Data collection", True)
        print(f"\nDataset \033[1;37;42m {self.dataset_name} \033[0m collection completed")
        print(f"1. Image dataset path: \033[1;37;42m {self.remote_img_dir}/{self.dataset_name} \033[0m", end='')
        print(f"   Total images collected: \033[1;37;42m {image_count} \033[0m")
        print(f"2. Log dataset path: \033[1;37;42m {self.remote_log_dir}/{self.dataset_name} \033[0m", end='')
        print(f"   Total log files collected: \033[1;37;42m {log_count} \033[0m")
        self.display.show_status(self.role, f"ADAS Data Collection", True)
        print()
        return True

    # ===== Setup-related methods =====

    def _get_remote_date(self):
        """
        Get the current date from the remote device.

        Returns:
            str: The current date on the remote device in the format 'YYYY-MM-DD HH:MM:SS',
                 or None if there was an error.
        """
        try:
            command = "date '+%Y-%m-%d %H:%M:%S'"
            remote_date = self.connect.remote_ssh.execute_command(command).strip()
            self.display.show_status(self.role, f"Get remote date: {remote_date}", True)
            return remote_date
        except Exception as e:
            self.display.show_status(self.role, "Get remote date", False)
            return None

    def _set_remote_next_day(self):
        """
        Set the date on the remote device to the next day.

        Returns:
            bool: True if the date was set successfully, False otherwise.
        """
        try:
            current_date = self._get_remote_date()
            if current_date is None:
                return False

            next_day = (datetime.strptime(current_date, "%Y-%m-%d %H:%M:%S") + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            command = f"date -s '{next_day}'"
            self.connect.remote_ssh.execute_command(command)
            self.display.show_status(self.role, f"Set remote date to next day: {next_day}", True)
            return True
        except Exception as e:
            self.display.show_status(self.role, "Set remote date to next day", False)
            return False

    def _get_remote_image_folders(self, show_list=False):
        """
        Get a list of image folders on the remote device.

        Args:
            show_list (bool): If True, display the list of folders.

        Returns:
            list: A list of image folder names.
        """
        try:
            command = f"ls -d {self.remote_img_dir}/*/"
            output = self.connect.remote_ssh.execute_command(command)
            folders = [os.path.basename(folder.strip('/')) for folder in output.split()]

            if show_list:
                self.display.print_header(f"Detect folder list")
                for folder in folders:
                    self.display.show_message(self.remote_role, f"Folder: {folder}")
                print()

                self.display.show_status(self.role, "Get remote image folders", True)
            return folders
        except Exception as e:
            self.display.show_status(self.role, "Get remote image folders", False)
            return []

    def _get_remote_log_files(self, show_list=False):
        """
        Get a list of log files on the remote device.

        Args:
            show_list (bool): If True, display the list of log files.

        Returns:
            list: A list of log file names.
        """
        try:
            command = f"ls {self.remote_log_dir}/*.csv"
            output = self.connect.remote_ssh.execute_command(command)
            log_files = [os.path.basename(file) for file in output.split()]

            if show_list:
                self.display.print_header(f"Detect log list")

                for log_file in log_files:
                    self.display.show_message(self.remote_role, f"Log: {log_file}")
                print()

                self.display.show_status(self.role, "Get remote log files", True)
            return log_files
        except Exception as e:
            self.display.show_status(self.role, "Get remote log files", False)
            return []

    def _run_adas_for_duration(self):
        """
        Run ADAS for the specified duration.

        Returns:
            bool: True if ADAS ran successfully for the duration, False otherwise.
        """
        try:
            # Start ADAS
            if not self.adas_runner.run_adas():
                return False

            current_folders = self._get_remote_image_folders()
            new_folders = list(set(current_folders) - set(self.initial_image_folders))

            if len(new_folders) != 1:
                raise Exception(f"Expected exactly one new folder, found {len(new_folders)}")
            new_folder = new_folders[0]

            # Wait for the specified duration with progress bar
            self.display.show_message(self.remote_role, f"Running ADAS for \033[1;37;42m {self.adas_run_duration} \033[0m seconds...")
            start_time = time.time()
            end_time = start_time + self.adas_run_duration

            while time.time() < end_time:
                elapsed = time.time() - start_time
                remaining = self.adas_run_duration - elapsed
                progress = int(elapsed / self.adas_run_duration * 50)  # 50 characters for progress bar

                # Count the number of images collected so far
                image_count_command = f"ls {os.path.join(self.remote_img_dir, new_folder)}/*.{self.img_format} | wc -l"
                if os.name == 'nt':  # 'nt' is the name for Windows systems
                    image_count_command = image_count_command.replace('\\', '/')

                image_count = int(self.connect.remote_ssh.execute_command(image_count_command).strip())

                # Update progress bar with image count
                print(f"\r📥 Collecting [{'=' * progress}{' ' * (50-progress)}] {elapsed:.1f}s / {self.adas_run_duration}s | Images: {image_count}", end='', flush=True)
                time.sleep(0.1)  # Update every 0.1 seconds
            print()
            return True
        except Exception as e:
            self.display.show_status(self.role, f"Run ADAS failed: {str(e)}", False)
            print(f"Error details: {str(e)}")
            return False

    def _rename_new_image_folder(self):
        """
        Rename the newly created image folder.

        Returns:
            bool: True if the folder was renamed successfully, False otherwise.
        """
        try:
            current_folders = self._get_remote_image_folders()
            new_folders = list(set(current_folders) - set(self.initial_image_folders))

            if len(new_folders) != 1:
                raise Exception(f"Expected exactly one new folder, found {len(new_folders)}")

            new_folder = new_folders[0]
            new_name = f"{self.dataset_name}"

            old_path = os.path.join(self.remote_img_dir, new_folder)
            new_path = os.path.join(self.remote_img_dir, new_name)

            rename_command = f"mv {old_path} {new_path}"

            if os.name == 'nt':  # 'nt' is the name for Windows systems
                rename_command = rename_command.replace('\\', '/')

            self.connect.remote_ssh.execute_command(rename_command)

            self.display.show_status(
                self.role,
                f"Rename image folder \033[1;37;42m {new_folder} \033[0m to \033[1;37;42m {new_name} \033[0m",
                True
            )

            return True
        except Exception as e:
            self.display.show_status(
                self.role,
                f"Rename image folder \033[1;37;41m {new_folder}\033[0m to \033[1;37;41m {new_name} \033[0m",
                False
            )
            return False

    def _handle_new_log_files(self):
        """
        Create a new log folder and move new log files into it.

        Returns:
            bool: True if new log files were handled successfully, False otherwise.
        """
        remote_log_dir = self.remote_log_dir

        try:
            current_log_files = self._get_remote_log_files()
            new_log_files = list(set(current_log_files) - set(self.initial_log_files))

            if not new_log_files:
                self.display.show_message(self.remote_role, "No new log files found.")
                return True

            new_log_folder = f"{self.dataset_name}"
            mkdir_command = f"mkdir {remote_log_dir}/{new_log_folder}"
            if os.name == 'nt':
                mkdir_command = mkdir_command.replace('\\', '/')

            self.connect.remote_ssh.execute_command(mkdir_command)

            current_date = datetime.now().strftime("%Y-%m-%d")

            for log_file in new_log_files:
                # Extract parts of the original filename
                parts = log_file.split('_')
                if len(parts) >= 3:
                    prefix = '_'.join(parts[:2])  # e.g., "1005_video-adas"
                    extension = '.'.join(log_file.split('.')[-1:])  # e.g., "csv" or "1.csv"

                    # Create new filename with current host date
                    new_filename = f"{prefix}_{current_date}.{extension}"

                    # Move and rename the file
                    move_command = f"mv {remote_log_dir}/{log_file} {remote_log_dir}/{new_log_folder}/{new_filename}"
                else:
                    # If filename doesn't match expected format, just move without renaming
                    move_command = f"mv {remote_log_dir}/{log_file} {remote_log_dir}/{new_log_folder}/"

                if os.name == "nt":
                    move_command = move_command.replace('\\', '/')

                self.connect.remote_ssh.execute_command(move_command)
                self.display.show_status(
                    self.role,
                    f"Move log file \033[1;37;42m {log_file} \033[0m to \033[1;37;42m {remote_log_dir}/{new_log_folder} \033[0m", 
                    True
                )

            self.display.show_status(
                self.role,
                f"Move log files from \033[1;37;42m {remote_log_dir} \033[0m to \033[1;37;42m {remote_log_dir}/{new_log_folder} \033[0m", 
                True
            )
            return True
        except Exception as e:
            self.display.show_status(
                self.role,
                f"Move log files from \033[1;37;41m {remote_log_dir} \033[0m to \033[1;37;41m {remote_log_dir}/{new_log_folder} \033[0m", 
                False
            )
            return False

if __name__ == "__main__":
    import yaml
    from config.args import Args

    def load_config(config_file):
        """Load the YAML configuration file and return its content as a dictionary.

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

        # Initialize
        data_collector = DataCollector(connection_handler, config)
        data_collector.run()

        connection_handler.close_connection()
