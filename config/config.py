'''
-----------------------------------------------
Connection parameters
----------------------------------------------
'''
HOSTNAME = '192.168.1.1' # Camera address
PORT = 22 #Camera port
USERNAME = 'root' # Camera user name
PASSWOED = 'ALUDS$#q' #Camera password
REMOTEPATH = '/logging/video-adas/117_video-adas_2024-07-26.csv' # LI80 Camera csv file
LOCALPATH = 'JSON_log.csv' # Local computer csf file
'''
---------------------------------------------------------
Parameter setting , set all the parameters here~~~~
---------------------------------------------------------
'''
# short word of T:True and F:False
# T = True
# F = False

# Enable/Disable show obj on the image
SHOW_AI_RESULT_IMAGE = True
SHOW_DETECT_OBJS = True
SHOW_TAILING_OBJS = True
SHOW_VANISH_LINE = True
SHOW_ADAS_RESULT = True

# Enable / Disable = True / False
SAVE_AI_RESULT_IMAGE = True
SHOW_DISTANCE_PLOT = True
SAVE_RAW_VIDEO = True

# Resize show images
DO_RESIZE = True
RESIZE_WIDTH = 1600
RESIZE_HEIGHT = 900

# Sleep how much ms on cv2.waitKey (WAIT_KEY_VALUE value smaller, play stream will faster)
WAIT_KEY_VALUE = 100

# Paths to your CSV files
CSV_FILE = 'assets/csv_file/117_video-adas_2024-07-26.csv' #live mode
# the RawFrame images directory
IMG_DIR = "assets/images/2024-7-26-16-28"
# Basname of the images
IMAGE_BASE_NAME = "RawFrame_"
# image foramt
IMAGE_FORMAT = "png"
# Directory of saving the AI result images
SAVE_IM_DIR = "/home/ali/Projects/GitHub_Code/ali/Historical/AI_result_image"

#plot label
PLOT_LABEL = "DISTANCE"

TFTP_IP = "192.168.1.10" 

#Save raw video path
SAVE_RAW_VIDEO_PATH = "/home/ali/Projects/GitHub_Code/ali/Historical/runs/output_video.mp4"
'''
----------------------------------------------------------------------------------
Finished setting parameters, now you can go to console and run command : python main.py
----------------------------------------------------------------------------------
'''

def get_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-imdir','--im-dir',help='image directory',default=IMG_DIR)
    parser.add_argument('-saveimdir','--save-imdir',help='save image directory',default=SAVE_IM_DIR)
    parser.add_argument('-imagebasename','--image-basename',help='image base name',default=IMAGE_BASE_NAME)
    parser.add_argument('-csvfile','--csv-file',help='json log csv file',default=CSV_FILE)
    parser.add_argument('-imageformat','--image-format',help='image foramt',default=IMAGE_FORMAT)
    parser.add_argument('-showairesultimage','--show-airesultimage',type=bool,help='show ai result images',default=SHOW_AI_RESULT_IMAGE)
    parser.add_argument('-saveairesultimage','--save-airesultimage',type=bool,help='save ai resul images',default=SAVE_AI_RESULT_IMAGE)
    parser.add_argument('-tftpip','--tftp-ip',help='tftp IP',default=TFTP_IP)

    parser.add_argument('-saverawvideo','--save-rawvideo',type=bool,help='save raw video',default=SAVE_RAW_VIDEO)
    parser.add_argument('-saverawvideopath','--save-rawvideopath',help='save video path',default=SAVE_RAW_VIDEO_PATH)

    parser.add_argument('-showdistanceplot','--show-distanceplot',type=bool,help='show plot result',default=SHOW_DISTANCE_PLOT)
    parser.add_argument('-resize','--resize',type=bool,help='enable/disable resize',default=DO_RESIZE)
    parser.add_argument('-resizew','--resize-w',type=int,help='resize width value',default=RESIZE_WIDTH)
    parser.add_argument('-resizeh','--resize-h',type=int,help='resize height value',default=RESIZE_HEIGHT)
    parser.add_argument('-sleep','--sleep',type=int,help='waitKey how much time',default=WAIT_KEY_VALUE)

    parser.add_argument('-showdetectobjs','--show-detectobjs',type=bool,help='show detection objects',default=SHOW_DETECT_OBJS)
    parser.add_argument('-showtailingobjs','--show-tailingobjs',type=bool,help='show tailing object',default=SHOW_TAILING_OBJS)
    parser.add_argument('-showvanishline','--show-vanishline',type=bool,help='show vanishing line',default=SHOW_VANISH_LINE)
    parser.add_argument('-showadasobjs','--show-adasobjs',type=bool,help='show ADAS result',default=SHOW_ADAS_RESULT)

    parser.add_argument('-plotlabel','--plot-label',help='plot label',default=PLOT_LABEL)
   
    return parser.parse_args()


def get_connection_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-hostname','--host-name',help='host name',default=HOSTNAME)
    parser.add_argument('-port','--port',help='port',type=int, default=PORT)
    parser.add_argument('-username','--user-name',type=str,help='user name',default=USERNAME)
    parser.add_argument('-password','--password',type=str,help='json log csv file',default=PASSWOED)
    parser.add_argument('-remotepath','--remote-path',help='remote path',default=REMOTEPATH)
    parser.add_argument('-localpath','--local_path',help='show ai result images',default=LOCALPATH)

    return parser.parse_args()
