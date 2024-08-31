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
        self.frame_ids = []
        self.distances = []
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [])  # Initialize a line object
        self.ax.set_title("Frame ID vs. Distance to Camera")
        self.ax.set_xlabel("Frame ID")
        self.ax.set_ylabel("Distance to Camera")
        self.start_time = time.time()
        self.elapsed_time = time.time()
        logging.info("📊 DynamicPlotter initialized!")

    def extract_distance_to_camera_txt(self, file_path, time_limit):
        """
        Extracts frame ID and corresponding distance to the camera from a given JSON file,
        and dynamically plots the values as they are collected. Stops after a time limit.
        """
        # logging.info("🚀 Starting data extraction from JSON log...")
        # start_time = time.time()  # Start time for the timer
        # elapsed_time = 0  # Initialize elapsed time

        # # Initialize progress bar with tqdm, setting the bar length to 50 characters
        # with tqdm(total=time_limit, desc="Processing Data", unit="s", ncols=75) as pbar:
        with open(file_path, 'r') as file:
            for line in file:
                self.elapsed_time = time.time() - self.start_time
                # Check if the time limit has been reached
                if self.elapsed_time > time_limit:
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
                            self.frame_ids.append(int(frame_id))
                            self.distances.append(distance)
                            
                except json.JSONDecodeError as e:
                    logging.error(f"❗ Error parsing JSON: {e}")
                except KeyError as e:
                    logging.error(f"🔑 Key error: {e}")
            

            # Update plot
            self.update_plot()
            # # Update progress bar
            # pbar.update(round(elapsed_time, 3) - pbar.n)  # Update progress bar by the time elapsed since last update
            
        return False

        logging.info("📈 Data extraction completed!")
        return False  # Indicate that the extraction was completed successfully

    def update_plot(self):
        """
        Updates the plot with new data points.
        """
        self.line.set_data(self.frame_ids, self.distances)
        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()  # Rescale plot to fit new data
        plt.pause(0.1)  # Pause to update the plot; you can adjust the pause time as needed

    def run(self, file_path, time_limit):
        """
        Reads data from the file and updates the plot dynamically for a limited time.
        """
        logging.info("🏃‍♂️ Running DynamicPlotter...")
        
        # Start a timer to close the plot after the specified time limit
        def close_plot():
            logging.info("🛑 Time limit reached. Closing the plot window...")
            plt.close(self.fig)
        
        # Set the timer
        timer = threading.Timer(time_limit, close_plot)
        timer.start()
        logging.info("📊 Data extraction and plotting started....")
        finished = self.extract_distance_to_camera_txt(file_path, time_limit)

        self.start_time = time.time()  # Start time for the timer
        # elapsed_time = 0  # Initialize elapsed time
        with tqdm(total=time_limit, desc="Processing Data", unit="s", ncols=75) as pbar:
            # Run the data extraction and plotting
            while not finished:
                self.frame_ids.clear()
                self.distances.clear()
                finished = self.extract_distance_to_camera_txt(file_path, time_limit)
                #logging.info("📊 Data extraction and plotting completed successfully.")

                # Update progress bar
                pbar.update(round(self.elapsed_time, 3) - pbar.n)  # Update progress bar by the time elapsed since last update

        
        plt.show()  # Show the plot window (will be closed by the timer if time_limit is reached)

        # Ensure the timer is canceled if the plotting completes early
        timer.cancel()
        logging.info("✅ Plot window closed. Run complete!")

# # Example usage
# plotter = DynamicPlotter()
# plotter.run("your_json_log_file_path.txt", time_limit=30)
