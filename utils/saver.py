import os
import cv2
import json
import csv

class ImageSaver:
    def __init__(self, base_dir='runs'):
        self.base_dir = base_dir
        self.current_dir = self._get_next_directory()
        self._create_directory(self.current_dir)
    
    def _get_next_directory(self):
        """Determine the next available directory."""
        i = 1
        cout = 0
        while True:
            dir_name = f'predict{i}'
            path = os.path.join(self.base_dir, dir_name)
            if not os.path.exists(path):
                return path
            cout += 1
            if cout % 3 == 0:
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

    def save_json_log(self, json_log, frame_ID):
        """Save the JSON log to a CSV file."""
        csv_path = os.path.join(self.current_dir, 'json_logs.csv')
        with open(csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([frame_ID, json.dumps(json_log)])
        print(f"JSON log saved to {csv_path}")

# Usage example
if __name__ == "__main__":
    image_saver = ImageSaver()

    # Example usage:
    # image = cv2.imread('example.png')  # Load or generate your image
    # json_log = {"frame_ID": {"123": {"detectObj": {"VEHICLE": []}, "tailingObj": [], "vanishLineY": []}}}
    # frame_ID = "123"
    
    # image_saver.save_image(image, frame_ID)
    # image_saver.save_json_log(json_log, frame_ID)
