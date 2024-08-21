import os
from engine.BaseDataset import BaseDataset
import time
import logging
from utils.plotter import Plotter
from utils.connection import Connection
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

class Varify(BaseDataset):
    
    def __init__(self,args):
        super().__init__(args)
        self.varify_device_input_mode = None
        self.varify_video_path = ""
        self.varify_raw_image_dir = None
        self.varify_image_mode_start_frame = 1
        self.varify_image_mode_end_frame = 99999
        self.server_port = args.server_port
        self.server_ip = args.server_ip
        self.visualize_mode = 0
        self.varify_camera_config_file_path = args.varify_camera_config_file_path
        self.varify_enable_save_raw_images = None
        self.varify_camera_csv_file_dir = args.camera_csvfile_dir
        self.varify_run_historical_time = args.varify_run_historical_time
        self.varify_historical_mode_csv_file = None
        self.varify_live_mode_csv_file = None
        self.Plot = Plotter(args)
        self.Connect = Connection(args)
        self.tftpserver_dir = args.tftpserver_dir
        self.varify_save_jsonlog_dir = args.varify_save_jsonlog_dir
        os.makedirs(self.varify_save_jsonlog_dir,exist_ok=True)

    def varify_historical_match_rate(self):
        self.remote_run_LI80_camera_live_mode_save_raw_images()

        self.remote_run_LI80_camera_historical_mode()

        self.compare_distance_between_live_mode_ans_historical_mode()

        return NotImplemented
    

    def compare_distance_between_live_mode_ans_historical_mode(self):
        self.Plot.extract_distance_data(self.varify_historical_mode_csv_file,self.varify_live_mode_csv_file)


    def remote_run_LI80_camera_live_mode_save_raw_images(self):
        self.varify_device_input_mode = 0 # live mode
        self.varify_enable_save_raw_images = 1 # enable save raw images

        self.remote_modify_config_file()

        self.remote_run_the_adas()

        time.sleep(self.varify_run_historical_time)

        self.remote_stop_run_adas()

        self.remote_download_jsonlog_csv_file(mode='live')    
    

    def remote_run_LI80_camera_historical_mode(self):
        self.varify_device_input_mode = 2 # historical mode
        self.varify_enable_save_raw_images = 0 # disable save raw images

        self.remote_modify_config_file()

        self.remote_run_the_adas()

        time.sleep(self.varify_run_historical_time * 2)

        self.remote_download_jsonlog_csv_file(mode='historical')    

        return NotImplemented
    


    def remote_stop_run_adas(self):
        commands = (
            f"killall -9 cardv"
        )
        self.Connect.execute_remote_command_with_progress_ver2(commands)


    def remote_download_jsonlog_csv_file(self, mode=None):
        if mode == 'live':
            csv_file_ = self.varify_live_mode_csv_file
        else:
            csv_file = self.varify_historical_mode_csv_file
        remote_commands = (
            f"cd {self.varify_camera_csv_file_dir} && "
            f"tftp -l {csv_file} -p {self.server_ip}"
        )
    
        self.Connect.execute_remote_command_with_progress_ver2(remote_commands)

        local_command = (
            f"cd {self.tftpserver_dir} && "
            f"mv {csv_file} {self.varify_save_jsonlog_dir}"
        )

        self.Connect.execute_local_command(local_command)

        return NotImplemented
    

    def remote_modify_config_file(self):
        # Ensure you have the correct path to the config file
        config_file_path = self.varify_config_file_path
        commands = (
            f"sed -i 's/^InputMode = [0-9]*/InputMode = {self.varify_device_input_mode}/' {config_file_path} && "
            f"sed -i 's|^VideoPath = .*|VideoPath = \"{self.varify_video_path}\"|' {config_file_path} && "
            f"sed -i 's|^RawImageDir = .*|RawImageDir = {self.varify_raw_image_dir}|' {config_file_path} && "
            f"sed -i 's/^ImageModeStartFrame = [0-9]*/ImageModeStartFrame = {self.varify_image_mode_start_frame}/' {config_file_path} && "
            f"sed -i 's/^ImageModeEndFrame = [0-9]*/ImageModeEndFrame = {self.varify_image_mode_end_frame}/' {config_file_path} && "
            f"sed -i 's/^ServerPort = [0-9]*/ServerPort = {self.server_port}/' {config_file_path} && "
            f"sed -i 's/^ServerIP = .*/ServerIP = {self.server_ip}/' {config_file_path} && "
            f"sed -i 's/^VisualizeMode = [0-2]*/VisualizeMode = {self.visualize_mode}/' {config_file_path}"
            f"sed -i 's/^DebugSaveRawImages = [0-1]*/DebugSaveRawImages = {self.varify_enable_save_raw_images}/' {config_file_path}"
        )
        # logging.info(f"remote modify config : {commands}")
        self.Connect.execute_remote_command_with_progress_ver2(commands)
    

    def remote_run_the_adas(self):
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
            
            output = self.Connect.execute_remote_command_with_progress_ver2(remote_command)
            
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")

     
