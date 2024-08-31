import os
import cv2
import json
import csv
import glob
import logging
from engine.BaseDataset import BaseDataset
from utils.connection import Connection
import threading
from tqdm import tqdm
import time
# from task.Historical import Historical
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

class Evaluation(BaseDataset):
    def __init__(self,args):
        super().__init__(args)
        self.args = args
        self.eval_camera_raw_im_dir = args.eval_camera_rawimage_dir
        self.eval_static_case_run_time = args.eval_static_case_run_time
        self.eval_dynamic_case_run_time =args.eval_dynamic_case_run_time
        # self.eval_save_ai_result_dir = args.eval_save_ai_result_dir
        self.tftpserver_dir = args.tftpserver_dir
        self.evaluationdata_dir = args.evaluationdata_dir

        self.local_commands = None
        self.remote_commands = None
        self.script_path = args.script_path
        self.script_dir = os.path.dirname(self.script_path)
        self.script_file = os.path.basename(self.script_path)
        self.camera_config_dir = args.camera_config_dir
        self.config_file_path = os.path.join(self.camera_config_dir,'config.txt')
        self.input_mode = 2
        self.video_path = "/new/path/to/video/file"
        self.raw_image_dir = None
        self.start_frame = 0
        self.end_frame = 99999
        self.server_port = args.server_port
        self.server_ip = args.tftp_ip
        self.visualize_mode = 0
        # self.csv_file_path = args.remote_csv_file_path
        # self.remote_csv_file_path = args.remote_csv_file_path
        
        # self.im_folder = None
        # self.Historical = Historical(args)

        self.Connect = Connection(args)
        self.display_parameters()
        
        # self.initialize_image_saver(args)

    def display_parameters(self):
        logging.info("--------------- 🛠️  Evaluation Settings 🛠️ ---------------")
        logging.info(f"📂 CAMERA RAW IMAGES DIR     : {self.eval_camera_raw_im_dir}")
        logging.info(f"📂 EVALUATION DATA DIR       : {self.evaluationdata_dir}")
        logging.info(f"📜 SCRIPT PATH               : {self.script_path}")
        logging.info(f"📁 SCRIPT DIRECTORY          : {self.script_dir}")
        logging.info(f"📄 SCRIPT FILE               : {self.script_file}")
        logging.info(f"⚙️  CONFIG DIR               : {self.camera_config_dir}")
        logging.info(f"⚙️  CONFIG FILE PATH         : {self.config_file_path}")
        logging.info(f"🔧 INPUT MODE               : {self.input_mode}")
        logging.info(f"🎞️  VIDEO PATH              : {self.video_path}")
        logging.info(f"🖼️  RAW IMAGE DIR           : {self.raw_image_dir}")
        logging.info(f"⏯️  START FRAME             : {self.start_frame}")
        logging.info(f"⏸️  END FRAME               : {self.end_frame}")
        logging.info(f"🌐 SERVER PORT              : {self.server_port}")
        logging.info(f"🌍 SERVER IP                : {self.server_ip}")
        logging.info(f"🖥️  VISUALIZE MODE          : {self.visualize_mode}")
        
        # Handle potential None values for attributes
        logging.info(f"📁 IM FOLDER                : {self.im_folder if self.im_folder else 'Not set'}")
        logging.info(f"💻 LOCAL COMMANDS           : {self.local_commands if self.local_commands else 'Not set'}")
        logging.info(f"🌐 REMOTE COMMANDS          : {self.remote_commands if self.remote_commands else 'Not set'}")
        logging.info("------------------------------------------------------------")



    def get_device_date(self):
        """
        Get the current date from the remote device.
        """
        date_command = "date"
        try:
            date_output = self.Connect.SSH.execute_remote_command_with_progress_ver2(date_command)
            logging.info(f"Device date: {date_output}")
            return date_output
        except Exception as e:
            logging.error(f"Error retrieving device date: {e}")
            return None


    def check_directory_exists(self, directory_path):
        # Construct the command to check for directory existence
        check_command = f'[ -d "{directory_path}" ] && echo "Directory exists" || echo "Directory does not exist"'

        try:
            # Execute the remote command
            result = self.Connect.SSH.execute_remote_command_with_progress_ver2(check_command)

            # Check if result is not None
            if result is not None:
                # Clean up the result
                result = result.strip()
                # Log the result
                logging.info(f"Remote command result: {result}")

                # Check if the directory exists based on the command output
                if "Directory exists" in result:
                    logging.info("Directory exists on the remote device.")
                    return True
                else:
                    logging.info("Directory does not exist on the remote device.")
                    return False
            else:
                logging.error("No result returned from remote command.")
                return False

        except Exception as e:
            logging.error(f"Error executing remote command: {e}")
            return False



    def modify_config_file(self):
        # Ensure you have the correct path to the config file
        config_file_path = self.config_file_path

        commands = (
            f"sed -i 's/^InputMode = [0-9]*/InputMode = {self.input_mode}/' {config_file_path} && "
            f"sed -i 's|^VideoPath = .*|VideoPath = \"{self.video_path}\"|' {config_file_path} && "
            f"sed -i 's|^RawImageDir = .*|RawImageDir = {self.raw_image_dir}|' {config_file_path} && "
            f"sed -i 's/^ImageModeStartFrame = [0-9]*/ImageModeStartFrame = {self.start_frame}/' {config_file_path} && "
            f"sed -i 's/^ImageModeEndFrame = [0-9]*/ImageModeEndFrame = {self.end_frame}/' {config_file_path} && "
            f"sed -i 's/^ServerPort = [0-9]*/ServerPort = {self.server_port}/' {config_file_path} && "
            f"sed -i 's/^ServerIP = .*/ServerIP = {self.server_ip}/' {config_file_path} && "
            f"sed -i 's/^VisualizeMode = [0-2]*/VisualizeMode = {self.visualize_mode}/' {config_file_path}"
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
                "./run_script"
            )
            
            output = self.Connect.SSH.execute_remote_command_with_progress_ver2(remote_command)
            
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")
      

    def visualize_online(self):
        # from task.Historical import Historical
        '''
        Optionally, provide a specialized implementation for Evaluation or call the method from Historical if needed.
        '''
        self.Connect.start_server_ver3()
       
    

    def is_processing_complete(self):
        """
        Check if the processing is complete by verifying if the last line of the CSV file
        contains the error message "libpng error: Read Error".
        
        Returns:
            bool: True if the error message is found, otherwise False.
        """
        try:
            # Check if the CSV file exists
            if not os.path.exists(self.csv_file_path):
                logging.error(f"❌CSV file does not exist: {self.csv_file_path}")
                return False

            with open(self.csv_file_path, 'r') as file:
                # Read all lines and get the last line
                lines = file.readlines()
                if not lines:
                    logging.error("CSV file is empty.")
                    return False
                
                last_line = lines[-1].strip()
                
                # Check for the specific error message
                error_message = "libpng error: Read Error"
                if error_message in last_line:
                    logging.info("Processing complete: Error message found.")
                    return True
                else:
                    logging.info("Processing not complete: Error message not found.")
                    return False

        except Exception as e:
            logging.error(f"❌An error occurred while checking processing status: {e}")
            return False
        
    def run_golden_dataset(self):
        """
            Executes the golden dataset evaluation by processing directories, running historical modes, and managing server operations.

            This method performs the following steps:
            1. **Directory Processing**:
            - Retrieves and sorts a list of image directories from the evaluation data directory.
            - Iterates through each directory to prepare for processing.
            
            2. **Server Initialization**:
            - Starts a TCP server for each directory using a separate thread.
            
            3. **Historical Mode Execution**:
            - Runs the historical mode for a specified duration based on the type of data (Static or Dynamic).
            - Uses a progress bar to indicate the running time of the historical mode.
            
            4. **Logging and Status Updates**:
            - Logs the start, progress, and completion of each run.
            - Handles exceptions and provides warnings for unknown data types and non-existent directories.
        """
        def start_server_thread(custom_directory=None):
            self.Connect.start_server_ver3(custom_directory)

        # Get a sorted list of image directories
        im_dir_list = sorted(glob.glob(os.path.join(self.evaluationdata_dir, '***/**/*')))

        if len(im_dir_list) == 0:
            logging.error("❌ The im_dir_list is empty!")
            logging.info("🔍 Please check if the dataset is placed in the directory: {self.evaluationdata_dir}.")
            return


        for im_dir in im_dir_list:
            print(f"🔍 Processing directory: {im_dir}")

        for im_dir in im_dir_list:
            logging.info(f"---------------------------------------------------------------------------------------------")
            logging.info(f"ℹ️  Starting run for: {im_dir}")
            self.im_folder = os.path.basename(os.path.normpath(im_dir))
            data_type = self.im_folder.split("_")[0]

            # Set running time based on the data type
            if data_type == 'Static':
                t = self.eval_static_case_run_time
            elif data_type == 'Dynamic':
                t = self.eval_dynamic_case_run_time
            else:
                logging.warning(f"⚠️ Unknown data type: {data_type}. Skipping directory.")
                continue

            # Get the GT_dist and mytype from directory structure
            parent_dir = os.path.dirname(im_dir)
            GT_dist = os.path.basename(parent_dir)
            mytype = os.path.basename(os.path.dirname(parent_dir))

            dir_path = os.path.join(self.eval_camera_raw_im_dir, mytype, GT_dist, self.im_folder)
            if self.check_directory_exists(dir_path):
                logging.info(f"✅ Directory found: {os.path.basename(dir_path)}")

                # Start the server in a separate thread
                server_th = threading.Thread(target=start_server_thread)
                server_th.start()

                # Run historical mode
                self.run_historical_mode(input_im_folder=dir_path)

                # Run historical mode for the specified time with a progress bar
                for _ in tqdm(range(t), desc=f"⏳ Running Historical Mode ... {os.path.basename(im_dir)}", unit="s"):
                    time.sleep(1)

                logging.info(f"🏁 Completed {t} seconds for {os.path.basename(im_dir)}. Preparing for next case.")

                # Stop the server and wait for the thread to finish
                self.Connect.stop_server.set()
                # server_th.join()
                logging.info("🛑 Server stopped and thread finished.")

                # Reset the stop event for the next iteration
                self.Connect.stop_server.clear()

            else:
                logging.warning(f"❌ Skipped: {dir_path} does not exist.")




    def sleep(self,time=1):
        time.sleep(time)
        return
    

    def run_historical_mode(self, input_im_folder="Dynamic_20240805_NONE_50km_30km_0"):

        self.raw_image_dir = os.path.join(self.eval_camera_raw_im_dir, input_im_folder)
        self.modify_config_file()
        logging.info(" ✅ modify_config_file finished!")
        self.run_the_adas()
        

    # Start visualization in a separate thread
    def visualization_thread_target(self):
        try:
            logging.info("Starting visualization.")
            self.visualize_online()
            logging.info("Visualization completed.")
        except Exception as e:
            logging.error(f"Error in visualization: {e}")


            

            