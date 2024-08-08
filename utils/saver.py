import os
import cv2
import json
import csv
from pathlib import Path

class ImageSaver:
    def __init__(self, base_dir='runs'):
        self.base_dir = base_dir
        self.current_dir = self._get_next_directory()
        self.current_csv_dir = self._get_next_csv_directory()
        self._create_directory(self.current_dir)
        self._create_directory(self.current_csv_dir)
    
    def _get_next_directory(self):
        """Determine the next available directory."""
        i = 1
        while True:
            dir_name = f'predict{i}'
            path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(path):
                return path
            i += 1
    
    def _get_next_csv_directory(self):
        """Determine the next available directory."""
        i = 1
        while True:
            dir_name = f'predict_csv{i}'
            path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(path):
                return path
            i += 1

    def _create_directory(self, path):
        """Create the directory if it does not exist."""
        if not os.path.exists(path):
            os.makedirs(path)
    
    def save_image(self, image, frame_ID):
        """Save the image to the current directory."""
        image_path = os.path.join(self.current_dir, f'frame_{frame_ID}.png')
        cv2.imwrite(image_path, image)
        print(f"Image saved to {image_path}")

    def save_json_log(self, json_log):
        """Save the JSON log to a CSV file."""
        csv_path = os.path.join(self.current_csv_dir, 'json_logs.csv')
        with open(csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([json.dumps(json_log)])
        print(f"JSON log saved to {csv_path}")
    
    def save_video(self, output_filename='video.mp4', fps=7):
        """Encode the images in the current directory into a video file."""
        # Get list of image files in the directory
        image_files = sorted(Path(self.current_dir).glob('frame_*.png'))
        
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
        print(f"Video saved to {video_path}")




# Usage example
# if __name__ == "__main__":
#     image_saver = ImageSaver()

    # Example usage:
    # image = cv2.imread('example.png')  # Load or generate your image
    # json_log = {"frame_ID": {"123": {"detectObj": {"VEHICLE": []}, "tailingObj": [], "vanishLineY": []}}}
    # frame_ID = "123"
    
    # image_saver.save_image(image, frame_ID)
    # image_saver.save_json_log(json_log, frame_ID)
