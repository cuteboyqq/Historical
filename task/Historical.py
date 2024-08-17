import csv
import json
import matplotlib.pyplot as plt
import os
import cv2
from engine.BaseDataset import BaseDataset
from utils.connection import Connection
import numpy as np
# from config.config import get_connection_args
import logging
import pandas as pd
from utils.plotter import Plotter
from utils.drawer import Drawer
from utils.evaluation import Evaluation
# # Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Historical(BaseDataset):
    def __init__(self, args):
        """
        Initializes the Historical dataset object.

        Args:
            args (argparse.Namespace): Arguments containing configuration parameters such as directories and connection settings.
        """
        super().__init__(args)
        self.tftpserver_dir = None
        self.camera_rawimages_dir = args.camerarawimages_dir
        self.camera_csvfile_dir = args.cameracsvfile_dir
        self.current_dir = os.getcwd()  # Current working directory (e.g., .../Historical)
        self.Connect = Connection(args)
        self.tftpserver_dir = args.tftpserver_dir
        self.im_folder = os.path.basename(self.im_dir)
        self.script_path = args.script_path
        self.script_dir = os.path.dirname(self.script_path)
        self.script_file = os.path.basename(self.script_path)

        # Commands for remote and local operations
        self.get_raw_images_remote_commands = (
            f"cd {self.camera_rawimages_dir} && "
            f"tar cvf {self.im_folder}.tar {self.im_folder}/ && "
            f"tftp -l {self.im_folder}.tar -p {self.tftp_ip} && "
            f"rm {self.im_folder}.tar"
        )
        
        self.get_raw_images_local_commands = (
            f"cd {self.tftpserver_dir} && "
            f"sudo chmod 777 {self.im_folder}.tar && "
            f"tar -xvf {self.im_folder}.tar && "
            f"sudo chmod 777 -R {self.im_folder} && "
            f"mv {self.im_folder} {self.current_dir}/assets/images"
        )
       
        self.get_csv_file_remote_commands = (
            f"cd {self.camera_csvfile_dir} && "
            f"tftp -l {self.csv_file} -p {self.tftp_ip}"
        )
        
        self.get_csv_file_local_commands = (
            f"cd {self.tftpserver_dir} && "
            f"mv {self.csv_file} {self.current_dir}/assets/csv_file"
        )
    
        self.display_parameters()

        self.Plotter = Plotter(args)
        self.Drawer = Drawer(args)
        self.Evaluation = Evaluation(args)
        # self.initialize_image_saver(args)
    
    def visualize(self, mode=None, 
                  jsonlog_from=None, 
                  plot_distance=False, 
                  gen_raw_video=False,
                  save_raw_image_dir=None, 
                  extract_video_to_frames=None, 
                  crop=False, 
                  raw_images_dir=None):
        """
        Main function for visualizing AI results based on the specified mode and options.

        Args:
            mode (str, optional): Operational mode. Options are "online", "semi-online", "offline", None.
            jsonlog_from (str, optional): Source of JSON logs. Options are "camera" or "online", None.
            plot_distance (bool, optional): If True, plots distance values on each frame ID.
            gen_raw_video (bool, optional): If True, generates a video from raw images.
            save_raw_image_dir (str, optional): Directory to save raw images.
            extract_video_to_frames (str, optional): Path to the video for extracting frames.
            crop (bool, optional): If True, crops the extracted frames.
            raw_images_dir (str, optional): Directory containing raw images for video generation.
        """
        if mode == "offline":
            if jsonlog_from == "camera":
                logging.info("Running offline mode with JSON log from camera...")
                self.visualize_offline_jsonlog_from_camera()
            elif jsonlog_from == "online":
                logging.info("Running offline mode with JSON log from online...")
                self.visualize_offline_jsonlog_from_online()
        
        elif mode == "semi-online":
            logging.info("Running semi-online mode, waiting for client (Camera running historical mode)...")
            self.visualize_semi_online()

        elif mode == "online":
            logging.info("Running online mode of historical visualization, waiting for client (Camera running historical mode)...")
            if save_raw_image_dir:
                self.im_dir = save_raw_image_dir
            self.visualize_online()
        
        elif mode=="eval" or mode=="evaluation":
            logging.info("Running evaluation mode")
            self.Evaluation.run_golden_dataset()
        
        if extract_video_to_frames:
            self.video_extract_frame(extract_video_to_frames, crop)

        if gen_raw_video:
            self.convert_rawimages_to_videoclip(im_dir=raw_images_dir)

        if plot_distance:
            self.Plotter.plot_distance_value_on_each_frame_ID()

    def visualize_online(self):
        """
        Visualizes AI results in real-time by transferring JSON logs and raw images from the camera to the local computer.
        """
        # self.remote_run_historical_mode_commands = (
        #         f"cd {self.script_dir} && "
        #         f"./{self.script_file}"
        #     )
        # self.Connect.execute_remote_command_async(self.remote_run_historical_mode_commands)
        # self.Connect.execute_remote_command_with_progress(self.run_ADAS_remote_commands)
        self.Connect.start_server_ver2()
        

    def visualize_semi_online(self):
        """
        Visualizes AI results in semi-online mode. Transfers raw images from the camera if not present locally,
        then runs online mode to process and visualize JSON logs on saved images.
        """
        HAVE_LOCAL_IMAGES = os.path.exists(self.im_dir)
        logging.info(f"HAVE_LOCAL_IMAGES: {HAVE_LOCAL_IMAGES}")

        if not HAVE_LOCAL_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{self.im_folder}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"Tar file {self.im_folder}.tar does not exist in TFTP folder.")
                logging.info("Downloading raw images from the LI80 camera...")
                self.Connect.execute_remote_command_with_progress(self.get_raw_images_remote_commands)
            
            logging.info(f"Tar file {self.im_folder}.tar exists in TFTP folder, moving to assets/images/")
            self.Connect.execute_local_command(self.get_raw_images_local_commands)
        
        self.Connect.start_server()

    def visualize_offline_jsonlog_from_camera(self):
        """
        Visualizes AI results offline using JSON logs saved from the camera.
        Downloads raw images and CSV file if not present locally.
        """
        HAVE_LOCAL_IMAGES = os.path.exists(self.im_dir)
        logging.info(f"HAVE_LOCAL_IMAGES: {HAVE_LOCAL_IMAGES}")

        if not HAVE_LOCAL_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{self.im_folder}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"Tar file {self.im_folder}.tar does not exist in TFTP folder.")
                logging.info("Downloading raw images from the LI80 camera...")
                self.Connect.execute_remote_command_with_progress(self.get_raw_images_remote_commands)
            
            logging.info(f"Tar file {self.im_folder}.tar exists in TFTP folder, moving to assets/images/")
            self.Connect.execute_local_command(self.get_raw_images_local_commands)

        if not os.path.exists(self.csv_file_path):
            logging.info(self.csv_file)
            self.Connect.execute_remote_command_with_progress(self.get_csv_file_remote_commands)
            self.Connect.execute_local_command(self.get_csv_file_local_commands)

        self.Drawer.draw_AI_result_to_images()

    def visualize_offline_jsonlog_from_online(self):
        """
        Visualizes AI results offline using JSON logs from previous online visualizations.
        Reads the CSV file and processes each frame's JSON data to draw bounding boxes and other annotations.
        """
        logging.info(self.csv_file)
        df = pd.read_csv(self.csv_file_path)

        for index, row in df.iterrows():
            try:
                json_data = json.loads(row[0])
                for frame_id, frame_data in json_data["frame_ID"].items():
                    tailing_objs = frame_data.get("tailingObj", [])
                    detect_objs = frame_data.get("detectObj", {}).get("VEHICLE", []) + frame_data.get("detectObj", {}).get("HUMAN", [])
                    vanish_objs = frame_data.get("vanishLineY", [])
                    ADAS_objs = frame_data.get("ADAS", [])
                    lane_info = frame_data.get("LaneInfo", [])
                    self.Drawer.draw_bounding_boxes(frame_id, tailing_objs, detect_objs, vanish_objs, ADAS_objs, lane_info)
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON on row {index}: {e}")
            except KeyError as e:
                logging.error(f"Key error on row {index}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error on row {index}: {e}")



   
            

    


    