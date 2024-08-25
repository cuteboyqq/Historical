import os
import cv2
import json
import csv
from pathlib import Path
import logging
import time
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageSaver:
    def __init__(self, args, base_dir='runs'):

        self.base_dir = base_dir
        # self.is_created = False
        self.current_dir = self._get_next_directory()
        self.custom_dir = None
        self.current_csv_dir = self._get_next_csv_directory()
        self._create_directory(self.current_dir)
        self._create_directory(self.current_csv_dir)
        self.image_format = args.image_format
        logging.info(f"ImageSaver initialized with base_dir={base_dir} and image_format={self.image_format}")

    # def _get_next_directory(self):
    #     """Determine the next available directory."""
    #     i = 1
    #     while True:
    #         dir_name = f'predict{i}'
    #         path = os.path.join(self.base_dir, dir_name)
    #         if not os.path.exists(path):
    #             print(f"path : {path} is not exist, create it")
    #             # self.is_created = True
    #             return path
    #         i += 1

    def _get_next_directory(self):
        """Determine the next available directory or return an empty existing one."""
        i = 1
        while True:
            dir_name = f'predict{i}'
            path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(path):
                print(f"path: {path} does not exist, creating it.")
                return path
            elif os.path.exists(path) and not os.listdir(path):
                print(f"path: {path} exists but is empty, using this directory.")
                return path
            i += 1


    def _get_next_csv_directory(self):
        """Determine the next available directory."""
        i = 1
        while True:
            dir_name = f'predict_csv{i}'
            path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(path):
                print(f"path: {path} does not exist, creating it.")
                return path
            elif os.path.exists(path) and not os.listdir(path):
                print(f"path: {path} exists but is empty, using this directory.")
                return path
            i += 1

    def _create_directory(self, path):
        """Create the directory if it does not exist."""
        if not os.path.exists(path):
            os.makedirs(path)


    def set_custom_directory(self, custom_dir):
        """Set a custom directory for saving images and logs."""
        self.custom_dir = custom_dir
        self._create_directory(self.custom_dir)
        logging.info(f"Custom directory set to {self.custom_dir}")


    def save_image(self, image, frame_ID):
        """Save the image to the current directory."""
        try:
            # Determine where to save the image
            save_dirs = self.custom_dir if self.custom_dir is not None else self.current_dir

            # logging.error(f"self.custom_dir is {self.custom_dir}")
            # logging.error(f"self.current_dir is {self.current_dir}")

            image_path = os.path.join(save_dirs, f'frame_{frame_ID}.{self.image_format}')
            success = cv2.imwrite(image_path, image)
            # if success:
            #     logging.info(f"Image saved to {image_path}")
            if not success:
                logging.error(f"Failed to save image to {image_path}")
        except Exception as e:
            logging.error(f"Error saving image: {e}")

    def save_json_log(self, json_log):
        """Save the JSON log to a CSV file."""
        csv_path = os.path.join(self.current_csv_dir, 'json_logs.csv')
        with open(csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([json.dumps(json_log)])
        # print(f"JSON log saved to {csv_path}")

    def save_video(self, output_filename='video.mp4', fps=7):
        """Encode the images in the current directory into a video file."""
        # Get list of image files in the directory
        image_files = sorted(Path(self.current_dir).glob(f'frame_*.{self.image_format}'))
        
        if not image_files:
            print("No images found to create a video.")
            return
        
        # Read the first image to get the size
        first_image = cv2.imread(str(image_files[0]))
        height, width, _ = first_image.shape
        
        # Create VideoWriter object
        video_path = os.path.join(self.current_dir, output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        
        # Write images to video
        for image_file in image_files:
            img = cv2.imread(str(image_file))
            video_writer.write(img)
        
        video_writer.release()




# Usage example
# if __name__ == "__main__":
#     image_saver = ImageSaver()

    # Example usage:
    # image = cv2.imread('example.png')  # Load or generate your image
    # json_log = {"frame_ID": {"123": {"detectObj": {"VEHICLE": []}, "tailingObj": [], "vanishLineY": []}}}
    # frame_ID = "123"
    
    # image_saver.save_image(image, frame_ID)
    # image_saver.save_json_log(json_log, frame_ID)
