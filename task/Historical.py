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
# # Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Historical(BaseDataset):
    def __init__(self,args):
        super().__init__(args)
        self.tftpserver_dir = None
        self.camera_rawimages_dir = args.camerarawimages_dir
        self.camera_csvfile_dir = args.cameracsvfile_dir
        self.current_dir = os.getcwd() # .../Historical
        # self.logging = logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        # con_args = get_connection_args()
        self.Connect = Connection(args)
        self.tftpserver_dir = args.tftpserver_dir
        self.im_folder = os.path.basename(self.im_dir)

        self.get_raw_images_remote_commands = ( f"cd {self.camera_rawimages_dir} && "
                                                f"tar cvf {self.im_folder}.tar {self.im_folder}/ && "
                                                f"tftp -l {self.im_folder}.tar -p {self.tftp_ip} && "
                                                f"rm {self.im_folder}.tar")
        
        self.get_raw_images_local_commands = (  f"cd {self.tftpserver_dir} && "
                                                f"sudo chmod 777 {self.im_folder}.tar && "
                                                f"tar -xvf {self.im_folder}.tar && "
                                                f"sudo chmod 777 -R {self.im_folder} && "
                                                f"mv {self.im_folder} {self.current_dir}/assets/images")
       
        self.get_csv_file_remote_commands = ( f"cd {self.camera_csvfile_dir} && "
                                              f"tftp -l {self.csv_file} -p {self.tftp_ip}")
        
        self.get_csv_file_local_commands = ( f"cd {self.tftpserver_dir} && "
                                             f"mv {self.csv_file} {self.current_dir}/assets/csv_file")
        
        self.display_parameters()

        self.Plotter = Plotter(args)

        self.Drawer = Drawer(args)
        
    '''
    -----------------------------------------------------------------------------
    Main function of visualize AI result
    inlcuding :
        1. LI80 camera live mode :
            1-1. visualize online
        2. LI80 camera historical mode :
            2-1. visualize online
            2-2. visualize semi-online
            2-3. visualize offline 

        And some utilities : decode video / encode frame to video, etc.
    -----------------------------------------------------------------------------------------
    '''
 
    def visualize(self, mode=None, 
                  jsonlog_from=None, 
                  plot_distance=False, 
                  gen_raw_video=False,
                  save_raw_image_dir=None, 
                  extract_video_to_frames=None, 
                  crop=False, 
                  raw_images_dir=None):
        # Handle modes and their associated actions
        if mode == "offline":
            if jsonlog_from == "camera":
                logging.info("Start run offline mode, json log from camera...")
                self.visualize_offline_jsonlog_from_camera()
            elif jsonlog_from == "online":
                logging.info("Start run offline mode, json log from online...")
                self.visualize_offline_jsonlog_from_online()
        
        elif mode == "semi-online":
            logging.info("Start run semi-online mode, waiting for client (Camera start run historical mode)")
            self.visualize_semi_online()

        elif mode == "online":
            logging.info("Start run online mode of visualize historical mode, waiting for client (Camera start run historical mode)")
            if save_raw_image_dir:
                self.im_dir = save_raw_image_dir
            self.visualize_online()
        
        # Handle video extraction and conversion
        if extract_video_to_frames:
            self.video_extract_frame(extract_video_to_frames, crop)

        if gen_raw_video:
            self.convert_rawimages_to_videoclip(im_dir=raw_images_dir)

        # Plot distance if requested
        if plot_distance:
            self.Plotter.plot_distance_value_on_each_frame_ID()


    '''
    ---------------------------------
    Online
    Detail:
        Visualize AI result online
        1. Transfer json log of each frame & raw images with jpg format to local computer, 
            and visualize on local computer
    ---------------------------------
    '''
    def visualize_online(self):
        self.Connect.start_server_ver2()

    '''
    -----------------------------------------------
    Semi-online
    Detail:
        Visualize AI result semi-online
        1. Transfer  the raw images from camera to local computer
        2. Run online mode, transfer json log to local computer online, 
            and visualize AI result on the raw image that already saved
    ------------------------------------------------
    '''
    def visualize_semi_online(self):
        HAVE_LOCAL_IMAGES = os.path.exists(self.im_dir)
        logging.info(f"HAVE_LOCAL_IMAGES: {HAVE_LOCAL_IMAGES}")
        # If local have no raw images or CSV file, download from camera device using SSH
        if not HAVE_LOCAL_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{self.im_folder}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"tar file: {self.im_folder}.tar does not exist in tftp folder")
                logging.info("Start to download raw images from the LI80 camera...")
                self.Connect.execute_remote_command_with_progress(self.get_raw_images_remote_commands)  # Execute commands on the camera
            
            logging.info(f"tar file: {self.im_folder}.tar exists in tftp folder, moving to the assets/images/")
            self.Connect.execute_local_command(self.get_raw_images_local_commands) # Execut command on the local computer
        
        self.Connect.start_server()


    '''
    ---------------------------------------------------
    Offline json from camera
    Detail:
        Visualize AI result offline
        JSON format is from camera saved JSON log csv file
    ------------------------------------------------------------
    '''
    def visualize_offline_jsonlog_from_camera(self):
        HAVE_LOCAL_IMAGES = os.path.exists(self.im_dir)
        logging.info(f"HAVE_LOCAL_IMAGES: {HAVE_LOCAL_IMAGES}")
        # If local have no raw images or CSV file, download from camera device using SSH
        if not HAVE_LOCAL_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{self.im_folder}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"tar file: {self.im_folder}.tar does not exist in tftp folder")
                logging.info("Start to download raw images from the LI80 camera...")
                self.Connect.execute_remote_command_with_progress(self.get_raw_images_remote_commands)  # Execute commands on the camera
            
            logging.info(f"tar file: {self.im_folder}.tar exists in tftp folder, moving to the assets/images/")
            self.Connect.execute_local_command(self.get_raw_images_local_commands) # Execut command on the local computer

        if not os.path.exists(self.csv_file_path):
            logging.info(self.csv_file)
            self.Connect.execute_remote_command_with_progress(self.get_csv_file_remote_commands) # Execute commands on the camera
            self.Connect.execute_local_command(self.get_csv_file_local_commands) # Execut command on the local computer

        # Start to darw AI result after local have raw images and CSV file
        self.Drawer.draw_AI_result_to_images()


    '''
    -------------------------------------------------------
    Offline json from online
    Detail:
        Visualize AI result offline
        JSON format is from run online visualize saved json log
    --------------------------------------------------------
    '''
    def visualize_offline_jsonlog_from_online(self):
    
        # Read the CSV file
        logging.info(self.csv_file)
        df = pd.read_csv(self.csv_file_path)

        # Iterate over each row in the CSV file
        for index, row in df.iterrows():
            try:
                json_data = json.loads(row[0])  # Assuming the JSON is in the first column
                for frame_id, frame_data in json_data["frame_ID"].items():
                    tailing_objs = frame_data.get("tailingObj", [])
                    detect_objs = frame_data.get("detectObj", {}).get("VEHICLE", []) + frame_data.get("detectObj", {}).get("HUMAN", [])
                    vanish_objs = frame_data.get("vanishLineY", [])
                    ADAS_objs = frame_data.get("ADAS",[])
                    lane_info = frame_data.get("LaneInfo",[])
                    # if tailing_objs:
                    self.Drawer.draw_bounding_boxes(frame_id, tailing_objs,detect_objs,vanish_objs,ADAS_objs,lane_info)
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON on row {index}: {e}")
            except KeyError as e:
                logging.error(f"Key error on row {index}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error on row {index}: {e}")


   
            

    


    