import os
import sys
import csv
import json
import time
from utils.adas_log_parser import AdasLogParser
# from visualize_tools.visualizer import Visualizer
from task.visualizer import Visualizer

class VisualizerOffline(Visualizer):
    def __init__(self, connection, config):
        """Initialize the VisualizerOffline.

        Args:
            config: Configuration object containing necessary parameters.
        """
        # Initialize the parent Visualizer class
        super().__init__(connection, config)

        self.log_frame_id_set = set()
        self.adas_log_parser = AdasLogParser()

        

    def run(self):
        """Run the VisualizerOffline.

        Returns:
            bool: True if the process completes successfully, False otherwise.
        """
        self.display.print_header("Starting visualize execution...")

        if not self._setup_visualizer():
            return False

        self.drawer.draw_AI_result_to_images()

        return True

    def _is_image_file_exists(self):
        """Check if the image directory exists.

        Returns:
            bool: True if the image directory exists, False otherwise.
        """
        print(f"self.img_dir:{self.img_dir}")
        if os.path.exists(self.img_dir):
            return True
        else:
            return False

    def _is_log_file_exists(self):
        """Check if the CSV log file exists.

        Returns:
            bool: True if the CSV log file exists, False otherwise.
        """
        print(f"self.csv_file_pat:{self.csv_file_path}")
        if os.path.exists(self.csv_file_path):
            return True
        else:
            return False

    def _get_image_file_list(self):
        """Get the list of image files in the image directory.

        Returns:
            list: A list of filenames in the image directory.
        """
        try:
            file_list = [f for f in os.listdir(self.img_dir) if f.lower().endswith(self.config.image_format)]
            return file_list
        except OSError as e:
            self.display.show_status(self.role, f"Error accessing image directory: {str(e)}", False)
            return []

    def _get_log_frame_id_set(self):
        """Get the number of unique frame_IDs from the CSV log file.

        Returns:
            int: The number of unique frame_IDs.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            json.JSONDecodeError: If there's an error decoding the JSON string.
        """
        frame_id_set = set()
        try:
            with open(self.csv_file_path, 'r') as csv_file:
                csv_reader = csv.reader(csv_file)
                next(csv_reader)  # Skip the header row if it exists

                for row in csv_reader:
                    if len(row) >= 6:  # Ensure the row has at least 6 columns
                        timestamp_str = row[0].strip()
                        json_str = row[6].strip()  # Get the JSON string from the 6th column
                        if json_str.startswith('[JSON] [debug] json'):
                            self.adas_log_parser.parse(json_str, src_timestamp_str=timestamp_str)
                            frame_id = self.adas_log_parser.get_frame_id()

                            if frame_id is not None:
                                frame_id_set.add(frame_id)
            return frame_id_set
        except FileNotFoundError:
            self.display.show_status(self.role, f"CSV file not found: {self.csv_file_path}", False)
            return set()
        except json.JSONDecodeError as e:
            self.display.show_status(self.role, f"Error decoding JSON: {str(e)}", False)
            return set()
        except OSError as e:
            self.display.show_status(self.role, f"Error opening CSV file: {str(e)}", False)
            return set()

    def _is_image_match_log(self):
        """Check if the number of image files matches the number of log entries.

        Returns:
            bool: True if the numbers match, False otherwise.
        """
        is_match = True

        # Get the number of image files
        image_file_num = len(self._get_image_file_list())

        # Get the set of frame_IDs from the log file
        self.log_frame_id_set = self._get_log_frame_id_set()

        # Get the number of log entries
        log_num = len(self.log_frame_id_set)

        # Compare the numbers
        if image_file_num != log_num:
            self.display.show_warning(self.role, "Image file number does not match log number")
            print(f"Image number: \t {image_file_num}")
            print(f"Log number: \t {log_num}")
            print()
            is_match = False

        return is_match

    def _setup_visualizer(self):
        """Set up the visualizer by checking if image files match log entries.

        Returns:
            bool: True if setup is successful, False otherwise.
        """
        # Check if image files exist
        if not self._is_image_file_exists():
            self.display.show_status(self.role, "Image file does not exist", False)
            return False

        # Check if log file exists
        if not self._is_log_file_exists():
            self.display.show_status(self.role, "Log file does not exist", False)
            return False

        # Check if image files match log entries
        self._is_image_match_log()

        return True