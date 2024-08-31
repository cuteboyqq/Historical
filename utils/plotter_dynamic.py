import json
import matplotlib.pyplot as plt
import time  # Import time module
import logging  # Import logging for info statements
from tqdm import tqdm  # Import tqdm for progress bar

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
        logging.info("📊 DynamicPlotter initialized!")

    def extract_distance_to_camera_txt(self, file_path, time_limit):
        """
        Extracts frame ID and corresponding distance to the camera from a given JSON file,
        and dynamically plots the values as they are collected. Stops after a time limit.
        """
        logging.info("🚀 Starting data extraction from JSON log...")
        start_time = time.time()  # Start time for the timer
        elapsed_time = 0  # Initialize elapsed time

        # Initialize progress bar with tqdm, setting the bar length to 50 characters
        with tqdm(total=time_limit, desc="Processing Data", unit="s", ncols=75) as pbar:
            with open(file_path, 'r') as file:
                for line in file:
                    elapsed_time = time.time() - start_time
                    # Check if the time limit has been reached
                    if elapsed_time > time_limit:
                        logging.info("⏰ Time limit reached. Stopping data extraction.")
                        break

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
                                # Update plot
                                self.update_plot()
                    except json.JSONDecodeError as e:
                        logging.error(f"❗ Error parsing JSON: {e}")
                    except KeyError as e:
                        logging.error(f"🔑 Key error: {e}")

                    # Update progress bar
                    pbar.update(round(elapsed_time,3) - pbar.n)  # Update progress bar by the time elapsed since last update

        logging.info("📈 Data extraction completed!")

    def update_plot(self):
        """
        Updates the plot with new data points.
        """
        self.line.set_data(self.frame_ids, self.distances)
        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()  # Rescale plot to fit new data
        plt.pause(0.5)  # Pause to update the plot; you can adjust the pause time as needed
        # logging.info("🖼️ Plot updated with new data points.")

    def run(self, file_path, time_limit=30):
        """
        Reads data from the file and updates the plot dynamically for a limited time.
        """
        logging.info("🏃‍♂️ Running DynamicPlotter...")
        self.extract_distance_to_camera_txt(file_path, time_limit)
        logging.info("🛑 Showing plot window. Run complete!")
        plt.show()  # Show the plot window

# # Example usage
# plotter = DynamicPlotter()
# plotter.run("path/to/your/json_log.txt", time_limit=30)  # Runs for 30 seconds
