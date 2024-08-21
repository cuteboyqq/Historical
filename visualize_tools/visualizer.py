from utils.drawer import Drawer
from utils.display import DisplayUtils
from utils.connection_handler import ConnectionHandler

class Visualizer():
    def __init__(self, connection, config):
        """Initialize the Visualizer.

        Args:
            config: Configuration object containing necessary parameters.
        """
        # Store the configuration object
        self.config = config

        # Image-related configurations
        self.img_dir = config.im_dir
        self.image_basename = config.image_basename
        self.image_format = config.image_format

        # ADAS log configurations
        self.csv_file_path = config.csv_file

        # Initialize the Drawer object for visualization
        self.drawer = Drawer(config)

        # Initialize the DisplayUtils object for displaying messages
        self.display = DisplayUtils()

        # Define the mode dictionary
        self.param_dict = {
            "online": {
                "InputMode": "0",
                "VisualizeMode": "0"
            },
            "semi-online": {
                "InputMode": "2",
                "VisualizeMode": "1"
            },
            "offline":  {
                "InputMode": "-1",
                "VisualizeMode": "2"
            },
        }
        self.mode_dict = self.param_dict[config.visualize_mode]

        # Initialize role for display messages
        self.role = "Host"

        # Connection-related configurations
        self.connect = connection

    def run(self):
        """Run the visualization process.

        This method should be implemented by subclasses to define the specific
        visualization behavior. In the base Visualizer class, it raises a
        NotImplementedError to indicate that subclasses must override this method.

        Raises:
            NotImplementedError: Always raised in the base class to ensure subclasses
                                 implement their own run method.
        """
        raise NotImplementedError("Subclasses must implement the 'run' method.")


    # ===== Socket reading-related methods =====

    def _receive_log(self, data):
        """Receive JSON logs from a client connection.

        This method processes the received data, saves the image to a file,
        and processes the JSON log.

        Args:
            data (dict): Dictionary containing image data and JSON log.
        """
        try:
            log = data['log']

            # Process the JSON log
            self.drawer.process_json_log(log, None)

        except Exception as e:
            self.display.show_status(self.role, f"Receive image and log: {str(e)}", False)

    def _receive_image_and_log(self, data):
        """Receive image data and JSON logs from a client connection.

        This method processes the received data, saves the image to a file,
        and processes the JSON log.

        Args:
            data (dict): Dictionary containing image data and JSON log.
        """
        try:
            frame_index = data['frame_index']
            image = data['image']
            log = data['log']

            # Save the image to a file
            image_path = f'{self.img_dir}/{self.image_basename}{frame_index}.{self.image_format}'

            with open(image_path, 'wb') as file:
                file.write(image)

            # Process the JSON log
            self.drawer.process_json_log(log, None)

        except Exception as e:
            self.display.show_status(self.role, f"Receive image and log: {str(e)}", False)

    # ===== Setup-related methods =====

    def _get_remote_config(self):
        """Retrieves the config file from the remote device.

        Returns:
            str: The content of the remote config file, or None if retrieval fails.
        """
        try:
            content = self.connect.get_file(self.remote_config_path)
            self.display.show_status(self.role, "Read remote ADAS config", True)
            return content
        except Exception as e:
            self.display.show_status(self.role, "Read remote ADAS config", False)
            return None

    def _modify_remote_config(self, server_ip, server_port):
        """Modifies the config file on the remote device.

        This method backs up the original config, modifies it with new server details,
        and writes it back to the remote device.

        Args:
            server_ip (str): Server IP address.
            server_port (int): Server port.

        Returns:
            bool: True if the modification is successful, False otherwise.
        """
        try:
            # First, backup the original config
            self.connect.remote_ssh.execute_command(f"cp {self.remote_config_path} {self.backup_config_path}")

            # Read the current config
            config_content = self._get_remote_config()
            if not config_content:
                return False

            # Modify the config #TODO:
            new_lines = []
            for line in config_content.splitlines():
                if line.startswith("InputMode"):
                    line = f"InputMode = {self.mode_dict['InputMode']}"
                elif line.startswith("ServerPort"):
                    line = f"ServerPort = {server_port}"
                elif line.startswith("ServerIP"):
                    line = f"ServerIP = {server_ip}"
                elif line.startswith("VisualizeMode"):
                    line = f"VisualizeMode = {self.mode_dict['VisualizeMode']}"
                new_lines.append(line)

            # Write the modified config back to the remote device
            modified_content = "\n".join(new_lines)
            self.connect.put_file(self.remote_config_path, modified_content)

            self.display.show_status(self.role, "Modify remote ADAS config", True)
            return True
        except Exception as e:
            self.display.show_status(self.role, "Modify remote ADAS config", False)
            return False

    def _restore_remote_config(self):
        """Restores the backed-up config file on the remote device.

        Returns:
            bool: True if the restoration is successful, False otherwise.
        """
        try:
            self.connect.remote_ssh.execute_command(f"mv {self.backup_config_path} {self.remote_config_path}")
            self.display.show_status(self.role, "Restore remote ADAS config", True)
            return True
        except Exception as e:
            self.display.show_status(self.role, "Restore remote ADAS config", False)
            return False

    def _run_remote_script(self):
        """Executes the run_adas.sh script on the remote device.

        Returns:
            bool: True if the script execution is successful, False otherwise.
        """
        try:
            result = self.connect.remote_ssh.execute_command(self.remote_adas_script_path)
            self.display.show_status(self.role, "Execute remote ADAS script", True)
            return True
        except Exception as e:
            self.display.show_status(self.role, "Execute remote ADAS script", False)
            return False
