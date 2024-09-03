import json
import matplotlib.pyplot as plt
import time
import logging
from tqdm import tqdm
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DynamicPlotter:
    def __init__(self):
        self.frame_ids_1 = []  # Separate frame IDs for first file
        self.distances_1 = []  # Distances for first file
        self.frame_ids_2 = []  # Separate frame IDs for second file
        self.distances_2 = []  # Distances for second file
        self.fig, self.ax = plt.subplots()  # Initialize plot figure and axes
        # Initialize lines with different styles for better visibility
        self.line1, = self.ax.plot([], [], label="Distance from live mode", linestyle='-', marker='o', color='blue')  
        self.line2, = self.ax.plot([], [], label="Distance from historical mode", linestyle='--', marker='x', color='orange') 
        self.ax.set_title("Frame ID vs. Distance to Camera")
        self.ax.set_xlabel("Frame ID")
        self.ax.set_ylabel("Distance to Camera")
        self.ax.legend()  # Show legend to differentiate the two lines
        self.start_time = time.time()
        logging.info("📊 DynamicPlotter initialized!")

    def extract_distance_to_camera_txt(self, file_path1, file_path2=None, time_limit=60):
        """
        Extracts frame ID and corresponding distances to the camera from two given JSON files,
        and dynamically plots the values as they are collected. Stops after a time limit.
        """
        # Process the first file
        with open(file_path1, 'r') as file1:
            for line in file1:
                elapsed_time = time.time() - self.start_time
                # Check if the time limit has been reached
                if elapsed_time > time_limit:
                    logging.info("⏰ Time limit reached. Stopping data extraction.")
                    return True

                try:
                    data = json.loads(line.strip())
                    # Extracting frame ID and its associated data
                    for frame_id, frame_data in data["frame_ID"].items():
                        # Accessing the 'tailingObj' data
                        tailing_obj = frame_data.get("tailingObj", [{}])[0]
                        distance = tailing_obj.get("tailingObj.distanceToCamera", None)
                        if distance is not None:
                            self.frame_ids_1.append(int(frame_id))
                            self.distances_1.append(distance)  # Append to first series

                except json.JSONDecodeError as e:
                    logging.error(f"❗ Error parsing JSON from file 1: {e}")
                except KeyError as e:
                    logging.error(f"🔑 Key error from file 1: {e}")

        if file_path2 is not None:
            # Process the second file
            with open(file_path2, 'r') as file2:
                for line in file2:
                    elapsed_time = time.time() - self.start_time
                    # Check if the time limit has been reached
                    if elapsed_time > time_limit:
                        logging.info("⏰ Time limit reached. Stopping data extraction.")
                        return True

                    try:
                        data = json.loads(line.strip())
                        # Extracting frame ID and its associated data
                        for frame_id, frame_data in data["frame_ID"].items():
                            # Accessing the 'tailingObj' data
                            tailing_obj = frame_data.get("tailingObj", [{}])[0]
                            distance = tailing_obj.get("tailingObj.distanceToCamera", None)
                            if distance is not None:
                                self.frame_ids_2.append(int(frame_id))
                                self.distances_2.append(distance)  # Append to second series

                    except json.JSONDecodeError as e:
                        logging.error(f"❗ Error parsing JSON from file 2: {e}")
                    except KeyError as e:
                        logging.error(f"🔑 Key error from file 2: {e}")

        # Update plot
        self.update_plot()
        return False

    def update_plot(self):
        """
        Updates the plot with new data points.
        """
        # Ensure that frame IDs and distances are not empty and have the same length
        if self.frame_ids_2 and len(self.frame_ids_2) == len(self.distances_2):
            self.line2.set_data(self.frame_ids_2, self.distances_2)


        if self.frame_ids_1 and len(self.frame_ids_1) == len(self.distances_1):
            self.line1.set_data(self.frame_ids_1, self.distances_1)
            

        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()  # Rescale plot to fit new data
        plt.pause(0.1)  # Pause to update the plot; you can adjust the pause time as needed

    def run(self, file_path1, file_path2, time_limit, mode='live'):
        """
        Reads data from two files and updates the plot dynamically for a limited time.
        """
        logging.info("🏃‍♂️ Running DynamicPlotter...")
        self.ax.set_title(f"{mode} mode: Frame ID vs. Distance to Camera")
        
        # Start a timer to close the plot after the specified time limit
        def close_plot():
            logging.info("🛑 Time limit reached. Closing the plot window...")
            plt.close(self.fig)
        
        # Set the timer
        timer = threading.Timer(time_limit, close_plot)
        timer.start()
        logging.info("📊 Data extraction and plotting started....")
        finished = self.extract_distance_to_camera_txt(file_path1, file_path2, time_limit)

        self.start_time = time.time()  # Start time for the timer
        with tqdm(total=time_limit, desc="Processing Data", unit="s", ncols=75) as pbar:
            # Run the data extraction and plotting
            while not finished:
                self.frame_ids_1.clear()
                self.distances_1.clear()
                self.frame_ids_2.clear()
                self.distances_2.clear()
                finished = self.extract_distance_to_camera_txt(file_path1, file_path2, time_limit)
                # Save the plot to a file if extraction is finished
                if finished:
                    self.fig.savefig(f'distance_to_camera_plot_{mode}.png')
                    logging.info(f"🖼️ Plot saved as 'distance_to_camera_plot_{mode}.png'.")
                # Update progress bar
                elapsed_time = time.time() - self.start_time
                pbar.update(round(elapsed_time, 3) - pbar.n)  # Update progress bar by the time elapsed since last update

        # Show the plot window (it will be closed by the timer if time_limit is reached)
        plt.show()
        # Ensure the timer is canceled if the plotting completes early
        timer.cancel()
        logging.info("✅ Plot window closed. Run complete!")

# Example usage
# plotter = DynamicPlotter()
# plotter.run("path_to_file1.txt", "path_to_file2.txt", time_limit=30)








# import json
# import matplotlib.pyplot as plt
# import time
# import logging
# from tqdm import tqdm
# import threading

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class DynamicPlotter:
#     def __init__(self):
#         self.frame_ids = []
#         self.distances = []
#         self.fig, self.ax = plt.subplots()
#         self.line, = self.ax.plot([], [])  # Initialize a line object
#         self.ax.set_title("Frame ID vs. Distance to Camera")
#         self.ax.set_xlabel("Frame ID")
#         self.ax.set_ylabel("Distance to Camera")
#         self.start_time = time.time()
#         self.elapsed_time = time.time()
#         logging.info("📊 DynamicPlotter initialized!")

#     def extract_distance_to_camera_txt(self, file_path, time_limit):
#         """
#         Extracts frame ID and corresponding distance to the camera from a given JSON file,
#         and dynamically plots the values as they are collected. Stops after a time limit.
#         """
#         # logging.info("🚀 Starting data extraction from JSON log...")
#         # start_time = time.time()  # Start time for the timer
#         # elapsed_time = 0  # Initialize elapsed time

#         # # Initialize progress bar with tqdm, setting the bar length to 50 characters
#         # with tqdm(total=time_limit, desc="Processing Data", unit="s", ncols=75) as pbar:
#         with open(file_path, 'r') as file:
#             for line in file:
#                 self.elapsed_time = time.time() - self.start_time
#                 # Check if the time limit has been reached
#                 if self.elapsed_time > time_limit:
#                     logging.info("⏰ Time limit reached. Stopping data extraction.")
#                     return True

#                 try:
#                     data = json.loads(line.strip())
#                     # Extracting frame ID and its associated data
#                     for frame_id, frame_data in data["frame_ID"].items():
#                         # Accessing the 'tailingObj' data
#                         tailing_obj = frame_data.get("tailingObj", [{}])[0]
#                         distance = tailing_obj.get("tailingObj.distanceToCamera", None)
#                         if distance is not None:
#                             self.frame_ids.append(int(frame_id))
#                             self.distances.append(distance)
                            
#                 except json.JSONDecodeError as e:
#                     logging.error(f"❗ Error parsing JSON: {e}")
#                 except KeyError as e:
#                     logging.error(f"🔑 Key error: {e}")
            

#             # Update plot
#             self.update_plot()
#             # # Update progress bar
#             # pbar.update(round(elapsed_time, 3) - pbar.n)  # Update progress bar by the time elapsed since last update
            
#         return False

#         logging.info("📈 Data extraction completed!")
#         return False  # Indicate that the extraction was completed successfully

#     def update_plot(self):
#         """
#         Updates the plot with new data points.
#         """
#         self.line.set_data(self.frame_ids, self.distances)
#         self.ax.relim()  # Recalculate limits
#         self.ax.autoscale_view()  # Rescale plot to fit new data
#         plt.pause(0.1)  # Pause to update the plot; you can adjust the pause time as needed

#     def run(self, file_path, time_limit, mode='live'):
#         """
#         Reads data from the file and updates the plot dynamically for a limited time.
#         """
#         logging.info("🏃‍♂️ Running DynamicPlotter...")
#         self.ax.set_title(f" {mode} mode : Frame ID vs. Distance to Camera")
#         # Start a timer to close the plot after the specified time limit
#         def close_plot():
#             logging.info("🛑 Time limit reached. Closing the plot window...")
#             plt.close(self.fig)
        
#         # Set the timer
#         timer = threading.Timer(time_limit, close_plot)
#         timer.start()
#         logging.info("📊 Data extraction and plotting started....")
#         finished = self.extract_distance_to_camera_txt(file_path, time_limit)

#         self.start_time = time.time()  # Start time for the timer
#         # elapsed_time = 0  # Initialize elapsed time
#         with tqdm(total=time_limit, desc="Processing Data", unit="s", ncols=75) as pbar:
#             # Run the data extraction and plotting
#             while not finished:
#                 self.frame_ids.clear()
#                 self.distances.clear()
#                 finished = self.extract_distance_to_camera_txt(file_path, time_limit)
#                 #logging.info("📊 Data extraction and plotting completed successfully.")
#                 # self.update_plot()
#                 # Save the plot to a file if extraction is finished
#                 if finished:
#                     self.fig.savefig(f'distance_to_camera_plot_{mode}.png')
#                     logging.info(f"🖼️ Plot saved as 'distance_to_camera_plot_{mode}.png'.")
#                 # Update progress bar
#                 pbar.update(round(self.elapsed_time, 3) - pbar.n)  # Update progress bar by the time elapsed since last update

    
#         # Show the plot window (it will be closed by the timer if time_limit is reached)
#         plt.show()
#         # Ensure the timer is canceled if the plotting completes early
#         timer.cancel()
#         logging.info("✅ Plot window closed. Run complete!")

# # # Example usage
# # plotter = DynamicPlotter()
# # plotter.run("your_json_log_file_path.txt", time_limit=30)