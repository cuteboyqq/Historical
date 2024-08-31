import os
from engine.BaseDataset import BaseDataset
import time
import logging
from utils.plotter import Plotter
from utils.connection import Connection
# from utils.connection_ver2 import ConnectionHandler
from datetime import datetime
import threading
from tqdm import tqdm
import paramiko
import datetime
import re
import json
import queue

import matplotlib
matplotlib.use('TkAgg')  # or 'Qt5Agg' or another GUI backend

print(matplotlib.rcsetup.all_backends)
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from utils.plotter_dynamic import DynamicPlotter


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

class Varify(BaseDataset):
    
    def __init__(self,args):
        super().__init__(args)
        self.varify_device_input_mode = None
        self.varify_video_path = ""
        self.varify_raw_image_dir = None
        self.varify_image_mode_start_frame = 0
        self.varify_image_mode_end_frame = 99999
        self.server_port = args.server_port
        self.server_ip = args.server_ip
        self.visualize_mode = 1
        self.varify_camera_config_file_path = args.varify_camera_config_file_path
        self.varify_enable_save_raw_images = None
        self.varify_camera_csv_file_dir = args.camera_csvfile_dir
        self.varify_run_historical_time = args.varify_run_historical_time
        self.varify_historical_mode_txt_file = None
        self.varify_live_mode_txt_file = None
        self.Plot = Plotter(args)
        self.Connect = Connection(args)
        self.tftpserver_dir = args.tftpserver_dir
        self.save_jsonlog_dir = args.varify_save_jsonlog_dir
        os.makedirs(self.save_jsonlog_dir,exist_ok=True)
        self.camera_rawimages_dir = args.camera_rawimages_dir
        self.camera_host_name = args.camera_host_name
        self.camera_port = args.camera_port
        self.camera_user_name = args.camera_user_name
        self.camera_password = args.camera_password
        self.closest_date_folder = None

        self.varify_raw_image_folder = None
        self.date_time = None

        self.curret_dir = os.getcwd()

        # Set up SSH client
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(self.camera_host_name, port=self.camera_port, username=self.camera_user_name, password=self.camera_password)


        self.plotter_dynamic = DynamicPlotter() 

        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.display_parameters()

    def display_varify_parameters(self):
        """
        Displays the categorized initialized parameters of the Varify class with emojis.
        """
        logging.info("🔍 Varify Class Parameters 🔍")
        
        # Input and Mode Settings
        logging.info("🎛️ **Input and Mode Settings:**")
        logging.info(f"  🖥️ Device Input Mode: {self.varify_device_input_mode}")
        logging.info(f"  🎥 Video Path: {self.varify_video_path}")
        logging.info(f"  🖼️ Raw Image Directory: {self.varify_raw_image_dir}")
        logging.info(f"  ⏳ Image Mode Start Frame: {self.varify_image_mode_start_frame}")
        logging.info(f"  ⏳ Image Mode End Frame: {self.varify_image_mode_end_frame}")
        logging.info(f"  👁️ Visualize Mode: {self.visualize_mode}")
        
        # Server Settings
        logging.info("🌐 **Server Settings:**")
        logging.info(f"  🌐 Server IP: {self.server_ip}")
        logging.info(f"  🔌 Server Port: {self.server_port}")
        
        # File Paths and Directories
        logging.info("📂 **File Paths and Directories:**")
        logging.info(f"  📁 Camera Config File Path: {self.varify_camera_config_file_path}")
        logging.info(f"  📂 Camera CSV File Directory: {self.varify_camera_csv_file_dir}")
        logging.info(f"  📦 TFTP Server Directory: {self.tftpserver_dir}")
        logging.info(f"  📂 Save JSON Log Directory: {self.save_jsonlog_dir}")
        
        # Historical and Live Mode
        logging.info("📅 **Historical and Live Mode Settings:**")
        logging.info(f"  ⏲️ Run Historical Time: {self.varify_run_historical_time}")
        logging.info(f"  📄 Historical Mode TXT File: {self.varify_historical_mode_txt_file}")
        logging.info(f"  📄 Live Mode TXT File: {self.varify_live_mode_txt_file}")
        
        # Objects
        logging.info("🔧 **Object Instances:**")
        logging.info(f"  📊 Plotter Object: {self.Plot}")
        logging.info(f"  🔗 Connection Object: {self.Connect}")

    def check_port_availability(self, port):

        """Check if a port is available on the remote server."""
        command = f"lsof -i:{port}"
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        output = stdout.read().decode().strip()
        return len(output) == 0


    def varify_historical_match_rate(self):
        logging.info("🕒 Setting the date and time...")
        self.date_time = self.set_date_time()

        is_in_use, pid, process_name = self.Connect.check_process_using_port(self.server_port)
        logging.info(f"✅ Port :{self.server_port} is in use :{is_in_use}")
        while is_in_use:
            logging.info(f"⚠️ Port {self.server_port} is in use by process {process_name} with PID {pid}.")
            # If in use, kill the process remotely via SSH
            kill_result = self.Connect.kill_process_remotely(pid)
            logging.info(f"🛑 Kill result: {kill_result}")
            
            # Increment port number to check the next one
            # self.connect.port += 1
            self.Connect.server_port = self.Connect.server_port + 1
            self.server_port = self.server_port + 1

            # Check the new port status
            is_in_use, pid, process_name = self.Connect.check_process_using_port(self.server_port)

        logging.info(f"✅ Port {self.server_port} is available.")


        logging.info("📡 Running device in live mode...")
        self.run_live_mode()

        logging.info("🔍 Finding the closest folder with raw images...")
        self.varify_raw_image_folder = self.find_closest_folder()
        self.varify_raw_image_dir = os.path.join(self.camera_rawimages_dir, self.varify_raw_image_folder)
        logging.info(f"📂 Closest folder in camera is {self.varify_raw_image_dir}")

        # logging.info("🔌 Checking if the server port is available...")
        # if self.check_port_availability(self.server_port):
        #     logging.error(f"🚫 Port {self.server_port} is already in use. Please resolve the conflict.")
        #     self.Connect.server_port = self.Connect.server_port + 1
        #     self.server_port = self.server_port + 1
        #     logging.warning(f"⚠️ Port conflict resolved by incrementing to {self.server_port}")
        # 🚀 Check if the server port is in use and get process details if so
        is_in_use, pid, process_name = self.Connect.check_process_using_port(self.server_port)
        logging.info(f"✅ Port :{self.server_port} is in use :{is_in_use}")
        while is_in_use:
            logging.info(f"⚠️ Port {self.server_port} is in use by process {process_name} with PID {pid}.")
            # If in use, kill the process remotely via SSH
            kill_result = self.Connect.kill_process_remotely(pid)
            logging.info(f"🛑 Kill result: {kill_result}")
            
            # Increment port number to check the next one
            # self.connect.port += 1
            self.Connect.server_port = self.Connect.server_port + 1
            self.server_port = self.server_port + 1

            # Check the new port status
            is_in_use, pid, process_name = self.Connect.check_process_using_port(self.server_port)

        logging.info(f"✅ Port {self.server_port} is available.")



        logging.info("🕰️ Running device in historical mode...")
        self.run_historical_mode()

        # Usage : Test plot
        # self.historical_mode_txt_file = "/home/ali/Projects/GitHub_Code/WNC/adas_evaluation_tools/src/assets/csv_file/varify/2024-8-23-10-35/2024-8-23-10-35.txt"
        # self.live_mode_txt_file = "/home/ali/Projects/GitHub_Code/WNC/adas_evaluation_tools/src/assets/csv_file/varify/2024.08.23-10:34:58/json_logs.txt"

        logging.info("📊 Plotting distances between historical and live mode...")
        self.Plot.plot_distances(self.historical_mode_txt_file, self.live_mode_txt_file)

        logging.info("🔄 Calculating match rate between historical and live mode...")
        match_rate = self.Plot.calculate_match_rate(self.historical_mode_txt_file, self.live_mode_txt_file, tolerance=0.0)
        logging.info(f"✅ Match rate calculated: {match_rate}")

    # def run_live_mode(self):
    #     logging.info("🔧 Configuring live mode settings...")
        
    #     def start_server_thread(draw, folder_name, visual_mode):
    #         logging.info(f"🚀 Starting server thread with folder name: {folder_name}")
    #         self.Connect.start_server(draw_jsonlog=draw, save_folder=folder_name, visual_mode=visual_mode)
    #         logging.info("📡 Server thread started successfully.")

    #     def collect_data_thread(json_log_path):
    #         # Collect data and put it in the queue
    #         logging.info("📈 Collecting data for dynamic plotting...")
    #         self.collect_data(json_log_path)
        
    #     def plot_dynamic():
    #         plt.ion()  # Enable interactive mode
    #         fig, ax = plt.subplots()
    #         line, = ax.plot([], [], 'b-')

    #         while not self.stop_event.is_set():
    #             try:
    #                 # Get data from queue
    #                 frame_ids, distances = self.data_queue.get(timeout=1)
    #                 line.set_xdata(frame_ids)
    #                 line.set_ydata(distances)
    #                 ax.relim()
    #                 ax.autoscale_view()
    #                 plt.draw()
    #                 plt.pause(0.1)
    #             except queue.Empty:
    #                 continue

    #     self.varify_device_input_mode = 0  # live mode
    #     self.varify_enable_save_raw_images = 1  # enable save raw images
    #     self.visualize_mode = 1  # semi-online

    #     logging.info("📝 Modifying configuration file for live mode...")
    #     self.modify_config_file()

    #     logging.info("🧵 Starting the server in a separate thread...")
    #     server_th = threading.Thread(target=start_server_thread, args=(False, str(self.date_time), "semi-online",))
    #     server_th.start()

    #     logging.info("🚗 Running the ADAS system in live mode...")
    #     self.run_the_adas()

    #     json_log_path = f"{self.curret_dir}/runs/{self.date_time}/{self.date_time}.txt"
    #     data_th = threading.Thread(target=collect_data_thread, args=(json_log_path,))
    #     data_th.start()

    #     logging.info("📊 Starting dynamic plotting in the main thread...")
    #     # plot_dynamic()  # Run in main thread
    #     self.plotter_dynamic.run(json_log_path)

    #     t = self.varify_run_historical_time
    #     logging.info(f"⏳ Running live mode for {t} seconds with progress...")

    #     for _ in tqdm(range(t), desc=f"⏳ Running live Mode and saving raw images", unit="s"):
    #         time.sleep(1)

    #     logging.info(f"🏁 Completed {t} seconds. Stopping the ADAS system...")
    #     self.stop_run_adas()
    #     logging.info("🏁 ADAS system stopped successfully!")

    #     logging.info("🛑 Stopping the server and finishing the thread...")
    #     self.Connect.stop_server.set()

    #     # Ensure the server thread finishes before proceeding
    #     server_th.join()
    #     logging.info("✅ Server thread has stopped successfully.")

    #     # Set the event to stop plotting
    #     self.stop_event.set()

    #     logging.info(f"📂 Moving files to {self.curret_dir}/assets/{str(self.date_time)}/{str(self.date_time)}.txt")
    #     self.move_file(f"{self.curret_dir}/runs/{str(self.date_time)}")

    #     self.live_mode_txt_file = f"{self.curret_dir}/runs/{str(self.date_time)}/{str(self.date_time)}.txt"
    #     logging.info(f"💾 Live mode JSON log file saved at: {self.live_mode_txt_file}")

    # def collect_data(self, json_log_path):
    #     # Simulate data collection
    #     """
    #     Extracts frame ID and corresponding distance to the camera from a given JSON file,
    #     and dynamically plots the values as they are collected.
    #     """
    #     frame_ids, distances = [], []
    #     with open(json_log_path, 'r') as file:
    #         for line in file:
    #             try:
    #                 data = json.loads(line.strip())
    #                 # Extracting frame ID and its associated data
    #                 for frame_id, frame_data in data["frame_ID"].items():
    #                     # Accessing the 'tailingObj' data
    #                     tailing_obj = frame_data.get("tailingObj", [{}])[0]
    #                     distance = tailing_obj.get("tailingObj.distanceToCamera", None)
    #                     if distance is not None:
    #                         frame_ids.append(int(frame_id))
    #                         distances.append(distance)
    #                         self.data_queue.put((frame_ids, distances))
    #                         time.sleep(0.5)  # Simulate some delay
    #                         # # Update plot
    #                         # self.update_plot()
    #             except json.JSONDecodeError as e:
    #                 print(f"Error parsing JSON: {e}")
    #             except KeyError as e:
    #                 print(f"Key error: {e}")



    def run_live_mode(self):
    
        logging.info("🔧 Configuring live mode settings...")
        
        def start_server_thread(draw, folder_name,visual_mode):
            logging.info(f"🚀 Starting server thread with folder name: {folder_name}")
            self.Connect.start_server(draw_jsonlog=draw, save_folder=folder_name, visual_mode=visual_mode)

        def start_plot_dynamic(json_log_path):
            self.plotter_dynamic.run(json_log_path)

        self.varify_device_input_mode = 0  # live mode
        self.varify_enable_save_raw_images = 1  # enable save raw images
        self.visualize_mode = 1 # semi-online

        logging.info("📝 Modifying configuration file for live mode...")
        self.modify_config_file()

        logging.info("🧵 Starting the server in a separate thread...")
        server_th = threading.Thread(target=start_server_thread, args=(False, str(self.date_time),"semi-online",))
        server_th.start()

        logging.info("🚗 Running the ADAS system in live mode...")
        self.run_the_adas()       
       
        json_log_path = f"{self.curret_dir}/runs/{self.date_time}/{self.date_time}.txt"
        # Start dynamic plotting in a separate thread to prevent blocking
        # plot_dynamic_th = threading.Thread(target=start_plot_dynamic, args=(json_log_path,))
        # plot_dynamic_th.start()
        t = self.varify_run_historical_time
        # self.plotter_dynamic.run(json_log_path,t)
        # logging.info("🧵 Starting plotting dynamic in a separate thread...")
        # plot_dynamic_th = threading.Thread(target=start_plot_dynamic, args=(json_log_path,))
        # plot_dynamic_th.start()

        logging.info(f"⏳ Running live mode for {t} seconds with progress...")

        for _ in tqdm(range(t), desc=f"⏳ Running live Mode and saving raw images", unit="s"):
            time.sleep(1)

        
        logging.info(f"🏁 Completed {t} seconds. Stopping the ADAS system...")
        self.stop_run_adas()
        logging.info("🏁 ADAS system stopped successfully!")

        logging.info("🛑 Stopping the server and finishing the thread...")
        self.Connect.stop_server.set()

        # Reset the stop event for the next iteration
        logging.info("🔄 Resetting the server stop event for the next run...")
        self.Connect.stop_server.clear()

        logging.info(f"📂 Moving files to {self.curret_dir}/assets/{str(self.date_time)}/{str(self.date_time)}.txt")
        self.move_file(f"{self.curret_dir}/runs/{str(self.date_time)}")

        # self.live_mode_txt_file = f"{self.save_jsonlog_dir}/{str(self.date_time)}/{str(self.date_time)}.txt"
        self.live_mode_txt_file = f"{self.curret_dir}/runs/{str(self.date_time)}/{str(self.date_time)}.txt"
        logging.info(f"💾 Live mode JSON log file saved at: {self.live_mode_txt_file}")


    def run_historical_mode(self):

        logging.info("🔧 Configuring historical mode settings...")

        def start_server_thread():
            logging.info("🚀 Starting server for historical mode...")
            # self.Connect.start_server_ver3()
            self.Connect.start_server(visual_mode="online")

        self.varify_device_input_mode = 2  # historical mode
        self.varify_enable_save_raw_images = 0  # disable save raw images
        self.visualize_mode = 0  # visualize the historical mode

        logging.info("📝 Modifying configuration file for historical mode...")
        self.modify_config_file()

        logging.info("🧵 Starting the server in a separate thread...")
        server_th = threading.Thread(target=start_server_thread)
        server_th.start()

        logging.info("🚗 Running the ADAS system in historical mode...")
        self.run_the_adas()

        t = int(self.varify_run_historical_time * 1.4)
        logging.info(f"⏳ Running historical mode for {t} seconds with progress...")

        for _ in tqdm(range(t), desc="⏳ Running historical Mode...", unit="s"):
            time.sleep(1)

        logging.info(f"🏁 Completed {t} seconds in historical mode. Stopping the ADAS system...")

        self.stop_run_adas()
        logging.info("🏁 ADAS system stopped successfully!")

        logging.info(f"📂 Moving files to {self.save_jsonlog_dir}/{self.varify_raw_image_folder}")
        self.move_file(f"{self.curret_dir}/runs/debug_csv/raw_images/{self.varify_raw_image_folder}")

        # self.historical_mode_txt_file = f"{self.save_jsonlog_dir}/{self.varify_raw_image_folder}/{self.varify_raw_image_folder}.txt"
        self.historical_mode_txt_file = f"{self.curret_dir}/runs/debug_csv/raw_images/{self.varify_raw_image_folder}/{self.varify_raw_image_folder}.txt"
        
        logging.info(f"💾 Historical mode JSON log file saved at: {self.historical_mode_txt_file}")

    
    
    def get_current_date_time(self):
        # Device csv file name is like this : 199_video-adas_1970-01-01.95.csv

        # Get the current date and time
        now = datetime.now()

        # Format the date and time
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        logging.info(f"Current Date: {current_date}")
        logging.info(f"Current Time: {current_time}")

        return current_date,current_time

    def stop_run_adas(self):
        commands = (
            f"killall -9 cardv"
        )
        self.Connect.SSH.execute_remote_command_with_progress_ver2(commands)
    


    def set_date_time(self):
        # Get the current date and time in the required format
        now = datetime.datetime.now()
        date_time_str = now.strftime("%Y.%m.%d-%H:%M:%S")
        
        # Construct the SSH command to set the date and time on the remote camera
        command = f"date -s '{date_time_str}'"
        
        
        # Execute the command on the remote system
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        
        # Read and log any errors
        stderr_output = stderr.read().decode().strip()
        if stderr_output:
            logging.error(f"Error setting date and time on remote camera: {stderr_output}")
        else:
            logging.info(f"Successfully set the date and time on the remote camera to {date_time_str}")
        
        return date_time_str
        # Close the SSH connection
        # ssh_client.close()

    def find_closest_folder(self):

        remote_raw_images_dir = self.camera_rawimages_dir
       
        # Get the current time in the format used for folder names
        now = datetime.datetime.now()
        current_time_str = now.strftime("%Y-%m-%d-%H-%M")

        # SSH command to list folders in the remote directory
        command = f"ls -d {remote_raw_images_dir}/*/"
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        
        folder_names = stdout.read().decode().strip().split("\n")

        # Parse folder names and find the closest one
        closest_folder = None
        min_diff = float('inf')

        for folder in folder_names:
            folder_name = folder.split("/")[-2]  # Extract the folder name from path
            try:
                folder_time = datetime.datetime.strptime(folder_name, "%Y-%m-%d-%H-%M")
                diff = abs((now - folder_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_folder = folder_name
            except ValueError:
                # Skip folders with invalid names
                continue

        if closest_folder is None:
            print("No valid folders found.")
            return None

        return closest_folder



    def remote_download_jsonlog_csv_file(self, mode=None):
        if mode == 'live':
            csv_file_ = self.varify_live_mode_csv_file
        else:
            csv_file = self.varify_historical_mode_csv_file
        
        # Go to csv file directory and download the csv file from device to local computer
        remote_commands = (
            f"cd {self.varify_camera_csv_file_dir} && "
            f"tftp -l {csv_file} -p {self.server_ip}"
        )
    
        self.Connect.SSH.execute_remote_command_with_progress_ver2(remote_commands)

        # Go to tftp sever folder directory and move the csv file to the ADAS evaluation tools directory
        local_command = (
            f"cd {self.tftpserver_dir} && "
            f"mv {csv_file} {self.varify_save_jsonlog_dir}"
        )

        self.Connect.execute_local_command(local_command)

        return NotImplemented
    

    def modify_config_file(self):
        # Ensure you have the correct path to the config file
        config_file_path = self.varify_camera_config_file_path
        commands = (
            f"sed -i 's/^InputMode = [0-9]*/InputMode = {self.varify_device_input_mode}/' {config_file_path} && "
            f"sed -i 's|^VideoPath = .*|VideoPath = \"{self.varify_video_path}\"|' {config_file_path} && "
            f"sed -i 's|^RawImageDir = .*|RawImageDir = {self.varify_raw_image_dir}|' {config_file_path} && "
            f"sed -i 's/^ImageModeStartFrame = [0-9]*/ImageModeStartFrame = {self.varify_image_mode_start_frame}/' {config_file_path} && "
            f"sed -i 's/^ImageModeEndFrame = [0-9]*/ImageModeEndFrame = {self.varify_image_mode_end_frame}/' {config_file_path} && "
            f"sed -i 's/^ServerPort = [0-9]*/ServerPort = {self.server_port}/' {config_file_path} && "
            f"sed -i 's/^ServerIP = .*/ServerIP = {self.server_ip}/' {config_file_path} && "
            f"sed -i 's/^VisualizeMode = [0-2]*/VisualizeMode = {self.visualize_mode}/' {config_file_path} && "
            f"sed -i 's/^DebugSaveRawImages = [0-1]*/DebugSaveRawImages = {self.varify_enable_save_raw_images}/' {config_file_path}"
        )
        # logging.info(f"remote modify config : {commands}")
        self.Connect.SSH.execute_remote_command_with_progress_ver2(commands)
    

    def run_the_adas(self):
        """
        Execute the ADAS script and manage process cleanup.
        """
        try:
            remote_command = (
                f"cd / && "
                # "ps -a | grep run_script | awk '{print $1}' | xargs -r kill -9 && "  # Use -r to avoid xargs error if no process is found
                "cd /customer && "
                "./run_adas.sh"
            )
            
            output = self.Connect.SSH.execute_remote_command_with_progress_ver3(remote_command)
            
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")

    
    def move_file(self,file):
        try:
            local_command = (
                f"mv {file} {self.save_jsonlog_dir}"
            )
            
            output = self.Connect.execute_local_command(local_command)
            
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")
