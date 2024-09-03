import csv
import json
import matplotlib.pyplot as plt
import os
import cv2
from engine.BaseDataset import BaseDataset
from utils.connection_handler import ConnectionHandler
from utils.connection import Connection
from task.evaluation import Evaluation
from utils.analysis import Analysis
from task.varify import Varify
from task.historical import Historical
import numpy as np
# from config.config import get_connection_args
import logging
import pandas as pd
from utils.plotter import Plotter
from utils.drawer import Drawer
from engine.visualize_runner import VisualizeRunner
from engine.test_runner import TestRunner
from utils.display import DisplayUtils
from utils.remote_uploader import RemoteUploader
# # Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TaskAssigner(BaseDataset):
    def __init__(self, args):
        """
        Initializes the Historical dataset object.

        Args:
            args (argparse.Namespace): Arguments containing configuration parameters such as directories and connection settings.
        """
        super().__init__(args)
        self.tftpserver_dir = None
        self.camera_rawimages_dir = args.camera_rawimages_dir
        self.camera_csvfile_dir = args.camera_csvfile_dir
        self.current_dir = os.getcwd()  # Current working directory (e.g., .../Historical)
        self.Connect = Connection(args)
        self.tftpserver_dir = args.tftpserver_dir
        self.im_folder = os.path.basename(self.im_dir)

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
        
        # self.display_parameters()
        self.Plotter = Plotter(args)
        self.Drawer = Drawer(args)
        self.Evaluation = Evaluation(args)
        self.Varify = Varify(args)
        self.Historical = Historical(args)
        self.RemoteUploader = RemoteUploader(args)
    
        # Analysis
        self.analysis_run = args.analysis_run
        if self.analysis_run:
            self.Analysis = Analysis(args)

        # Evaluation settings
        self.eval_camera_raw_im_dir = args.eval_camera_rawimage_dir

        self.tar_golden_dataset_and_put_to_TFTP_folder_local_commands = (
            f"cd {self.Evaluation.evaluationdata_dir} && "
            f"cd .. && "
            f"tar cvf {os.path.basename(self.Evaluation.evaluationdata_dir)}.tar {os.path.basename(self.Evaluation.evaluationdata_dir)} && "
            f"sudo chmod 777 {os.path.basename(self.Evaluation.evaluationdata_dir)}.tar && "
            f"mv {os.path.basename(self.Evaluation.evaluationdata_dir)}.tar {self.tftpserver_dir}"
        )

      
        self.transfer_golden_dataset_to_LI80_camera_remote_commands = (
            f"cd {self.camera_rawimages_dir} && "
            f"tftp -gr {os.path.basename(self.Evaluation.evaluationdata_dir)}.tar {self.tftp_ip} && "
            f"tar -xv --checkpoint=1 --checkpoint-action=dot -f {os.path.basename(self.Evaluation.evaluationdata_dir)}.tar && "
            f"chmod 777 -R {os.path.basename(self.Evaluation.evaluationdata_dir)} && "
            f"rm {os.path.basename(self.Evaluation.evaluationdata_dir)}.tar"
        )

        # Alister add Andy's code
        self.connection_handler = ConnectionHandler(args)
        self.VisualizeRunner = VisualizeRunner(self.connection_handler, args)
        # self.TestRunner = TestRunner(self.connection_handler,args)

        super().display_parameters()

    def task_assigner(self, mode=None, 
              jsonlog_from=None, 
              plot_distance=False, 
              gen_raw_video=False,
              save_raw_image_dir=None, 
              extract_video_to_frames=None, 
              crop=False, 
              raw_images_dir=None):
        if mode == "offline":
            if jsonlog_from == "camera":
                logging.info("🎥 Running offline mode with JSON log from camera...")
                self.visualize_offline_jsonlog_from_camera()
            elif jsonlog_from == "online":
                logging.info("🌐 Running offline mode with JSON log from online...")
                self.visualize_offline_jsonlog_from_online()

        elif mode == "online" or mode == "semi-online":
            logging.info("🔄 Running online or semi-online mode, waiting for client (Camera running historical mode)...")
            self.visualize_online_semi_online()
            # self.Connect.start_server(visual_mode=mode)
        elif mode == "visual":
            self.VisualizeRunner.run_visualize()
        
        # elif mode == "test":
        #     self.TestRunner.run_tests()
        #     self.connection_handler.close_connection()
        #     # Generate the test report
        #     report = self.TestRunner.gen_test_report()
        #     print(report)

        elif mode == "eval" or mode == "evaluation":
            logging.info("🧪 Running evaluation mode...")
            self.auto_evaluate_golden_dataset()
            # self.Evaluation.run_golden_dataset()
        
        elif mode == "varify":
            logging.info("✅ Running verify mode...")
            self.Varify.varify_historical_match_rate()

        elif mode == "historical":
            logging.info("✅ Running historical mode...")
            self.auto_run_historical_mode()
        
        if extract_video_to_frames:
            logging.info("🎞️ Extracting video frames...")
            self.video_extract_frame(extract_video_to_frames, crop)

        if gen_raw_video:
            logging.info("🎬 Generating raw video from images...")
            self.convert_rawimages_to_videoclip(im_dir=raw_images_dir)

        if plot_distance:
            logging.info("📏 Plotting distance values on frames...")
            self.Plotter.plot_all_static_golden_dataset()

        if self.analysis_run and mode == 'analysis':
            logging.info("📊 Running analysis mode...")
            self.Analysis.calc_all_static_performance()


    # Alister add 2024-08-28
    def auto_run_historical_mode(self):
        
        DEVICE_HAVE_IMAGES = self.Evaluation.check_directory_exists(self.Historical.h_mode_camera_dataset_path)
        dataset_folder_name = os.path.basename(self.Historical.h_mode_camera_dataset_path)
        logging.info(f"📷 DEVICE_HAVE_IMAGES: {DEVICE_HAVE_IMAGES}")

        if not DEVICE_HAVE_IMAGES:
            self.Historical.preprocess_input_dataset()
            tar_path = f'{self.tftpserver_dir}{os.sep}{dataset_folder_name}.tar'

            if not os.path.exists(tar_path):
                logging.info(f"❌ Tar file {dataset_folder_name}.tar does not exist in local TFTP folder.")
                logging.info("📦 Tar the Dataset and put it in the local TFTP folder...")
                logging.info(f"🚀 Start executing local command: {self.Historical.tar_dataset_and_put_to_TFTP_folder_local_commands}")
                self.Connect.SSH.execute_local_command(self.Historical.tar_dataset_and_put_to_TFTP_folder_local_commands)
            
            logging.info(f"✅ Tar file {dataset_folder_name}.tar exists in TFTP folder, moving to device {self.camera_rawimages_dir}")
            # Local and remote file paths
            local_tar_file = f"{self.tftpserver_dir}/{os.path.basename(self.Historical.h_mode_local_dataset_path_final)}.tar"
            remote_tar_file = f"{self.Historical.camera_rawimages_dir}/{os.path.basename(self.Historical.h_mode_local_dataset_path_final)}.tar"
            self.RemoteUploader.upload_file_with_progress(local_tar_file,remote_tar_file)
            logging.info(f"🌐 Start executing remote command: {self.Historical.transfer_dataset_to_LI80_camera_remote_commands}")
            self.Connect.SSH.execute_remote_command_with_progress(self.Historical.transfer_dataset_to_LI80_camera_remote_commands)

        self.Historical.run_historical_mode()



    def auto_evaluate_golden_dataset(self):
        DEVICE_HAVE_IMAGES = self.Evaluation.check_directory_exists(self.eval_camera_raw_im_dir)
        golden_dataset_folder_name = os.path.basename(self.eval_camera_raw_im_dir)
        logging.info(f"📷 DEVICE_HAVE_IMAGES: {DEVICE_HAVE_IMAGES}")

        if not DEVICE_HAVE_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{golden_dataset_folder_name}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"❌ Tar file {golden_dataset_folder_name}.tar does not exist in local TFTP folder.")
                logging.info("📦 Tar the Golden Dataset and put it in the local TFTP folder...")
                logging.info(f"🚀 Start executing local command: {self.tar_golden_dataset_and_put_to_TFTP_folder_local_commands}")
                self.Connect.execute_local_command(self.tar_golden_dataset_and_put_to_TFTP_folder_local_commands)
            
            logging.info(f"✅ Tar file {golden_dataset_folder_name}.tar exists in TFTP folder, moving to device {self.camera_rawimages_dir}")
            logging.info(f"🌐 Start executing remote command: {self.transfer_golden_dataset_to_LI80_camera_remote_commands}")
        
            self.Connect.SSH.execute_remote_command_with_progress(self.transfer_golden_dataset_to_LI80_camera_remote_commands)
           

        self.Evaluation.run_golden_dataset()



    def visualize_online_semi_online(self,mode="online"):
        """
        Visualizes AI results in real-time by transferring JSON logs and raw images from the camera to the local computer.
        """
        self.Connect.start_server(visual_mode=mode)


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
                self.Connect.SSH.execute_remote_command_with_progress(self.get_raw_images_remote_commands)
            
            logging.info(f"Tar file {self.im_folder}.tar exists in TFTP folder, moving to assets/images/")
            self.Connect.SSH.execute_local_command(self.get_raw_images_local_commands)
        
        self.Connect.start_server()


    def visualize_offline_jsonlog_from_camera(self):
        """
        📷 Visualizes AI results offline using JSON logs saved from the camera.
        Downloads raw images and CSV file if not present locally.
        """
        HAVE_LOCAL_IMAGES = os.path.exists(self.im_dir) and bool(os.listdir(self.im_dir))
        logging.info(f"HAVE_LOCAL_IMAGES: {HAVE_LOCAL_IMAGES} 🖼️")

        if not HAVE_LOCAL_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{self.im_folder}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"🚫 Tar file {self.im_folder}.tar does not exist in TFTP folder.")
                logging.info("🌐 Downloading raw images from the LI80 camera... ⏳")
                logging.info(f"Start execute_remote_command_with_progress : {self.get_raw_images_remote_commands}")
                self.Connect.SSH.execute_remote_command_with_progress(self.get_raw_images_remote_commands)
            else:
                logging.info(f"✅ Tar file {self.im_folder}.tar exists in TFTP folder, moving to assets/images/ 📂")
                logging.info(f"Start execute_local_command : {self.execute_local_command}")
                self.Connect.SSH.execute_local_command(self.get_raw_images_local_commands)

        if not os.path.exists(self.csv_file_path):
            logging.info(f"📄 CSV file not found: {self.csv_file_path}")
            logging.info("🌐 Downloading CSV file from the LI80 camera... ⏳")
            logging.info(f"Start execute_remote_command_with_progress : {self.get_csv_file_remote_commands}")
            self.Connect.SSH.execute_remote_command_with_progress(self.get_csv_file_remote_commands)
            logging.info(f"Start execute_local_command : {self.get_csv_file_local_commands}")
            self.Connect.SSH.execute_local_command(self.get_csv_file_local_commands)

        logging.info("🖼️ Drawing AI results on images...")
        self.Drawer.draw_AI_result_to_images()
        logging.info("🎉 Visualization complete!")



    def visualize_offline_jsonlog_from_online(self):
        """
        🎥 Visualizes AI results offline using JSON logs from previous online visualizations.
        📂 Reads the input file (CSV or TXT) and processes each frame's JSON data to draw bounding boxes and other annotations.
        """
        logging.info(f"📁 Processing file: {self.csv_file_path}")

        # Determine file format based on extension
        file_extension = self.csv_file_path.split('.')[-1]
        
        if file_extension.lower() == 'csv':
            df = pd.read_csv(self.csv_file_path)
            logging.info("✅ CSV file loaded successfully.")
        elif file_extension.lower() == 'txt':
            with open(self.csv_file_path, 'r') as file:
                lines = file.readlines()
            df = pd.DataFrame(lines, columns=["json_data"])
            logging.info("✅ TXT file loaded successfully.")
        else:
            logging.error(f"❌ Unsupported file format: {file_extension}")
            return

        for index, row in df.iterrows():
            try:
                json_data = json.loads(row[0])
                # logging.info(f"📝 Processing frame at row {index}")

                for frame_id, frame_data in json_data["frame_ID"].items():
                    tailing_objs = frame_data.get("tailingObj", [])
                    detect_objs = frame_data.get("detectObj", {}).get("VEHICLE", []) + frame_data.get("detectObj", {}).get("HUMAN", [])
                    vanish_objs = frame_data.get("vanishLine", [])
                    ADAS_objs = frame_data.get("ADAS", [])
                    lane_info = frame_data.get("LaneInfo", [])

                    # 🖼️ Draw bounding boxes and other annotations
                    self.Drawer.draw_bounding_boxes(frame_id, tailing_objs, detect_objs, vanish_objs, ADAS_objs, lane_info)

            except json.JSONDecodeError as e:
                logging.error(f"⚠️ Error decoding JSON on row {index}: {e}")
            except KeyError as e:
                logging.error(f"⚠️ Key error on row {index}: {e}")
            except Exception as e:
                logging.error(f"⚠️ Unexpected error on row {index}: {e}")



   
            

    


    