import cv2
import matplotlib.pyplot as plt
import csv
import json
import os
from PIL import Image, ImageDraw
import logging
import numpy as np
from utils.saver import ImageSaver
import glob
import yaml
from config.args import Args
import colorlog


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Create a named logger
# logger = logging.getLogger('my_application')
# # logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG or as needed

# # Create a stream handler
# handler = logging.StreamHandler()

# # Create a color formatter
# formatter = colorlog.ColoredFormatter(
#     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     # Define colors for different log levels
#     log_colors={
#         'DEBUG': 'cyan',
#         'INFO': 'green',
#         'WARNING': 'yellow',
#         'ERROR': 'red',
#         'CRITICAL': 'bold_red',
#     }
# )
# handler.setFormatter(formatter)

# # Add the handler to the logger
# logger.addHandler(handler)


class BaseDataset:
    def __init__(self,args):

        # self.logging = logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        # Input settings
        self.im_dir = args.im_dir
        self.im_folder = None
        self.image_basename = args.image_basename
        self.csv_file_path = args.csv_file
        self.csv_file = os.path.basename(self.csv_file_path)
        self.image_format = args.image_format
        self.tftp_ip = args.tftp_ip

        # Enable / Disable save AI result images
        self.save_airesultimage = args.save_airesultimage

        self.save_rawvideo = args.save_rawvideo
        self.save_rawvideopath = args.save_rawvideopath
        self.save_jsonlog = args.save_jsonlog
        self.save_rawimages = args.save_rawimages

        # How fast of show the images
        self.sleep = args.sleep
        self.sleep_zeroonadas = args.sleep_zeroonadas
        self.sleep_onadas = args.sleep_onadas

        # Enable / disable plot frame-distance
        self.show_distanceplot = args.show_distanceplot
        self.distances = []
        self.frame_ids = []

        # Enable / disable show objs on images
        self.show_airesultimage = args.show_airesultimage
        self.show_detectobjs = args.show_detectobjs
        self.show_tailingobjs = args.show_tailingobjs
        self.show_vanishline = args.show_vanishline
        self.show_adasobjs = args.show_adasobjs
        self.showtailobjBB_corner = args.showtailobjBB_corner
        self.show_laneline = args.show_laneline
        self.show_distancetitle = args.show_distancetitle

        self.tailingobjs_BB_thickness = args.tailingobjs_BB_thickness
        self.tailingobjs_BB_colorB = args.tailingobjs_BB_colorB
        self.tailingobjs_BB_colorG = args.tailingobjs_BB_colorG
        self.tailingobjs_BB_colorR = args.tailingobjs_BB_colorR
        self.tailingobjs_text_size = args.tailingobjs_text_size

        self.tailingObj_x1 = None
        self.tailingObj_y1 = None

        self.ADAS_FCW = False
        self.ADAS_LDW = False

        # Enable/Disable show customer resized images
        self.resize = args.resize
        self.resize_w = args.resize_w
        self.resize_h = args.resize_h

        #csv file list
        self.csv_file_list = ['assets/csv_file/golden_date_ImageMode_10m.csv',
                                'assets/csv_file/golden_date_ImageMode_20m.csv',
                                'assets/csv_file/golden_date_ImageMode_30m.csv',
                                'assets/csv_file/golden_date_ImageMode_40m.csv',
                                'assets/csv_file/golden_date_ImageMode_50m.csv',]
        self.list_label = ['GT_10m',
                           'GT_20m',
                           'GT_30m',
                           'GT_40m',
                           'GT_50m']
        
        #plot label
        self.plot_label = args.plot_label

        self.img_saver = ImageSaver()


        # Video extract frames parameters
        self.skip_frame = 10
        self.crop = True
        self.crop_top = 0.3
        self.crop_left = 0.1
        self.crop_right = 0.9

        self.model_w = args.model_w
        self.model_h = args.model_h


    def display_parameters(self):
        logging.info(f"IMAGE DIRECTORY: {self.im_dir}")
        # logging.info(f"SAVE IMAGE DIRECTORY: {self.save_imdir}")
        logging.info(f"IMAGE BASENAME: {self.image_basename}")
        logging.info(f"CSV FILE PATH: {self.csv_file_path}")
        logging.info(f"IMAGE FORMAT: {self.image_format}")
        logging.info(f"TFTP IP: {self.tftp_ip}")
        logging.info(f"SAVE AI RESULT IMAGE: {self.save_airesultimage}")
        logging.info(f"SAVE RAW VIDEO: {self.save_rawvideo}")
        logging.info(f"SAVE RAW VIDEO PATH: {self.save_rawvideopath}")
        # logging.info(f"SAVE JSON LOG PATH: {self.save_jsonlogpath}")
        logging.info(f"SAVE JSON LOG: {self.save_jsonlog}")
        logging.info(f"SLEEP: {self.sleep}")
        logging.info(f"SLEEP ZERO ON ADAS: {self.sleep_zeroonadas}")
        logging.info(f"SLEEP ON ADAS: {self.sleep_onadas}")
        logging.info(f"SHOW DISTANCE PLOT: {self.show_distanceplot}")
        logging.info(f"SHOW AI RESULT IMAGE: {self.show_airesultimage}")
        logging.info(f"SHOW DETECT OBJS: {self.show_detectobjs}")
        logging.info(f"SHOW TAILING OBJS: {self.show_tailingobjs}")
        logging.info(f"SHOW VANISH LINE: {self.show_vanishline}")
        logging.info(f"SHOW ADAS OBJS: {self.show_adasobjs}")
        logging.info(f"SHOW TAIL OBJ BB CORNER: {self.showtailobjBB_corner}")
        logging.info(f"SHOW LANE LINE: {self.show_laneline}")
        logging.info(f"RESIZE: {self.resize}")
        logging.info(f"RESIZE WIDTH: {self.resize_w}")
        logging.info(f"RESIZE HEIGHT: {self.resize_h}")
        logging.info(f"PLOT LABEL: {self.plot_label}")


    def video_extract_frame(self,video_path,crop):
        vidcap = cv2.VideoCapture(video_path)
        success,image = vidcap.read()
        count = 0

        if crop is None:
            crop = self.crop

        while success:
            if count% (self.skip_frame)==0:
                filename_ = self.image_basename + str(count) + ".jpg"
                # img_path = os.path.join(save_dir,filename_)               
                # cv2.imwrite(img_path,image)
                if crop:
                    # Get the dimensions of the image
                    height, width = image.shape[:2]

                    # Calculate the cropping coordinates
                    top_crop = int(height * self.crop_top)
                    left_crop = int(width * self.crop_left)
                    right_crop = int(width * self.crop_right)

                    # Crop the image
                    image = image[top_crop:, left_crop:right_crop]

                if self.resize:
                    image = cv2.resize(image, (self.resize_w, self.resize_h), interpolation=cv2.INTER_AREA)
                if count >= 20000:
                    self.img_saver.save_image(image,count)
                logging.info('save frame %d',count)
            success,image = vidcap.read()
            count += 1

    # def videos_extract_frame(self):
    #     video_path_list = glob.glob(os.path.join(self.video_dir,"*.mkv"))
    #     for i in range(len(video_path_list)):
    #         self.video_extract_frame(video_path_list[i])

    def draw_tailing_obj(self,tailing_objs,im):
        distance_to_camera = tailing_objs[0].get('tailingObj.distanceToCamera', None)
        tailingObj_id = tailing_objs[0].get('tailingObj.id', None)
        tailingObj_x1 = tailing_objs[0].get('tailingObj.x1', None)
        tailingObj_y1 = tailing_objs[0].get('tailingObj.y1', None)
        tailingObj_x2 = tailing_objs[0].get('tailingObj.x2', None)
        tailingObj_y2 = tailing_objs[0].get('tailingObj.y2', None)
        # logging.info(f"tailingObj_id:{tailingObj_id}")
        # logging.info(f"tailingObj_x1:{tailingObj_x1}")
        # logging.info(f"tailingObj_y1:{tailingObj_y1}")
        # logging.info(f"tailingObj_x2:{tailingObj_x2}")
        # logging.info(f"tailingObj_y2:{tailingObj_y2}")
        tailingObj_label = tailing_objs[0].get('tailingObj.label', None)

        self.tailingObj_x1 = tailingObj_x1
        self.tailingObj_y1 = tailingObj_y1

        text_thickness = 0.45
        # Draw bounding box on the image
        if self.showtailobjBB_corner:
            top_left = (tailingObj_x1, tailingObj_y1)
            bottom_right = (tailingObj_x2, tailingObj_y2)
            top_right = (tailingObj_x2,tailingObj_y1)
            bottom_left = (tailingObj_x1,tailingObj_y2) 
            BB_width = abs(tailingObj_x2 - tailingObj_x1)
            BB_height = abs(tailingObj_y2 - tailingObj_y1)
            divide_length = 5
            thickness = 3
            color = (0,255,255)

            if distance_to_camera>=10:
                color = (0,255,255)
                thickness = 3
                text_thickness = 0.40
            elif distance_to_camera>=7 and distance_to_camera<10:
                color = (0,100,255)
                thickness = 5
                text_thickness = 0.46
            elif distance_to_camera<7:
                color = (0,25,255)
                thickness = 7
                text_thickness = 0.50

            # Draw each side of the rectangle
            cv2.line(im, top_left, (top_left[0]+int(BB_width/divide_length), top_left[1]), color, thickness)
            cv2.line(im, top_left, (top_left[0], top_left[1] + int(BB_height/divide_length)), color, thickness)

            cv2.line(im, bottom_right,(bottom_right[0] - int(BB_width/divide_length),bottom_right[1]), color, thickness)
            cv2.line(im, bottom_right,(bottom_right[0],bottom_right[1] - int(BB_height/divide_length) ), color, thickness)


            cv2.line(im, top_right, ((top_right[0]-int(BB_width/divide_length)), top_right[1]), color, thickness)
            cv2.line(im, top_right, (top_right[0], (top_right[1]+int(BB_height/divide_length))), color, thickness)

            cv2.line(im, bottom_left, ((bottom_left[0]+int(BB_width/divide_length)), bottom_left[1]), color, thickness)
            cv2.line(im, bottom_left, (bottom_left[0], (bottom_left[1]-int(BB_height/divide_length))), color, thickness)
        else:
            cv2.rectangle(im, (tailingObj_x1, tailingObj_y1), (tailingObj_x2, tailingObj_y2), color=(0,255,255), thickness=2)


        # if tailingObj_label=='VEHICLE':
            # Put text on the image
        # if not self.show_detectobjs:
        cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
        cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.1, color, 1, cv2.LINE_AA)

        if distance_to_camera is not None:
            self.distances.append(distance_to_camera)
        else:
            self.distances.append(float('nan'))  # Handle missing values

    
    def draw_detect_objs(self,detect_objs,im):
        # Draw detectObj bounding boxes
        for obj_type, obj_list in detect_objs.items():
            for obj in obj_list:
                label = obj.get(f'detectObj.label', '')
                x1 = obj.get(f'detectObj.x1', 0)
                y1 = obj.get(f'detectObj.y1', 0)
                x2 = obj.get(f'detectObj.x2', 0)
                y2 = obj.get(f'detectObj.y2', 0)
                confidence = obj.get(f'detectObj.confidence', 0.0)
                
                if self.show_tailingobjs and self.tailingObj_x1==x1 and self.tailingObj_y1==y1:
                    # Draw bounding box
                    continue
                else:
                    # Draw bounding box
                    if label == "VEHICLE":
                        color=(255,150,0)
                    elif label=="HUMAN":
                        color=(0,128,255)
                    cv2.rectangle(im, (x1, y1), (x2, y2), color=color, thickness=1)
                    cv2.putText(im, f'{label} {confidence:.2f}', (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

    def draw_vanish_objs(self,vanish_objs,im):
        vanishlineY = vanish_objs[0].get('vanishlineY', None)
        logging.info(f'vanishlineY:{vanishlineY}')
        x2 = im.shape[1]
        cv2.line(im, (0, vanishlineY), (x2, vanishlineY), (0, 255, 255), thickness=1)
        cv2.putText(im, 'VanishLineY:' + str(round(vanishlineY,3)), (10,30), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)


    def draw_ADAS_objs(self,ADAS_objs,im):
        self.ADAS_FCW = ADAS_objs[0].get('FCW',None)
        self.ADAS_LDW = ADAS_objs[0].get('LDW',None)
        logging.info(f'ADAS_FCW:{self.ADAS_FCW}')
        logging.info(f'ADAS_LDW:{self.ADAS_LDW}')
        if self.ADAS_FCW==True:
            cv2.putText(im, 'Collision Warning', (150,50), cv2.FONT_HERSHEY_SIMPLEX,1.3, (0, 128, 255), 2, cv2.LINE_AA)
        if self.ADAS_LDW==True:
            cv2.putText(im, 'Departure Warning', (150,80), cv2.FONT_HERSHEY_SIMPLEX,1.3, (128, 0, 255), 2, cv2.LINE_AA)

    def draw_laneline_objs(self,lane_info,im):
        pLeftCarhood = (lane_info[0]["pLeftCarhood.x"], lane_info[0]["pLeftCarhood.y"])
        pLeftFar = (lane_info[0]["pLeftFar.x"], lane_info[0]["pLeftFar.y"])
        pRightCarhood = (lane_info[0]["pRightCarhood.x"], lane_info[0]["pRightCarhood.y"])
        pRightFar = (lane_info[0]["pRightFar.x"], lane_info[0]["pRightFar.y"])

        width_Cardhood = abs(pRightCarhood[0] - pLeftCarhood[0])
        width_Far = abs(pRightFar[0] - pLeftFar[0])

        pLeftCarhood_mainlane = (pLeftCarhood[0]+int(width_Cardhood/4.0),pLeftCarhood[1])
        pLeftFar_mainlane = (pLeftFar[0]+int(width_Far/4.0),pLeftFar[1])
        pRightCarhood_mainlane = (pRightCarhood[0]-int(width_Cardhood/4.0),pRightCarhood[1])
        pRightFar_mainlane = (pRightFar[0]-int(width_Far/4.0),pRightFar[1])               
        # Create an array of points to define the polygon
        points = np.array([pLeftCarhood, pLeftFar, pRightFar, pRightCarhood], dtype=np.int32)
        points_mainlane = np.array([pLeftCarhood_mainlane,
                                    pLeftFar_mainlane,
                                    pRightFar_mainlane,
                                    pRightCarhood_mainlane], dtype=np.int32)
        # Reshape points array for polylines function
        points = points.reshape((-1, 1, 2))

        # Create an overlay for the filled polygon
        overlay = im.copy()
        cv2.fillPoly(overlay, [points_mainlane], color=(0, 255, 0))  # Green filled polygon

        # Blend the overlay with the original image
        alpha = 0.35  # Transparency factor
        cv2.addWeighted(overlay, alpha, im, 1 - alpha, 0, im)

        # Optionally, draw the polygon border
        # cv2.polylines(image, [points], isClosed=True, color=(0, 0, 0), thickness=2)  # Black border

        # Draw for direction
        # pmiddleFar_mainlane = (int((pLeftFar[0]+pRightFar[0])/2.0),int((pLeftFar[1]+pRightFar[1])/2.0))
        # pmiddleCarhood_mainlane = (int((pLeftCarhood[0]+pRightCarhood[0])/2.0),int((pLeftCarhood[1]+pRightCarhood[1])/2.0))
        # cv2.line(image, pmiddleFar_mainlane, pmiddleCarhood_mainlane, (0, 255, 255), 1)  # Blue line

        # Draw left lane line
        cv2.line(im, pLeftCarhood, pLeftFar, (255, 0, 0), 2)  # Blue line
        # Draw right lane line
        cv2.line(im, pRightCarhood, pRightFar, (0, 0, 255), 2)  # Red line

    def extract_distance_data(self,csv_file):
        frame_ids = []
        distances = []

        with open(csv_file, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            for row in reader:
                # Debug print for each row
                logging.info(f"Row: {row}")

                # Join the row into a single string
                row_str = ','.join(row)
                
                # Find the position of 'json:'
                json_start = row_str.find('json:')
                if json_start != -1:
                    json_data = row_str[json_start + 5:].strip()
                    if json_data.startswith('"') and json_data.endswith('"'):
                        json_data = json_data[1:-1]  # Remove enclosing double quotes
                    
                    # Replace any double quotes escaped with backslashes
                    json_data = json_data.replace('\\"', '"')
                    
                    try:
                        data = json.loads(json_data)
                        logging.info(f"Parsed JSON: {data}")

                        for frame_id, frame_data in data['frame_ID'].items():
                            frame_ids.append(int(frame_id))
                            tailing_objs = frame_data.get('tailingObj', [])
                            if tailing_objs:
                                distance_to_camera = tailing_objs[0].get('tailingObj.distanceToCamera', None)
                                if distance_to_camera is not None:
                                    distances.append(distance_to_camera)
                                else:
                                    distances.append(float('nan'))  # Handle missing values
                            else:
                                distances.append(float('nan'))  # Handle missing values
                    except json.JSONDecodeError as e:
                        logging.info(f"Error decoding JSON: {e}")
                    except Exception as e:
                        logging.info(f"Unexpected error: {e}")

        return frame_ids, distances
    
    def compare_distance_in_two_csv_file(self):
        return NotImplemented
    
    def compare_distance_in_multiple_csv_file(self):
        return NotImplemented

    def draw_AI_result_to_images(self):
        return NotImplemented
    
    '''
    -------------------------------------
    FUNC:save_rawimages_to_videoclip
        Purpose: 
            Convert Raw images to raw video clip
    ------------------------------------
    '''
    def convert_rawimages_to_videoclip(self,im_dir=None):

        if im_dir is None:
            im_dir = self.im_dir

        video_dir = self.save_rawvideopath.split(os.path.basename(self.save_rawvideopath))[0]
        logging.info(video_dir)
        os.makedirs(video_dir,exist_ok=True)
        # Get list of image files, assuming they are named RawFrame_[index].png
        images = [img for img in os.listdir(self.im_dir) if img.endswith(".png")]
        images.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))  # Sort by index

        # Check if there are images in the folder
        if not images:
            logging.error("No images found in the folder.")
            exit()

        # Read the first image to get the size (width and height)
        frame = cv2.imread(os.path.join(im_dir, images[0]))
        height, width, layers = frame.shape

        # Define the codec and create a VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # or use 'XVID' for .avi files
        video = cv2.VideoWriter(self.save_rawvideopath, fourcc, 7.0, (width, height))

        # Read each image and write it to the video file
        for image in images:
            img_path = os.path.join(im_dir, image)
            img = cv2.imread(img_path)
            video.write(img)

        # Release the video writer object
        video.release()
        cv2.destroyAllWindows()

        logging.info(f"Video saved as {self.save_rawvideopath}")
    

    '''
    ------------------------------------------
    FUNC: process_json_log
        input : json_log only one frame
        # Example usage
        json_log = {
            "frame_ID": {
                "89": {
                    "ADAS": [{"FCW": false, "LDW": false}],
                    "detectObj": {
                        "VEHICLE": [
                            {"detectObj.confidence": 0.8481980562210083, "detectObj.label": "VEHICLE", "detectObj.x1": 269, "detectObj.x2": 312, "detectObj.y1": 160, "detectObj.y2": 203},
                            {"detectObj.confidence": 0.8470443487167358, "detectObj.label": "VEHICLE", "detectObj.x1": 78, "detectObj.x2": 143, "detectObj.y1": 154, "detectObj.y2": 207}
                        ]
                    },
                    "tailingObj": [
                        {"tailingObj.distanceToCamera": 27.145750045776367, "tailingObj.id": 3, "tailingObj.label": "VEHICLE", "tailingObj.x1": 230, "tailingObj.x2": 257, "tailingObj.y1": 166, "tailingObj.y2": 193}
                    ],
                    "vanishLineY": [{"vanishlineY": 171}]
                }
            }
        }
        Purpose : Process just one frame JSON log
    ------------------------------------------
    '''
    def process_json_log(self,json_log):
        try:
            log_data = json.loads(json_log)
            logging.info("=======================================================================================")
            logging.info("Received [JSON]: %s", json.dumps(log_data))
            logging.info("=======================================================================================")
            # print("Received JSON:", json.dumps(log_data, indent=4))  # Print formatted JSON

            frame_ID = list(log_data["frame_ID"].keys())[0]  # Extract the first frame_ID key
            
            
            tailing_objs = log_data["frame_ID"][frame_ID]["tailingObj"]
            vanishline_objs = log_data["frame_ID"][frame_ID]["vanishLineY"]
            ADAS_objs = log_data["frame_ID"][frame_ID]["ADAS"]
            lane_info = log_data["frame_ID"][frame_ID]["LaneInfo"]
            detect_objs = log_data["frame_ID"][frame_ID]["detectObj"]["VEHICLE"]

            image_path = f"{self.im_dir}/{self.image_basename}{frame_ID}.{self.image_format}"
            logging.info(image_path)
            image = cv2.imread(image_path)
            image = cv2.resize(image, (self.model_w, self.model_h), interpolation=cv2.INTER_AREA)

            cv2.putText(image, 'frame_ID:'+str(frame_ID), (10,10), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)

            if self.show_adasobjs:
                for obj in ADAS_objs:
                    self.ADAS_FCW = obj["FCW"]
                    self.ADAS_LDW = obj["LDW"]
                    logging.info(f'ADAS_FCW:{self.ADAS_FCW}')
                    logging.info(f'ADAS_LDW:{self.ADAS_LDW}')
                    if self.ADAS_FCW==True or self.ADAS_FCW==1 or self.ADAS_FCW=="true":
                        cv2.putText(image, 'Forward Collision', (80,80), cv2.FONT_HERSHEY_SIMPLEX,1.3, (0, 0, 255), 2, cv2.LINE_AA)
                    if self.ADAS_LDW==True or self.ADAS_LDW==1 or self.ADAS_FCW=="true":
                        cv2.putText(image, 'Lane Departure', (80,100), cv2.FONT_HERSHEY_SIMPLEX,1.3, (0, 0, 255), 2, cv2.LINE_AA)

            if self.show_vanishline:
                for obj in vanishline_objs:
                    vanishlineY = obj["vanishlineY"]
                    x2 = image.shape[1]
                    cv2.line(image, (0, vanishlineY), (x2, vanishlineY), (0, 255, 255), thickness=1)
                    cv2.putText(image, 'VanishLineY:' + str(round(vanishlineY,3)), (10,30), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
            



            text_thickness = 0.45
            if self.show_tailingobjs and tailing_objs:
                custom_text_thickness = 0.45
                if self.tailingobjs_text_size is not None:
                    custom_text_thickness = self.tailingobjs_text_size
                else:
                    custom_text_thickness = 0.45


                custom_color = (0,255,255)
                if self.tailingobjs_BB_colorB is not None and \
                    self.tailingobjs_BB_colorG is not None and \
                    self.tailingobjs_BB_colorR is not None:
                    custom_color = (self.tailingobjs_BB_colorB,self.tailingobjs_BB_colorG,self.tailingobjs_BB_colorR)
                else:
                    custom_color = (0,255,255)

                custom_thickness = 2
                if self.tailingobjs_BB_thickness is not None:
                    custom_thickness = self.tailingobjs_BB_thickness
                else:
                    custom_thickness = 2


                for obj in tailing_objs:
                    tailingObj_x1, tailingObj_y1 = obj["tailingObj.x1"], obj["tailingObj.y1"]
                    tailingObj_x2, tailingObj_y2 = obj["tailingObj.x2"], obj["tailingObj.y2"]
                    distance = obj["tailingObj.distanceToCamera"]
                    label = obj["tailingObj.label"]
                    distance_to_camera = obj['tailingObj.distanceToCamera']
                    tailingObj_id = obj['tailingObj.id']
                    tailingObj_label = obj['tailingObj.label']
                    # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    if self.show_distancetitle:
                        cv2.putText(image, str(round(distance_to_camera,1)), (int(self.model_w/3.0), int(self.model_h*11.0/12.0)), cv2.FONT_HERSHEY_SIMPLEX,1.0, (0,255,255), 2, cv2.LINE_AA)


                    im = image
                    color = (0,255,255)
                    if self.showtailobjBB_corner and self.show_tailingobjs:
                        top_left = (tailingObj_x1, tailingObj_y1)
                        bottom_right = (tailingObj_x2, tailingObj_y2)
                        top_right = (tailingObj_x2,tailingObj_y1)
                        bottom_left = (tailingObj_x1,tailingObj_y2) 
                        BB_width = abs(tailingObj_x2 - tailingObj_x1)
                        BB_height = abs(tailingObj_y2 - tailingObj_y1)
                        divide_length = 5
                    
                        if distance>=10:
                            color = (0,255,255)
                            thickness = 3
                            text_thickness = 0.40
                        elif distance>=7 and distance<10:
                            color = (0,100,255)
                            thickness = 5
                            text_thickness = 0.46
                        elif distance<7:
                            color = (0,25,255)
                            thickness = 7
                            text_thickness = 0.50
                        # Draw corner of the rectangle
                        cv2.line(im, top_left, (top_left[0]+int(BB_width/divide_length), top_left[1]), color, thickness)
                        cv2.line(im, top_left, (top_left[0], top_left[1] + int(BB_height/divide_length)), color, thickness)

                        cv2.line(im, bottom_right,(bottom_right[0] - int(BB_width/divide_length),bottom_right[1]), color, thickness)
                        cv2.line(im, bottom_right,(bottom_right[0],bottom_right[1] - int(BB_height/divide_length) ), color, thickness)


                        cv2.line(im, top_right, ((top_right[0]-int(BB_width/divide_length)), top_right[1]), color, thickness)
                        cv2.line(im, top_right, (top_right[0], (top_right[1]+int(BB_height/divide_length))), color, thickness)

                        cv2.line(im, bottom_left, ((bottom_left[0]+int(BB_width/divide_length)), bottom_left[1]), color, thickness)
                        cv2.line(im, bottom_left, (bottom_left[0], (bottom_left[1]-int(BB_height/divide_length))), color, thickness)
                    elif not self.showtailobjBB_corner and self.show_tailingobjs:
                        cv2.rectangle(im, (tailingObj_x1, tailingObj_y1), (tailingObj_x2, tailingObj_y2), color=(0,255,255), thickness=2)
                        # cv2.putText(image, f"{label} ({distance:.2f}m)", (tailingObj_x1, tailingObj_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    if self.show_tailingobjs:
                        if not self.showtailobjBB_corner:
                            cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
                            cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.05, color, 1, cv2.LINE_AA)
                        else:
                            cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
                            cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.05, color, 1, cv2.LINE_AA)
            if self.show_detectobjs and detect_objs:
                for obj in detect_objs:
                    x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
                    x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
                    confidence = obj["detectObj.confidence"]
                    label = obj["detectObj.label"]
                    if tailingObj_x1!=x1 and tailingObj_y1!=y1:
                        cv2.rectangle(image, (x1, y1), (x2, y2), (255, 200, 0), 1)
                        cv2.putText(image, f"{label} ({confidence:.2f})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)


            # Draw lane lines if LaneInfo is present
            if lane_info and lane_info[0]["isDetectLine"]:
                pLeftCarhood = (lane_info[0]["pLeftCarhood.x"], lane_info[0]["pLeftCarhood.y"])
                pLeftFar = (lane_info[0]["pLeftFar.x"], lane_info[0]["pLeftFar.y"])
                pRightCarhood = (lane_info[0]["pRightCarhood.x"], lane_info[0]["pRightCarhood.y"])
                pRightFar = (lane_info[0]["pRightFar.x"], lane_info[0]["pRightFar.y"])

                width_Cardhood = abs(pRightCarhood[0] - pLeftCarhood[0])
                width_Far = abs(pRightFar[0] - pLeftFar[0])

                pLeftCarhood_mainlane = (pLeftCarhood[0]+int(width_Cardhood/4.0),pLeftCarhood[1])
                pLeftFar_mainlane = (pLeftFar[0]+int(width_Far/4.0),pLeftFar[1])
                pRightCarhood_mainlane = (pRightCarhood[0]-int(width_Cardhood/4.0),pRightCarhood[1])
                pRightFar_mainlane = (pRightFar[0]-int(width_Far/4.0),pRightFar[1])               
                # Create an array of points to define the polygon
                points = np.array([pLeftCarhood, pLeftFar, pRightFar, pRightCarhood], dtype=np.int32)
                points_mainlane = np.array([pLeftCarhood_mainlane,
                                            pLeftFar_mainlane,
                                            pRightFar_mainlane,
                                            pRightCarhood_mainlane], dtype=np.int32)
                # Reshape points array for polylines function
                points = points.reshape((-1, 1, 2))

                # Create an overlay for the filled polygon
                overlay = image.copy()
                cv2.fillPoly(overlay, [points_mainlane], color=(0, 255, 0))  # Green filled polygon

                # Blend the overlay with the original image
                alpha = 0.35  # Transparency factor
                cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

                # Optionally, draw the polygon border
                # cv2.polylines(image, [points], isClosed=True, color=(0, 0, 0), thickness=2)  # Black border

                # Draw for direction
                # pmiddleFar_mainlane = (int((pLeftFar[0]+pRightFar[0])/2.0),int((pLeftFar[1]+pRightFar[1])/2.0))
                # pmiddleCarhood_mainlane = (int((pLeftCarhood[0]+pRightCarhood[0])/2.0),int((pLeftCarhood[1]+pRightCarhood[1])/2.0))
                # cv2.line(image, pmiddleFar_mainlane, pmiddleCarhood_mainlane, (0, 255, 255), 1)  # Blue line


                # Draw left lane line
                cv2.line(image, pLeftCarhood, pLeftFar, (255, 0, 0), 2)  # Blue line
                # Draw right lane line
                cv2.line(image, pRightCarhood, pRightFar, (0, 0, 255), 2)  # Red line
        
            if self.resize:
                image = cv2.resize(image, (self.resize_w, self.resize_h), interpolation=cv2.INTER_AREA)
            if self.show_airesultimage:
                cv2.imshow("Visualize historical mode online", image)
                if self.ADAS_LDW or self.ADAS_FCW:
                    if self.sleep_zeroonadas:
                        cv2.waitKey(0)  # Display the image for a short time
                    else:
                        cv2.waitKey(self.sleep_onadas)
                else:
                    cv2.waitKey(self.sleep)
            if self.save_airesultimage:
                self.img_saver.save_image(image,frame_ID)
                # cv2.imwrite(f'{self.save_imdir}/frame_{frame_ID}.jpg',image)

            if self.save_jsonlog:
                self.img_saver.save_json_log(log_data)
                # # Save the JSON log to a CSV file
                # with open(f'{self.save_jsonlogpath}', mode='a', newline='') as file:
                #     writer = csv.writer(file)
                #     writer.writerow([json.dumps(log_data)])  # Save frame_ID and JSON log
                    # writer.writerow([frame_ID, json.dumps(log_data)])  # Save frame_ID and JSON log

        except KeyError as e:
            logging.error(f"KeyError: {e} - The key might be missing in the JSON data.")
        except json.JSONDecodeError as e:
            logging.error(f"JSONDecodeError: {e} - The JSON data might be malformed.")
        except Exception as e:
            logging.error(f"Error: {e} - An unexpected error occurred.")
    


    
    
            
    