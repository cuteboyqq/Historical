import yaml
import os

# Argument parsing for class initialization
class Args:
    def __init__(self, config):

        # Model configuation
        self.model_w = config['MODEL']['INPUT_WIDTH']
        self.model_h = config['MODEL']['INPUT_HEIGHT']

        # Mode
        self.mode = config['MODE']['VISUALIZE_HISTORICAL_MODE']

        # Visualize configuration
        self.visualize_mode = config['VISUALIZE']['MODE']
        self.device_mode = config['VISUALIZE']['DEVICE_MODE']

        # JSON log
        self.jsonlog_from = config['JSONLOG']['FROM']

        # Camera configuration
        self.camera_rawimages_dir = config['CAMERA']['CAMERA_RAW_IMAGE_DIR']
        self.camera_csvfile_dir = config['CAMERA']['CAMERA_CSV_FILE_DIR']
        self.camera_host_name = config['CAMERA']['CAMERA_HOSTNAME']
        self.camera_port = config['CAMERA']['CAMERA_PORT']
        self.camera_user_name = config['CAMERA']['CAMERA_USERNAME']
        self.camera_password = config['CAMERA']['CAMERA_PASSWORD']
        self.camera_config_dir = config['CAMERA']['CAMERA_CONFIG_DIR']

        # Server configuration
        self.tftpserver_dir = config['SERVER']['TFTP_DIR']
        self.server_port = config['SERVER']['PORT']
        self.tftp_ip = config['SERVER']['TFTP_IP']
        self.server_ip = config['SERVER']['IP']

        # Local configuration
        self.im_dir = config['LOCAL']['RAW_IMG_DIR']
        self.csv_file = config['LOCAL']['CSV_FILE']
        self.save_rawvideopath = config['LOCAL']['SAVE_RAW_VIDEO_PATH']

        # Remote configuration
        self.remote_adas_script_path = config['REMOTE']['ADAS_START_SCRIPT_PATH']
        self.remote_adas_stop_script_path = config['REMOTE']['ADAS_STOP_SCRIPT_PATH']
        self.remote_adas_config_path = config['REMOTE']['REMOTE_ADAS_CONFIG_PATH']
        self.backup_adas_config_path = config['REMOTE']['BACKUP_ADAS_CONFIG_PATH']
        self.adas_run_duration = config['REMOTE']['ADAS_RUN_DURATION']



        # Image configuration
        self.image_basename = config['IMAGE']['BASE_NAME']
        self.image_format = config['IMAGE']['FORMAT']

        # Display settings
        self.show_distanceplot = config['DISPLAY']['SHOW_DISTANCE_PLOT']
        self.show_airesultimage = config['DISPLAY']['SHOW_AI_RESULT_IMAGE']
        self.show_detectobjs = config['DISPLAY']['SHOW_DETECT_OBJS']
        self.show_tailingobjs = config['DISPLAY']['SHOW_TAILING_OBJS']
        self.show_vanishline = config['DISPLAY']['SHOW_VANISH_LINE']
        self.show_adasobjs = config['DISPLAY']['SHOW_ADAS_RESULT']
        self.showtailobjBB_corner = config['DISPLAY']['SHOW_TAILING_OBJS_BB_CORNER']
        self.show_laneline = config['DISPLAY']['SHOW_LANE_INFO']
        self.show_distancetitle = config['DISPLAY']['SHOW_DISTANCE_TITLE']
        self.show_detectobjinfo = config['DISPLAY']['SHOW_DETECT_OBJS_INFO']
        self.show_devicemode = config['DISPLAY']['SHOW_DEVICE_MODE']


        # Lane line
        self.alpha = config['LANE_LINE']['ALPHA']
        self.laneline_thickness = config['LANE_LINE']['THICKNESS']

        # Tailing obj bounding box
        self.tailingobjs_BB_thickness = config['TAILING_OBJ']['BOUDINGBOX_THINKNESS']
        self.tailingobjs_BB_colorB = config['TAILING_OBJ']['BOUDINGBOX_COLOR_B']
        self.tailingobjs_BB_colorG = config['TAILING_OBJ']['BOUDINGBOX_COLOR_G']
        self.tailingobjs_BB_colorR = config['TAILING_OBJ']['BOUDINGBOX_COLOR_R']
        self.tailingobjs_text_size = config['TAILING_OBJ']['TEXT_SIZE']
        self.tailingobjs_distance_decimal_length = config['TAILING_OBJ']['DISTANCE_DECIMAL_LENGTH']

        # Resize settings
        self.resize = config['RESIZE']['ENABLED']
        self.resize_w = config['RESIZE']['WIDTH']
        self.resize_h = config['RESIZE']['HEIGHT']

        # Save settings
        self.save_rawimages = config['SAVE']['RAW_IMAGES']
        self.save_airesultimage = config['SAVE']['AI_RESULT_IMAGE']
        self.save_rawvideo = config['SAVE']['RAW_VIDEO']
        self.save_jsonlog = config['SAVE']['JSON_LOG']
        self.save_extractframe = config['SAVE']['EXTRACT_FRAME']
        self.video_fps = config['SAVE']['VIDEO_FPS']

        # Wait settings
        self.sleep = config['WAIT']['VALUE']
        self.sleep_zeroonadas = config['WAIT']['ZERO_ON_ADAS_EVENT']
        self.sleep_onadas = config['WAIT']['ON_ADAS_EVENT']

        # Plot settings
        self.plot_label = config['PLOT']['LABEL']
        self.run_plot = config['PLOT']['RUN']
        self.save_plot = config['PLOT']['SAVE']
        self.save_plot_dir = config['PLOT']['SAVE_DIR']


        # Evaluation settings
        self.eval_static_case_run_time = config['EVALUATION']['RUN_TIME']['STATIC']
        self.eval_dynamic_case_run_time = config['EVALUATION']['RUN_TIME']['DYNAMIC']

        self.eval_camera_rawimage_dir = config['EVALUATION']['CAMERA']['DATASET_DIR']
        self.script_path = config['EVALUATION']['CAMERA']['SCRIPT_PATH']
        self.remote_csv_file_path = config['EVALUATION']['CAMERA']['CSV_FILE_PATH']
        # self.eval_save_ai_result_dir = config['EVALUATION']['EVAL_SAVE_AI_RESULT_DIR']

        self.eval_save_jsonlog_dir = config['EVALUATION']['LOCAL']['JSONLOG_DIR']
        self.evaluationdata_dir = config['EVALUATION']['LOCAL']['DATASET_DIR']

        # Analysis settings
        self.analysis_run = config['ANALYSIS']['RUN']
        self.analysis_json_log_path = config['ANALYSIS']['JSON_LOG_PATH']
        self.analysis_jsonlog_dir = config['ANALYSIS']['JSON_LOG_DIR']

        # Test settings
        self.test_version_fw_version = config['TEST']['VERSION']['FW_VERSION']
        self.test_version_mcu_version = config['TEST']['VERSION']['MCU_VERSION']
        self.test_version_adas_version = config['TEST']['VERSION']['ADAS_VERSION']
        self.test_adas_config_path = config['TEST']['CONFIG_PARAMS']['CONFIG_PATH']
        self.test_check_duration = config['TEST']['MONITOR']['DURATION']
        self.test_check_interval = config['TEST']['MONITOR']['INTERVAL']
        self.test_threshold_inference_time = config['TEST']['THRESHOLD']['INFERENCE_TIME']
        self.test_threshold_buffer_size_ratio = config['TEST']['THRESHOLD']['BUFFER_SIZE_RATIO']
        self.test_cpu_threshold = config['TEST']['THRESHOLD']['CPU_USAGE']
        self.test_mem_threshold = config['TEST']['THRESHOLD']['MEMORY_USAGE']


        # Varify settings
        self.varify_camera_config_file_path = config['VARIFY']['CAMERA']['CONFIG_PATH']
        self.varify_run_historical_time = config['VARIFY']['CAMERA']['RUN_HISTORICAL_TIME']
        self.varify_save_jsonlog_dir = config['VARIFY']['LOCAL']['SAVE_JSONLOG_DIR']



        # Check if the operating system is Windows
        if os.name == 'nt':  # 'nt' is the name for Windows systems
            self.csv_file = os.path.normpath(self.csv_file).strip('"')
            self.im_dir = os.path.normpath(self.im_dir).strip('"')