import os
from utils.connection import Connection
from utils.drawer import Drawer
from engine.BaseDataset import BaseDataset
import logging
import threading
from utils.connection_handler import ConnectionHandler
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

class Historical(BaseDataset):

    def __init__(self,args):
        super().__init__(args)

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
        self.tftpserver_dir = args.tftpserver_dir
        self.camera_rawimages_dir = args.camera_rawimages_dir

        self.stream_format = ['mp4', 'avi']  # Fixed '.avi' to 'avi' for consistency

        self.h_mode_video_skip_frame = args.h_mode_video_skip_frame
        self.h_mode_camera_dataset_path = args.h_mode_camera_dataset_path
        self.h_mode_camera_script_path = args.h_mode_camera_script_path
        self.h_mode_local_dataset_path = args.h_mode_local_dataset_path
        self.h_mode_local_dataset_path_final = None
   

        self.tar_dataset_and_put_to_TFTP_folder_local_commands = None
  
        self.transfer_dataset_to_LI80_camera_remote_commands=None
   
        self.input_path = None
        self.Connect = Connection(args)
        self.ConnectHandler = ConnectionHandler(args)

    def preprocess_input_dataset(self):
        if os.path.isfile(self.h_mode_local_dataset_path):
            format = self.h_mode_local_dataset_path.split(".")[-1].lower()  # Convert to lowercase for consistency

            if format in self.stream_format:
                self.video_extract_frame(self.h_mode_local_dataset_path, crop=True, resize_w=576, resize_h=320, skipFrame = self.h_mode_video_skip_frame)
                self.h_mode_local_dataset_path_final = self.img_saver.save_dir
            else:
                print("Unsupported format or processing for other formats can be added here.")

        elif os.path.isdir(self.h_mode_local_dataset_path):
            self.h_mode_local_dataset_path_final = self.h_mode_local_dataset_path

        self.tar_dataset_and_put_to_TFTP_folder_local_commands = (
            f"cd {self.h_mode_local_dataset_path_final} && "
            f"cd .. && "
            f"tar cvf {os.path.basename(self.h_mode_local_dataset_path_final)}.tar {os.path.basename(self.h_mode_local_dataset_path_final)} && "
            f"sudo chmod 777 {os.path.basename(self.h_mode_local_dataset_path_final)}.tar && "
            f"mv {os.path.basename(self.h_mode_local_dataset_path_final)}.tar {self.tftpserver_dir}"
        )

        self.transfer_dataset_to_LI80_camera_remote_commands = (
            f"cd {self.camera_rawimages_dir} && "
            # f"tftp -gr {os.path.basename(self.h_mode_local_dataset_path_final)}.tar {self.tftp_ip} && "
            f"chmod 777 {os.path.basename(self.h_mode_local_dataset_path_final)}.tar && "
            f"tar -xvf {os.path.basename(self.h_mode_local_dataset_path_final)}.tar && "
            f"chmod 777 -R {os.path.basename(self.h_mode_local_dataset_path_final)} && "
            f"rm {os.path.basename(self.h_mode_local_dataset_path_final)}.tar"
        )

    def run_historical_mode(self):
        """
        Run historical mode by starting a server, modifying configurations, 
        and handling port usage for historical mode datasets.
        """

        def start_server_thread():
            self.Connect.start_server(visual_mode="online")

        if self.h_mode_local_dataset_path_final is not None:
            input_im_folder = os.path.basename(self.h_mode_local_dataset_path_final)
        else:
            input_im_folder = os.path.basename(self.h_mode_camera_dataset_path)

        self.raw_image_dir = os.path.join(self.camera_rawimages_dir, input_im_folder)

        # 🚀 Check if the server port is in use and get process details if so
        is_in_use, pid, process_name = self.ConnectHandler.check_process_using_port(self.server_port)

        while is_in_use:
            logging.info(f"⚠️ Port {self.server_port} is in use by process {process_name} with PID {pid}.")
            # If in use, kill the process remotely via SSH
            kill_result = self.ConnectHandler.kill_process_remotely(pid)
            logging.info(f"🛑 Kill result: {kill_result}")
            
            # Increment port number to check the next one
            self.Connect.server_port += 1
            self.server_port += 1

            # Check the new port status
            is_in_use, pid, process_name = self.ConnectHandler.check_process_using_port(self.server_port)

        logging.info(f"✅ Port {self.server_port} is available.")

        # 🔧 Modify configuration file for historical mode
        self.modify_config_file()
        logging.info("✅ Configuration file modification finished!")

        # 🚀 Start the server in a separate thread
        logging.info("🌐 Starting server in a separate thread...")
        server_th = threading.Thread(target=start_server_thread)
        server_th.start()

        # 🎯 Run the ADAS application
        logging.info("🎬 Running ADAS application...")
        self.run_the_adas()



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
                # "cd /customer && "
                f".{self.h_mode_camera_script_path}"
            )
            
            output = self.Connect.SSH.execute_remote_command_with_progress_ver3(remote_command)
            
            logging.info(f"🚀 Command output: {output}")

        except Exception as e:
            logging.error(f"❌An error occurred while running the ADAS: {e}")

        finally:
            logging.info("ADAS execution command complete.")
       
    
    