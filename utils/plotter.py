
from engine.BaseDataset import BaseDataset
from config.args import Args

import matplotlib.pyplot as plt
import json
import pandas as pd
import logging
import csv
import os
import glob
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Plotter(BaseDataset):

    def __init__(self,args):
        super().__init__(args)
        self.json_log_path = args.csv_file
        self.eval_save_jsonlog_dir = args.eval_save_jsonlog_dir
        self.save_plot = args.save_plot
        self.save_plot_dir = args.save_plot_dir
        self.type = None
        os.makedirs(self.save_plot_dir,exist_ok=True)
        self.display_init_params()

    def display_init_params(self):
        ascii_art = """
                ____  _       _   _                   
        |  _ \| |_   _| | | |_ __  _   _  ___  
        | |_) | | | | | | | | '_ \| | | |/ _ \ 
        |  __/| | |_| | |_| | | | | |_| | (_) |
        |_|   |_|\__,_|\___/|_| |_|\__, |\___/ 
                                |___/       

        """
        print(ascii_art)
        logging.info("🎯 Plotter Class Information 🎯")
        logging.info(f"📦 Class Name: {self.__class__.__name__}")
        logging.info(f"📝 Documentation: {self.__class__.__doc__}")
        logging.info(f"🔧 Module: {self.__module__}")
        logging.info(f"💡 Base Class: {self.__class__.__bases__}")
        logging.info("📂 Initialized Parameters:")
        logging.info(f"  📄 JSON Log Path:         {self.json_log_path}")
        logging.info(f"  📁 Evaluation Save Dir:   {self.eval_save_jsonlog_dir}")
        logging.info(f"  💾 Save Plot:             {self.save_plot}")
        logging.info(f"  📂 Save Plot Directory:   {self.save_plot_dir}")
        logging.info(f"  🔍 Type:                  {self.type if self.type else 'Not Set'}")
        logging.info("\n")

    def parse_GT_dist(self,GT_dist=None):
        if len(GT_dist.split("m"))== 2:
            print(GT_dist.split("m"))
            return 'static'
        else:
            print(GT_dist.split("m"))
            return 'dynamic'
            
    def plot_all_static_golden_dataset(self):
        search_dir_list = sorted(glob.glob(f'{self.eval_save_jsonlog_dir}/**/*'))
        for search_dir in search_dir_list:
            print(search_dir)
            front_ego = search_dir.split("/")[-1]
            print(f"front_ego:{front_ego}")
            data_type = self.parse_GT_dist(front_ego)
            print(f"self.type :{self.type}")
            self.type = os.path.basename(os.path.dirname(search_dir))
            
            if data_type=='static':
                self.plot_static_different_scenary_distance_value_on_each_frame_ID(ground_truth_distance=front_ego)
            else:
                self.plot_dynamic_different_scenary_distance_value_on_each_frame_ID(front_ego=front_ego)

    def plot_dynamic_different_scenary_distance_value_on_each_frame_ID(self,front_ego = None):
        plt.figure(figsize=(128, 72))
        plt.style.use('ggplot')

        search_dir = os.path.join(self.eval_save_jsonlog_dir,self.type, front_ego)
        print(f'plotter search_dir:{search_dir}')
        search_dir_path_list = glob.glob(f"{search_dir}/**/*.txt")
        for search_dir_path in search_dir_path_list:
            print(search_dir_path)
            file_name = os.path.basename(os.path.dirname(search_dir_path))
            scenary = file_name.split("_")[-1]
            print(f'scenary:{scenary}')
            self.json_log_path = search_dir_path
            frame_ids,distances = self.plot_distance_value_on_each_frame_ID_txt(show_plot=False)
           
            plt.plot(frame_ids, distances, label= f'{file_name} result')
        
        plt.xlabel('Frame ID', fontsize=20)
        plt.ylabel('Tailing Object Distance to Camera', fontsize=20)
        plt.title(f'Front-Ego = {front_ego}', fontsize=24)
        plt.legend(fontsize=32)  # Adjust legend font size
        plt.xticks(fontsize=14)  # Adjust x-axis tick font size
        plt.yticks(fontsize=14)  # Adjust y-axis tick font size


        plt.grid(True)
        
        # Ensure labels are shown by adding a legend
        plt.legend()
        
        if self.save_plot:
            # Save the plot as a .jpg or .png file
            save_path = os.path.join(self.save_plot_dir, str(front_ego)+'m.jpg')
            plt.savefig(save_path,dpi=10,format='jpg')  # Change 'png' to 'jpg' for JPEG format
        
        # Show the plot
        plt.show()

    def plot_static_different_scenary_distance_value_on_each_frame_ID(self,ground_truth_distance = None):
        plt.figure(figsize=(128, 72))
        GT_dist = int(ground_truth_distance.split('m')[0])
        GT_dist_int = int(GT_dist)
        GT_frame_ids = []
        GT_dists = []
        plt.style.use('ggplot')  # 'ggplot' style often has more saturated colors
        GT_frame_ids = list(range(400))  # Ensure it's a flat list
        GT_dists = [GT_dist] * 400  # Ensure it's a flat list

        # Plot the ground truth data
        plt.plot(GT_frame_ids, GT_dists, label='GT:' + str(GT_dist), color='blue')

        # Add shaded range for GT values
        plt.fill_between(GT_frame_ids, GT_dist_int-5, GT_dist_int+5, color='blue', alpha=0.15, label=f'Accept distance range {GT_dist_int-5} to {GT_dist_int+5}')
        print(f'GT_dist:{GT_dist}')
        
        search_dir = os.path.join(self.eval_save_jsonlog_dir,self.type, ground_truth_distance)
        print(f'plotter search_dir:{search_dir}')
        search_dir_path_list = glob.glob(f"{search_dir}/**/*.txt")
        for search_dir_path in search_dir_path_list:
            print(search_dir_path)
            file_name = os.path.basename(os.path.dirname(search_dir_path))
            scenary = file_name.split("_")[-1]
            print(f'scenary:{scenary}')
            self.json_log_path = search_dir_path
            frame_ids,distances = self.plot_distance_value_on_each_frame_ID_txt(show_plot=False)
           
            plt.plot(frame_ids, distances, label= f'{file_name} result')
        
        plt.xlabel('Frame ID', fontsize=20)
        plt.ylabel('Tailing Object Distance to Camera', fontsize=20)
        plt.title(f'Static Ground Truth = {GT_dist}m', fontsize=24)
        plt.legend(fontsize=32)  # Adjust legend font size
        plt.xticks(fontsize=14)  # Adjust x-axis tick font size
        plt.yticks(fontsize=14)  # Adjust y-axis tick font size


        plt.grid(True)
        
        # Ensure labels are shown by adding a legend
        plt.legend()
        
        if self.save_plot:
            # Save the plot as a .jpg or .png file
            save_path = os.path.join(self.save_plot_dir, 'GT_'+str(GT_dist)+'m.jpg')
            plt.savefig(save_path,dpi=10,format='jpg')  # Change 'png' to 'jpg' for JPEG format
        
        # Show the plot
        plt.show()

    def plot_distance_value_on_each_frame_ID_txt(self,show_plot=True):
        # Read the JSON log from the text file
        with open(self.json_log_path, 'r') as file:
            lines = file.readlines()

        # Initialize lists for frame_ID and distanceToCamera
        frame_ids = []
        distances = []

        # Parse each JSON entry
        for index, line in enumerate(lines):
            try:
                # Convert JSON string to dictionary
                json_data = json.loads(line)
                # Extract frame_ID and tailingObj.distanceToCamera
                for frame_id, content in json_data["frame_ID"].items():
                    frame_ids.append(int(frame_id))
                    # Extract distanceToCamera, handling potential missing data
                    tailing_obj_list = content.get("tailingObj", [{}])
                    if tailing_obj_list:
                        distances.append(tailing_obj_list[0].get("tailingObj.distanceToCamera", None))
                    else:
                        distances.append(None)
            except json.JSONDecodeError:
                print(f"Error decoding JSON at line {index + 1}")

        if show_plot:

            # Plot the data
            plt.figure(figsize=(200, 100))
            plt.plot(frame_ids, distances, linestyle='-', color='b')
            plt.xlabel('Frame ID')
            plt.ylabel('Tailing Object Distance to Camera')
            plt.title('Tailing Object Distance to Camera vs Frame ID')
            plt.grid(True)
            plt.show()
            return frame_ids,distances
        else:
            return frame_ids,distances




    def plot_distance_value_on_each_frame_ID_csv(self):
        # Read the CSV file
        data = pd.read_csv(self.csv_file_path, header=None, names=['json'])

        # Initialize lists for frame_ID and distanceToCamera
        frame_ids = []
        distances = []

        # Parse each JSON entry
        for index, row in data.iterrows():
            json_str = row['json']
            try:
                # Convert JSON string to dictionary
                json_data = json.loads(json_str)
                # Extract frame_ID and tailingObj.distanceToCamera
                for frame_id, content in json_data["frame_ID"].items():
                    frame_ids.append(int(frame_id))
                    # Extract distanceToCamera, handling potential missing data
                    distances.append(content.get("tailingObj", [{}])[0].get("tailingObj.distanceToCamera", None))
            except json.JSONDecodeError:
                print(f"Error decoding JSON at row {index}")

        # Plot the data
        plt.figure(figsize=(200, 100))
        plt.plot(frame_ids, distances, linestyle='-', color='b')
        plt.xlabel('Frame ID')
        plt.ylabel('Tailing Object Distance to Camera')
        plt.title('Tailing Object Distance to Camera vs Frame ID')
        plt.grid(True)
        plt.show()

    

    def plot_distance_in_one_csv_file(self):
        plt.figure(figsize=(200, 100))
        frame_ids, distances = self.extract_distance_data(self.csv_file_path)
        plt.plot(frame_ids, distances, label=self.plot_label)
        plt.xlabel('FrameID')
        plt.ylabel('tailingObj.distanceToCamera')
        plt.title('Distance to Camera over Frames')
        plt.legend()
        plt.grid(True)

        plt.show()


    def compare_distance_in_two_csv_file(self):
        return NotImplemented
    
    def compare_distance_in_multiple_csv_file(self):
        i = 0
        plt.figure(figsize=(200, 100))

        for csv_file  in self.csv_file_list:
            frame_ids, distances = self.extract_distance_data(csv_file)
            plt.plot(frame_ids, distances, label=self.list_label[i])
            i += 1

        plt.xlabel('FrameID')
        plt.ylabel('tailingObj.distanceToCamera')
        plt.title('Distance to Camera over Frames')
        plt.legend()
        plt.grid(True)

        plt.show()
    """
        function : extract_distance_data
        Extracts frame IDs and distance values from a CSV file containing JSON data.

        The function reads a CSV file where each row contains JSON data prefixed with 'json:'. It parses the JSON data
        to extract the frame IDs and the distance values to the camera associated with each frame. 

        Parameters:
        - csv_file (str): The path to the CSV file containing the data.

        Returns:
        - Tuple[List[int], List[float]]:
            - frame_ids (List[int]): A list of frame IDs extracted from the JSON data.
            - distances (List[float]): A list of distances to the camera corresponding to each frame ID.
        
        Process:
        1. Initializes empty lists for `frame_ids` and `distances`.
        2. Opens the specified CSV file for reading.
        3. Iterates over each row in the CSV file:
            - Joins the row elements into a single string.
            - Searches for the 'json:' prefix to locate the start of the JSON data.
            - Extracts and cleans the JSON data, removing any extra quotes and handling escaped characters.
            - Parses the JSON data using `json.loads`.
            - Extracts `frame_ID` and `distanceToCamera` values:
                - Appends frame IDs and corresponding distances to the lists.
                - Handles missing or invalid distance values by appending `float('nan')`.
            - Logs any errors encountered during JSON parsing.
        
        Example:
        If the CSV file contains rows like:
        "1, ..., json:{\"frame_ID\":{\"1\":{\"tailingObj\":[{\"tailingObj.distanceToCamera\":12.5}]}}}"
        The function will parse this JSON to extract `frame_ID` as `1` and `distanceToCamera` as `12.5`.

        Logs:
        - Logs each row read from the CSV file.
        - Logs parsed JSON data.
        - Logs any JSON decoding errors or unexpected exceptions.

    """
    def extract_distance_data(self,csv_file):
    
        frame_ids = []
        distances = []

        with open(csv_file, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            for row in reader:
                # Debug print for each row
                logging.info(f"Row: {row}")

                # Join the row into a single string
                row_str = ','.join(row)
                
                # Find the position of 'json:'
                json_start = row_str.find('json:')
                if json_start != -1:
                    json_data = row_str[json_start + 5:].strip()
                    if json_data.startswith('"') and json_data.endswith('"'):
                        json_data = json_data[1:-1]  # Remove enclosing double quotes
                    
                    # Replace any double quotes escaped with backslashes
                    json_data = json_data.replace('\\"', '"')
                    
                    try:
                        data = json.loads(json_data)
                        logging.info(f"Parsed JSON: {data}")

                        for frame_id, frame_data in data['frame_ID'].items():
                            frame_ids.append(int(frame_id))
                            tailing_objs = frame_data.get('tailingObj', [])
                            if tailing_objs:
                                distance_to_camera = tailing_objs[0].get('tailingObj.distanceToCamera', None)
                                if distance_to_camera is not None:
                                    distances.append(distance_to_camera)
                                else:
                                    distances.append(float('nan'))  # Handle missing values
                            else:
                                distances.append(float('nan'))  # Handle missing values
                    except json.JSONDecodeError as e:
                        logging.info(f"Error decoding JSON: {e}")
                    except Exception as e:
                        logging.info(f"Unexpected error: {e}")

        return frame_ids, distances
    
    def extract_distance_to_camera_txt(self, file_path):
        frame_ids = []
        distances = []

        with open(file_path, 'r') as file:
            for line in file:
                try:
                    data = json.loads(line.strip())
                    # Extracting frame ID and its associated data
                    for frame_id, frame_data in data["frame_ID"].items():
                        # Accessing the 'tailingObj' data
                        tailing_obj = frame_data.get("tailingObj", [{}])[0]
                        distance = tailing_obj.get("tailingObj.distanceToCamera", None)
                        if distance is not None:
                            frame_ids.append(int(frame_id))
                            distances.append(distance)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                except KeyError as e:
                    print(f"Key error: {e}")

        return frame_ids, distances
    
    def plot_distances(self, file1, file2):
        # Extract distances and frame IDs from both files
        frame_ids1, distances1 = self.extract_distance_to_camera_txt(file1)
        frame_ids2, distances2 = self.extract_distance_to_camera_txt(file2)

        # Plot the distances
        plt.figure(figsize=(24, 12))
        plt.plot(frame_ids1, distances1, label='Historical mode', marker='o')
        plt.plot(frame_ids2, distances2, label='Live mode', marker='x')

        plt.xlabel('Frame ID')
        plt.ylabel('tailingObj.distanceToCamera')
        plt.title('Distance to Camera per Frame')
        plt.legend()
        plt.grid(True)
        
        # Save the plot as a file
        plt.savefig('distance_to_camera_plot.png')
        print("Plot saved as 'distance_to_camera_plot.png'")



    def extract_distance_to_camera_txt_ver2(self, file_path):
        frame_distances = {}

        with open(file_path, 'r') as file:
            for line in file:
                try:
                    data = json.loads(line.strip())
                    for frame_id, frame_data in data["frame_ID"].items():
                        tailing_obj = frame_data.get("tailingObj", [{}])[0]
                        distance = tailing_obj.get("tailingObj.distanceToCamera", None)
                        if distance is not None:
                            frame_distances[int(frame_id)] = distance
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                except KeyError as e:
                    print(f"Key error: {e}")

        return frame_distances

    def calculate_match_rate(self, file1, file2, tolerance=0.0):
        # Extract distances for each file
        distances1 = self.extract_distance_to_camera_txt_ver2(file1)
        distances2 = self.extract_distance_to_camera_txt_ver2(file2)

        # Initialize counters
        match_count = 0
        total_count = 0

        # Compare distances for each frame ID
        for frame_id in distances1:
            if frame_id in distances2:
                total_count += 1
                if abs(distances1[frame_id] - distances2[frame_id]) <= tolerance:
                    match_count += 1

        # Calculate match rate
        if total_count == 0:
            return 0.0  # Avoid division by zero
        match_rate = (match_count / total_count) * 100
        return match_rate