import threading
import queue
import matplotlib.pyplot as plt
import logging
import time
from tqdm import tqdm

class LiveModeRunner:
    def __init__(self):
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()

    def run_live_mode(self):
        logging.info("🔧 Configuring live mode settings...")
        
        def start_server_thread(draw, folder_name, visual_mode):
            logging.info(f"🚀 Starting server thread with folder name: {folder_name}")
            self.Connect.start_server(draw_jsonlog=draw, save_folder=folder_name, visual_mode=visual_mode)
            logging.info("📡 Server thread started successfully.")

        def collect_data_thread(json_log_path):
            # Collect data and put it in the queue
            logging.info("📈 Collecting data for dynamic plotting...")
            self.collect_data(json_log_path)
        
        def plot_dynamic():
            plt.ion()  # Enable interactive mode
            fig, ax = plt.subplots()
            line, = ax.plot([], [], 'b-')

            while not self.stop_event.is_set():
                try:
                    # Get data from queue
                    frame_ids, distances = self.data_queue.get(timeout=1)
                    line.set_xdata(frame_ids)
                    line.set_ydata(distances)
                    ax.relim()
                    ax.autoscale_view()
                    plt.draw()
                    plt.pause(0.1)
                except queue.Empty:
                    continue

        self.varify_device_input_mode = 0  # live mode
        self.varify_enable_save_raw_images = 1  # enable save raw images
        self.visualize_mode = 1  # semi-online

        logging.info("📝 Modifying configuration file for live mode...")
        self.modify_config_file()

        logging.info("🧵 Starting the server in a separate thread...")
        server_th = threading.Thread(target=start_server_thread, args=(False, str(self.date_time), "semi-online",))
        server_th.start()

        logging.info("🚗 Running the ADAS system in live mode...")
        self.run_the_adas()

        json_log_path = f"{self.curret_dir}/runs/{self.date_time}/{self.date_time}.txt"
        data_th = threading.Thread(target=collect_data_thread, args=(json_log_path,))
        data_th.start()

        logging.info("📊 Starting dynamic plotting in the main thread...")
        plot_dynamic()  # Run in main thread

        t = self.varify_run_historical_time
        logging.info(f"⏳ Running live mode for {t} seconds with progress...")

        for _ in tqdm(range(t), desc=f"⏳ Running live Mode and saving raw images", unit="s"):
            time.sleep(1)

        logging.info(f"🏁 Completed {t} seconds. Stopping the ADAS system...")
        self.stop_run_adas()
        logging.info("🏁 ADAS system stopped successfully!")

        logging.info("🛑 Stopping the server and finishing the thread...")
        self.Connect.stop_server.set()

        # Ensure the server thread finishes before proceeding
        server_th.join()
        logging.info("✅ Server thread has stopped successfully.")

        # Set the event to stop plotting
        self.stop_event.set()

        logging.info(f"📂 Moving files to {self.curret_dir}/assets/{str(self.date_time)}/{str(self.date_time)}.txt")
        self.move_file(f"{self.curret_dir}/runs/{str(self.date_time)}")

        self.live_mode_txt_file = f"{self.curret_dir}/runs/{str(self.date_time)}/{str(self.date_time)}.txt"
        logging.info(f"💾 Live mode JSON log file saved at: {self.live_mode_txt_file}")

    def collect_data(self, json_log_path):
        # Simulate data collection
        """
        Extracts frame ID and corresponding distance to the camera from a given JSON file,
        and dynamically plots the values as they are collected.
        """
        frame_ids, distances = [], []
        with open(json_log_path, 'r') as file:
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
                            self.data_queue.put((frame_ids, distances))
                            time.sleep(0.5)  # Simulate some delay
                            # Update plot
                            self.update_plot()
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                except KeyError as e:
                    print(f"Key error: {e}")

