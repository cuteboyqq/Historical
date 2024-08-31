from utils.drawer import Drawer
from utils.display import DisplayUtils
# from utils.connection_handler import ConnectionHandler
import numpy as np
import cv2
from utils.saver import ImageSaver
from datetime import datetime
import os
import psutil
import os
import signal
class Visualizer():
    def __init__(self, connection, config):
        """Initialize the Visualizer.

        Args:
            config: Configuration object containing necessary parameters.
        """
        # Store the configuration object
        self.config = config

        # Re start camera ADAS when visualize
        self.re_start_adas = config.re_start_adas


        # Save raw images
        self.save_rawimages = config.save_rawimages

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

        # Alister add 2024-08-31
        self.server_port = self.connect.server_port

        self.ImageSaver = ImageSaver(config)


        current_datetime = datetime.now()
        # Format the dsatetime string as 'YYYY.MM.DD-HH:MM:SS'
        self.folder_name = current_datetime.strftime('%Y.%m.%d-%H:%M:%S')

        self.current_directory = os.getcwd()

        self.save_raw_images_dir = os.path.join(self.current_directory,"assets","images",self.folder_name)

        os.makedirs(self.save_raw_images_dir, exist_ok=True)


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

            # with open(image_path, 'wb') as file:
            #    file.write(image)

            

            np_arr = np.frombuffer(image, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if self.save_rawimages:
                self.ImageSaver.save_image(image, frame_index,save_dir=self.save_raw_images_dir)

            if image is None:
                raise ValueError("Failed to decode image from buffer.")

            # Process the JSON log
            self.drawer.process_json_log(log, img_buffer=image)
            # self.drawer.process_json_log(log)

        except Exception as e:
            self.display.show_status(self.role, f"Receive image and log: {str(e)}", False)

    def _receive_image_and_log_and_image_path(self, data):
        """Receive image data and JSON logs from a client connection.

        This method processes the received data, saves the image to a file,
        and processes the JSON log.

        Args:
            data (dict): Dictionary containing image data and JSON log.
        """
        try:
            frame_index = data['frame_index']
            image = data['image']
            image_path = data['image_path']
            log = data['log']

            
            np_arr = np.frombuffer(image, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if self.save_rawimages:
                self.ImageSaver.save_image(image, frame_index,save_dir=self.save_raw_images_dir)
            if image is None:
                raise ValueError("Failed to decode image from buffer.")

            # Process the JSON log
            # self.drawer.process_json_log(log, image_path)
            self.drawer.process_json_log(log, img_buffer= image, device_image_path=image_path)

        except Exception as e:
            self.display.show_status(self.role, f"Receive image and log: {str(e)}", False)

    def check_local_port_in_use(self,port):
        """
        Check if a port is in use on the local machine and return the process using it.

        Args:
            port (int): The port number to check.

        Returns:
            tuple: A tuple containing a boolean (whether the port is in use), process ID (int), and process name (str).
        """
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                pid = conn.pid
                process_name = psutil.Process(pid).name()
                return True, pid, process_name
        return False, None, None

    def kill_local_process(self,pid):
        """
        Kill a local process by its PID.

        Args:
            pid (int): The process ID to kill.

        Returns:
            str: Result message indicating success or failure.
        """
        try:
            os.kill(pid, signal.SIGTERM)  # or signal.SIGKILL
            return f"✅ Process with PID {pid} has been killed successfully."
        except Exception as e:
            return f"❌ Error killing process with PID {pid}: {e}"