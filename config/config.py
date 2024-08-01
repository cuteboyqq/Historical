'''
Online Mode:
    Input for raw images is set in the camera configuration file located at /customer/adas/config/config.txt.

    To run in historical mode with online visualization:

    1. The online JSON log CSV file will be saved in the local directory: runs/predict[number]/.
    2. The online raw images will be saved in the local directory: LOCAL_RAW_IMG_DIR.
    
Offline Mode:
    This mode retrieves historical JSON logs and raw images from the camera to the local computer if they do not already exist locally. 
    The visualization of the JSON logs will be performed on the local computer.

    1. The offline input JSON log CSV file is located in the directory: LOCAL_CSV_FILE.
    2. The offline input raw images are located in the directory: LOCAL_RAW_IMG_DIR.
'''
'''
Set Input Raw Images Directory (LOCAL_IMG_DIR) & JSON Log CSV File (LOCAL_CSV_FILE)
    Notes:
       If local copies of the raw images and JSON log CSV file are not available, 
       the system will attempt to connect to the camera and download these files 
       using the provided CAMERA_HOSTNAME, CAMERA_USERNAME, and CAMERA_PASSWORD, 
       among other necessary credentials.
       Users can specify the LOCAL_CSV_FILE and LOCAL_IMG_DIR even if these files do not currently exist.

    Connection Requirements:
        The camera must be connected to the local computer via a Type-C to USB cable, micro-USB to USB cable, or over WiFi using SSH.
'''
'''
---------------------------------------------------------
Parameter setting , set all the parameters here~~~~
---------------------------------------------------------
'''
'''
-----------------------------------------------
Connection parameters
----------------------------------------------
'''
CAMERA_HOSTNAME = '192.168.1.1'                                    # Camera address
CAMERA_PORT = 22                                                   # Camera port
CAMERA_USERNAME = 'root'                                           # Camera user name
CAMERA_PASSWOED = 'ALUDS$#q'                                       # Camera password
SERVER_PORT = 4900                                                 # Local computer server port (online server)
TFTP_SERVER_DIR = '/home/ali/Public/tftp'                          # TFTP server directory
TFTP_IP = "192.168.1.10"                                           # TFTP sever ip
CAMERA_RAW_IMAGE_DIR = '/mnt/mmc/adas/debug/raw_images'     # Camera save raw images directory
CAMERA_CSV_FILE_DIR = '/logging/video-adas'                 # Camera save csv file directory
# REMOTEPATH = '/logging/video-adas/117_video-adas_2024-07-26.csv' # LI80 Camera csv file
# LOCALPATH = 'JSON_log.csv' # Local computer csf file
'''
-------------------------------------------------------------------------------------
'''
LOCAL_CSV_FILE = 'assets/csv_file/120_video-adas_2024-08-01.csv' # Local Paths to your CSV files / Offline input CSV file path, 
                                                                 # and this csv file comes from camera or online
LOCAL_RAW_IMG_DIR = "assets/images/2024-8-1-19-46"  # Local directory to the RawFrame images / Online save raw image directory
'''
-------------------------------------------------------------------------------------
'''
IMAGE_BASE_NAME = "RawFrame_"                                                   # Basname of the images
IMAGE_FORMAT = "png"                                                            # Image foramt
PLOT_LABEL = "DISTANCE"                                                         # Label for the plot
# Save path
SAVE_LOCAL_RAW_VIDEO_PATH = "/home/ali/Projects/GitHub_Code/ali/Historical/runs/2024-7-30-13-49.mp4" # save raw video path
SAVE_LOCAL_JSON_LOG_PATH = "/home/ali/Projects/GitHub_Code/ali/Historical/json_log-2024-07-30.csv"   # save json log path
SAVE_LOCAL_AI_RESULT_IM_DIR = "/home/ali/Projects/GitHub_Code/ali/Historical/runs/predict"   # Directory of saving the AI result images
SAVE_AI_RESULT_IMAGE = True     # Save AI result image
SAVE_RAW_VIDEO = True           # Convert raw images inot raw videos
SAVE_JSON_LOG = True            # Save JSON log when run historical mode on line

# Enable/Disable show obj on the image
SHOW_AI_RESULT_IMAGE = True     # Show AI result images
SHOW_DETECT_OBJS = True        # Show detection objects
SHOW_TAILING_OBJS = True        # Show tailing objects
SHOW_VANISH_LINE = True         # Show vanishing line
SHOW_ADAS_RESULT = True         # Show ADAS result
SHOW_LANE_INFO = True           # Show lane line information
SHOW_TAILING_OBJS_BB_CORNER = True# Show tailing object bounding box with corner only
SHOW_DISTANCE_PLOT = True       # Show distance plot

DO_RESIZE = True              # Resized AI result images
RESIZE_WIDTH =  1280         # Resized widt
RESIZE_HEIGHT = 720         # Resized hright

# Sleep how much ms on cv2.waitKey (WAIT_KEY_VALUE value smaller, play stream will faster)
WAIT_KEY_VALUE = 50                 # waitKey value on show images
WAIT_KEY_ZERO_ON_ADAS_EVENT = False  # waitKey value is zero when ADAS event is True
WAIT_KEY_ON_ADAS_EVENT = 50        # waitKey value when ADAS event is True

'''
----------------------------------------------------------------------------------
Finished setting parameters, now you can go to console and run command : python main.py
----------------------------------------------------------------------------------
'''

def get_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-imdir','--im-dir',help='image directory',default=LOCAL_RAW_IMG_DIR)
    parser.add_argument('-saveimdir','--save-imdir',help='save image directory',default=SAVE_LOCAL_AI_RESULT_IM_DIR)
    parser.add_argument('-imagebasename','--image-basename',help='image base name',default=IMAGE_BASE_NAME)
    parser.add_argument('-csvfile','--csv-file',help='json log csv file',default=LOCAL_CSV_FILE)
    parser.add_argument('-imageformat','--image-format',help='image foramt',default=IMAGE_FORMAT)
    parser.add_argument('-showairesultimage','--show-airesultimage',type=bool,help='show ai result images',default=SHOW_AI_RESULT_IMAGE)
    parser.add_argument('-saveairesultimage','--save-airesultimage',type=bool,help='save ai resul images',default=SAVE_AI_RESULT_IMAGE)
    parser.add_argument('-tftpip','--tftp-ip',help='tftp IP',default=TFTP_IP)

    parser.add_argument('-saverawvideo','--save-rawvideo',type=bool,help='save raw video',default=SAVE_RAW_VIDEO)
    parser.add_argument('-savejsonlog','--save-jsonlog',type=bool,help='save json log',default=SAVE_JSON_LOG)
    parser.add_argument('-saverawvideopath','--save-rawvideopath',help='save video path',default=SAVE_LOCAL_RAW_VIDEO_PATH)
    parser.add_argument('-savejsonlogpath','--save-jsonlogpath',help='save json log path',default=SAVE_LOCAL_JSON_LOG_PATH)

    parser.add_argument('-showdistanceplot','--show-distanceplot',type=bool,help='show plot result',default=SHOW_DISTANCE_PLOT)
    parser.add_argument('-resize','--resize',type=bool,help='enable/disable resize',default=DO_RESIZE)
    parser.add_argument('-resizew','--resize-w',type=int,help='resize width value',default=RESIZE_WIDTH)
    parser.add_argument('-resizeh','--resize-h',type=int,help='resize height value',default=RESIZE_HEIGHT)
    parser.add_argument('-sleep','--sleep',type=int,help='waitKey how much time',default=WAIT_KEY_VALUE)
    parser.add_argument('-sleeponadas','--sleep-onadas',type=int,help='waitKey on ADAS event',default=WAIT_KEY_ON_ADAS_EVENT)
    parser.add_argument('-sleepzeroonadas','--sleep-zeroonadas',type=bool,help='waitKey 0 on ADAS event',default=WAIT_KEY_ZERO_ON_ADAS_EVENT)

    parser.add_argument('-showdetectobjs','--show-detectobjs',type=bool,help='show detection objects',default=SHOW_DETECT_OBJS)
    parser.add_argument('-showtailingobjs','--show-tailingobjs',type=bool,help='show tailing object',default=SHOW_TAILING_OBJS)
    parser.add_argument('-showvanishline','--show-vanishline',type=bool,help='show vanishing line',default=SHOW_VANISH_LINE)
    parser.add_argument('-showadasobjs','--show-adasobjs',type=bool,help='show ADAS result',default=SHOW_ADAS_RESULT)
    parser.add_argument('-showtailobjBBcorner','--showtailobjBB-corner',type=bool,help='show tailobj bounding box corner',default=SHOW_TAILING_OBJS_BB_CORNER)
    parser.add_argument('-showlaneline','--show-laneline',type=bool,help='show lane line information',default=SHOW_LANE_INFO)
    parser.add_argument('-plotlabel','--plot-label',help='plot label',default=PLOT_LABEL)

    parser.add_argument('-camerarawimagedir','--camerarawimage-dir',help='show ai result images',default=CAMERA_RAW_IMAGE_DIR)
    parser.add_argument('-cameracsvfiledir','--cameracsvfile-dir',help='show ai result images',default=CAMERA_CSV_FILE_DIR)

    parser.add_argument('-hostname','--host-name',help='host name',default=CAMERA_HOSTNAME)
    parser.add_argument('-port','--port',help='port',type=int, default=CAMERA_PORT)
    parser.add_argument('-serverport','--server-port',help='server port',type=int, default=SERVER_PORT)
    parser.add_argument('-username','--user-name',type=str,help='user name',default=CAMERA_USERNAME)
    parser.add_argument('-password','--password',type=str,help='json log csv file',default=CAMERA_PASSWOED)
    # parser.add_argument('-remotepath','--remote-path',help='remote path',default=REMOTEPATH)
    # parser.add_argument('-localpath','--local-path',help='show ai result images',default=LOCALPATH)
    parser.add_argument('-tftpserverdir','--tftpserver-dir',help='show ai result images',default=TFTP_SERVER_DIR)
   
    return parser.parse_args()


def get_connection_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-hostname','--host-name',help='host name',default=TFTP_IP)
    parser.add_argument('-port','--port',help='port',type=int, default=CAMERA_PORT)
    parser.add_argument('-username','--user-name',type=str,help='user name',default=CAMERA_USERNAME)
    parser.add_argument('-password','--password',type=str,help='json log csv file',default=CAMERA_PASSWOED)
    # parser.add_argument('-remotepath','--remote-path',help='remote path',default=REMOTEPATH)
    # parser.add_argument('-localpath','--local-path',help='show ai result images',default=LOCALPATH)
    parser.add_argument('-tftpserverdir','--tftpserver-dir',help='show ai result images',default=TFTP_SERVER_DIR)
    
    return parser.parse_args()
