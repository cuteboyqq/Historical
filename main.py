from task.Historical import *
from config.config import *
from utils.connection import Connection

# def visualize(self,mode=None,
#                   jsonlog_from=None,
#                   plot_distance=False,
#                   gen_raw_video=False)
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

if __name__=="__main__":
    args = get_args()
    history = Historical(args)

    OFFLINE_JSONLOG_FROM_CAMERA = False
    PLOT_DISTANCE = False
    COVERT_TO_RAW_VIDEO=False
    SEMI_ONLINE = False
    ONLINE = True
    OFFLINE_JSONLOG_FROM_ONLINE = False

    if OFFLINE_JSONLOG_FROM_CAMERA:
        history.visualize(mode="offline",jsonlog_from="camera")

    if PLOT_DISTANCE:
        history.visualize(plot_distance=True)

    if COVERT_TO_RAW_VIDEO:
        history.visualize(gen_raw_video=True)

    if SEMI_ONLINE:
        history.visualize(mode="semi-online")
    if ONLINE:
        history.visualize(mode="online")

    if OFFLINE_JSONLOG_FROM_ONLINE:
        history.visualize(mode="offline",jsonlog_from="online")
    
 