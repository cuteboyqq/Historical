import csv
import json
import matplotlib.pyplot as plt
import os
import cv2
from engine.BaseDataset import BaseDataset
# from utils.connection import Connection
import numpy as np
# from config.config import get_connection_args
import logging
import pandas as pd
from utils.plotter import Plotter
# # Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Drawer(BaseDataset):

    def __init__(self, args):
        super().__init__(args)

    def process_json_log(self,json_log,device_image_path):
        """
        Processes a JSON log, performs various visualizations and actions based on its content, and handles exceptions.

        Args:
            json_log (str): JSON formatted string containing log data.

        The function performs the following tasks:
        1. **Parsing JSON**: Attempts to load and parse the provided JSON log. Logs the parsed JSON for debugging purposes.
        2. **Extracting Frame Information**:
            - Extracts `frame_ID` from the JSON data.
            - Retrieves data related to tailing objects, vanish line, ADAS (Advanced Driver Assistance Systems) alerts, and lane information from the JSON.
        3. **Image Processing**:
            - Constructs the path for the corresponding image file and reads it using OpenCV.
            - Resizes the image to the dimensions specified by the model.
            - Annotates the image with the `frame_ID` text.
        4. **ADAS Alerts**:
            - Checks and displays ADAS alerts such as Forward Collision Warning (FCW) and Lane Departure Warning (LDW) if enabled.
        5. **Vanish Line**:
            - Draws a line and displays the vanish line Y-coordinate if enabled.
        6. **Detection Objects**:
            - Draws bounding boxes and annotations for detected objects if enabled.
            - Differentiates between tailing and detected objects, handling overlapping cases by comparing coordinates.
        7. **Tailing Objects**:
            - Draws bounding boxes and annotations for tailing objects, with customizable color and thickness.
            - Optionally draws corners of bounding boxes based on distance to the camera.
        8. **Lane Information**:
            - Draws lane lines and overlays the image with lane information if detected.
        9. **Image Resizing**:
            - Resizes the final image to the dimensions specified by `resize_w` and `resize_h` if enabled.
        10. **Displaying and Saving Results**:
            - Displays the processed image in a window if enabled, with different wait times based on ADAS status.
            - Saves the processed image and JSON log to files if enabled.

        Exceptions:
        - Catches and logs `KeyError` if a required key is missing in the JSON data.
        - Catches and logs `JSONDecodeError` if the JSON data is malformed.
        - Catches and logs any other unexpected exceptions.
        """
        try:
            log_data = json.loads(json_log)
            logging.info("=======================================================================================")
            logging.info("Received [JSON]: %s", json.dumps(log_data))
            logging.info("=======================================================================================")
            # print("Received JSON:", json.dumps(log_data, indent=4))  # Print formatted JSON

            frame_ID = list(log_data["frame_ID"].keys())[0]  # Extract the first frame_ID key
            
            
            tailing_objs = log_data["frame_ID"][frame_ID]["tailingObj"]
            vanishline_objs = log_data["frame_ID"][frame_ID]["vanishLine"]
            ADAS_objs = log_data["frame_ID"][frame_ID]["ADAS"]
            lane_info = log_data["frame_ID"][frame_ID]["LaneInfo"]
            detect_objs = log_data["frame_ID"][frame_ID]["detectObj"]["VEHICLE"]

            image_path = f"{self.im_dir}/{self.image_basename}{frame_ID}.{self.image_format}"
            logging.info(image_path)
            image = cv2.imread(image_path)
            image = cv2.resize(image, (self.model_w, self.model_h), interpolation=cv2.INTER_AREA)

            cv2.putText(image, 'frame_ID:'+str(frame_ID), (10,15), cv2.FONT_HERSHEY_SIMPLEX,0.60, (0, 255, 255), 1, cv2.LINE_AA)

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
                    vanishlineY = obj["vanishLineY"]
                    x2 = image.shape[1]
                    cv2.line(image, (0, vanishlineY), (x2, vanishlineY), (0, 255, 255), thickness=1)
                    cv2.putText(image, 'VanishLineY:' + str(round(vanishlineY,3)), (10,30), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
            


            if self.show_detectobjs and detect_objs:
                if tailing_objs:
                    for obj in tailing_objs:
                        tailingObj_x1, tailingObj_y1 = obj["tailingObj.x1"], obj["tailingObj.y1"]
                        tailingObj_x2, tailingObj_y2 = obj["tailingObj.x2"], obj["tailingObj.y2"]
                        distance = obj["tailingObj.distanceToCamera"]
                        label = obj["tailingObj.label"]
                        distance_to_camera = obj['tailingObj.distanceToCamera']
                        tailingObj_id = obj['tailingObj.id']
                        tailingObj_label = obj['tailingObj.label']


                for obj in detect_objs:
                    x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
                    x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
                    confidence = obj["detectObj.confidence"]
                    label = obj["detectObj.label"]
                    if tailingObj_x1!=x1 and tailingObj_y1!=y1:
                        cv2.rectangle(image, (x1, y1), (x2, y2), (255, 200, 0), 1)
                        if self.show_detectobjinfo:
                            cv2.putText(image, f"{label} ({confidence:.2f})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)
                    elif tailingObj_x1==x1 and tailingObj_y1==y1:
                        if self.show_detectobjinfo:
                            cv2.putText(image, f"Conf:{confidence:.2f}", (x1, y1 - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

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
                        text = f"Distance:{round(distance_to_camera,self.tailingobjs_distance_decimal_length)}m" 
                        xy = (int(self.model_w/3.0), int(self.model_h*11.0/12.0))
                        cv2.putText(image, text, xy, cv2.FONT_HERSHEY_SIMPLEX,1.0, (0,255,255), 2, cv2.LINE_AA)

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

                        if distance>15:
                            color = (0,255,255)
                            thickness = 1
                            text_thickness = 0.40

                        if distance>=10 and distance<=15:
                            color = (0,255,255)
                            thickness = 2
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
                            # Get text size for label
                            text_label = f'{tailingObj_label},ID:{tailingObj_id}'
                            text_distance = f'Distance:{round(distance_to_camera,3)}m'
                            font = cv2.FONT_HERSHEY_SIMPLEX

                            text_size_label, _ = cv2.getTextSize(text_label, font, text_thickness, 1)
                            text_size_distance, _ = cv2.getTextSize(text_distance, font, text_thickness + 0.05, 1)

                            # Calculate the rectangle size
                            rect_x1 = tailingObj_x1
                            rect_y1 = tailingObj_y1 - 10 -  text_size_label[1]  # Adjust height to fit text
                            rect_x2 = tailingObj_x1 + text_size_label[0]
                            rect_y2 = tailingObj_y1 - 10  # Adjust height to fit text

                            # Draw the rectangle
                            cv2.rectangle(im, (rect_x1, rect_y1), (rect_x2, rect_y2), (0, 0, 0), -1)


                            # Calculate the rectangle size
                            rect_x1_d = tailingObj_x1
                            rect_y1_d = tailingObj_y1 - 25 - text_size_distance[1]  # Adjust height to fit text
                            rect_x2_d = tailingObj_x1 + text_size_distance[0]
                            rect_y2_d = tailingObj_y1 - 25    # Adjust height to fit text

                            # Draw the rectangle
                            cv2.rectangle(im, (rect_x1_d, rect_y1_d), (rect_x2_d, rect_y2_d), (0, 0, 0), -1)

                            # Draw the text
                            cv2.putText(im, text_label, (tailingObj_x1, tailingObj_y1 - 10), font, text_thickness, color, 1, cv2.LINE_AA)
                            cv2.putText(im, text_distance, (tailingObj_x1, tailingObj_y1 - 25), font, text_thickness + 0.05, color, 1, cv2.LINE_AA)


                            # cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
                            # cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.05, color, 1, cv2.LINE_AA)
            
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

                # Draw left lane line
                cv2.line(overlay, pLeftCarhood, pLeftFar, (255, 0, 0), self.laneline_thickness)  # Blue line
                # Draw right lane line
                cv2.line(overlay, pRightCarhood, pRightFar, (0, 0, 255), self.laneline_thickness)  # Red line
                # Blend the overlay with the original image
                alpha = self.alpha  # Transparency factor
                cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

                # Optionally, draw the polygon border
                # cv2.polylines(image, [points], isClosed=True, color=(0, 0, 0), thickness=2)  # Black border

                # Draw for direction
                # pmiddleFar_mainlane = (int((pLeftFar[0]+pRightFar[0])/2.0),int((pLeftFar[1]+pRightFar[1])/2.0))
                # pmiddleCarhood_mainlane = (int((pLeftCarhood[0]+pRightCarhood[0])/2.0),int((pLeftCarhood[1]+pRightCarhood[1])/2.0))
                # cv2.line(image, pmiddleFar_mainlane, pmiddleCarhood_mainlane, (0, 255, 255), 1)  # Blue line

            if device_image_path is not None:
                base_directory_name = os.path.basename(os.path.dirname(device_image_path))
                x = int(self.model_w / 4.0)
                y = int(self.model_h / 10.0)
                font = cv2.FONT_HERSHEY_SIMPLEX
                color = (0,0,0)
                cv2.putText(image, base_directory_name, (x, y), font, 0.50, color, 1, cv2.LINE_AA)

            if self.show_devicemode:

                x = int(self.model_w * 2.0/ 4.0)
                y = int(self.model_h / 20.0)
                font = cv2.FONT_HERSHEY_SIMPLEX
                color = (0,0,255)
                mode = 'Unknown'
                if self.mode in ['eval','evaluation']:
                    mode = 'Evaluation (Historical)'
                elif self.mode == 'online':
                    mode = 'Visualize online'
                # elif self.mode == 'sem-online':
                #     mode = 'Visualize semi-online'
            
                cv2.putText(image, 'Mode : ' + mode, (x, y), font, 0.50, color, 1, cv2.LINE_AA)


            if self.resize:
                image = cv2.resize(image, (self.resize_w, self.resize_h), interpolation=cv2.INTER_AREA)
            if self.show_airesultimage:
                cv2.imshow("Visualize AI Result", image)
                if self.ADAS_LDW or self.ADAS_FCW:
                    if self.sleep_zeroonadas:
                        cv2.waitKey(0)  # Display the image for a short time
                    else:
                        cv2.waitKey(self.sleep_onadas)
                else:
                    cv2.waitKey(self.sleep)

            


            if self.save_airesultimage:
                if device_image_path is not None:
                    base_directory_name = os.path.basename(os.path.dirname(device_image_path))
                    GT_dist = os.path.basename(os.path.dirname(os.path.dirname(device_image_path)))
                    data_folder = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(device_image_path))))
                    save_file = "frame_" + str(frame_ID) + ".jpg"
                    current_directory = os.getcwd()
                    save_dir = os.path.join(current_directory,"runs",data_folder,GT_dist,base_directory_name)
                    save_path = os.path.join(save_dir,save_file)
                   
                    os.makedirs(save_dir, exist_ok=True)
                    cv2.imwrite(save_path,image)
                else:
                    self.img_saver.save_image(image,frame_ID)
                    # cv2.imwrite(f'{self.save_imdir}/frame_{frame_ID}.jpg',image)

            if self.save_jsonlog:
                if device_image_path is not None:
                    logging.info(f"device_image_path:{device_image_path}")
                    base_directory_name = os.path.basename(os.path.dirname(device_image_path))
                    GT_dist = os.path.basename(os.path.dirname(os.path.dirname(device_image_path)))
                    data_folder = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(device_image_path))))
                    data_folder = data_folder + '_csv'
                    logging.info(f"base_directory_name:{base_directory_name}")
                    current_directory = os.getcwd()
                    save_dir = os.path.join(current_directory,"runs",data_folder,GT_dist,base_directory_name)
                   
                    logging.info(f"save_file:{save_file}")
                    logging.info(f"current_directory:{current_directory}")
                    txt_file = base_directory_name + '.txt'  # Updated to '.txt' for the file extension
                    os.makedirs(save_dir, exist_ok=True)
                    txt_path = os.path.join(save_dir, txt_file)
                    # Convert the JSON string to a dictionary and then back to a JSON string to remove escape characters
                    json_log_dict = json.loads(json_log)
                    json_log_str = json.dumps(json_log_dict)
                    
                    with open(txt_path, mode='a') as file:  # Opening file in append mode
                        file.write(json_log_str + '\n')  # Writing JSON log to the file without escape characters
                    print(f"JSON log saved to {txt_path}")
                else:
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


    
    def draw_AI_result_to_images(self):
        """
        Processes a CSV file to extract and visualize AI results by overlaying information onto images.

        Steps:
        1. Initialize empty lists for storing frame IDs and distances.
        2. Open and read the CSV file specified by `self.csv_file_path`.
        3. For each row in the CSV:
        - Convert the row to a string and locate the JSON data.
        - Parse the JSON data to extract frame information.
        - For each frame ID:
            a. Construct the image file path using the frame ID.
            b. Read the image using OpenCV.
            c. Overlay frame ID and other AI results onto the image:
                - Tail objects (`tailingObj`)
                - Detected objects (`detectObj`)
                - Vanishing line objects (`vanishLineY`)
                - ADAS objects (`ADAS`)
                - Lane information (`LaneInfo`)
            d. Optionally display the image with overlays and save the image to disk.
        - Handle exceptions related to JSON decoding and other unexpected errors.
        4. If enabled, plot distances to the camera over frame IDs using Matplotlib.

        Attributes:
        - `self.frame_ids`: List of frame IDs extracted from the CSV.
        - `self.distances`: List of distances corresponding to the tailing objects in each frame.
        - `self.csv_file_path`: Path to the CSV file containing AI results.
        - `self.image_basename`: Base name for image files.
        - `self.image_format`: Format of the image files.
        - `self.im_dir`: Directory where image files are located.
        - `self.show_tailingobjs`: Flag to indicate whether to draw tailing objects.
        - `self.show_detectobjs`: Flag to indicate whether to draw detected objects.
        - `self.show_vanishline`: Flag to indicate whether to draw vanish lines.
        - `self.show_adasobjs`: Flag to indicate whether to draw ADAS objects.
        - `self.show_laneline`: Flag to indicate whether to draw lane lines.
        - `self.show_airesultimage`: Flag to control whether to display the processed images.
        - `self.resize`: Flag to indicate whether to resize images before display.
        - `self.resize_w`, `self.resize_h`: Dimensions for resizing images.
        - `self.sleep`, `self.sleep_onadas`, `self.sleep_zeroonadas`: Time to wait before closing the image window.
        - `self.save_airesultimage`: Flag to control whether to save the processed images.
        - `self.save_imdir`: Directory to save the processed images.
        - `self.plot_label`: Label for the distance plot.
        - `self.show_distanceplot`: Flag to control whether to display the distance plot.

        Returns:
        - `frame_ids`: List of frame IDs processed.
        - `distances`: List of distances to the camera for the tailing objects.
        """
        frame_ids = []
        distances = []

        with open(self.csv_file_path, 'r') as file:
            reader = csv.reader(file, delimiter=',')
            for row in reader:
                # Debug print for each row
                # print(f"Row: {row}")
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
                        # print(f"Parsed JSON: {data}")

                        for frame_id, frame_data in data['frame_ID'].items():
                            
                            self.frame_ids.append(int(frame_id))
                            logging.info(f"frame_id:{frame_id}")
                            logging.info(f"csv_file_path:{self.csv_file_path}")

                            # Get image path
                            im_file = self.image_basename + frame_id + "." + self.image_format
                            im_path = os.path.join(self.im_dir,im_file)
                            logging.info(im_path)
                            im = cv2.imread(im_path)

                            cv2.putText(im, 'frame_ID:'+str(frame_id), (10,10), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
                            tailing_objs = frame_data.get('tailingObj', [])
                            vanish_objs = frame_data.get('vanishLineY', [])
                            ADAS_objs = frame_data.get('ADAS', [])
                            detect_objs = frame_data.get('detectObj', {})
                            lane_info = frame_data.get("LaneInfo",[])

                            #---- Draw tailing obj----------
                            if tailing_objs and self.show_tailingobjs:
                                self.draw_tailing_obj(tailing_objs,im)
                            else:
                                self.distances.append(float('nan'))  # Handle missing values

                            # ------Draw detect objs---------
                            if detect_objs and self.show_detectobjs:
                                self.draw_detect_objs(detect_objs,im)                                                   

                            # -------Draw vanish line--------
                            if vanish_objs and self.show_vanishline:
                                self.draw_vanish_objs(vanish_objs,im)

                            # -------Draw ADAS objs-----------------
                            if ADAS_objs and self.show_adasobjs:
                                self.draw_ADAS_objs(ADAS_objs,im)

                            # Draw lane lines if LaneInfo is present
                            if lane_info and lane_info[0]["isDetectLine"] and self.show_laneline:
                                self.draw_laneline_objs(lane_info,im)

                            if self.show_airesultimage:
                                # 按下任意鍵則關閉所有視窗
                                if self.resize:
                                    im = cv2.resize(im, (self.resize_w, self.resize_h), interpolation=cv2.INTER_AREA)
                                cv2.imshow("im",im)
                                if self.ADAS_FCW==True or self.ADAS_LDW==True:
                                    if self.sleep_zeroonadas:
                                        cv2.waitKey(0)
                                    else:
                                        cv2.waitKey(self.sleep_onadas)
                                else:
                                    cv2.waitKey(self.sleep)
                                # cv2.destroyAllWindows()
                            if self.save_airesultimage:
                                os.makedirs(self.save_imdir,exist_ok=True)
                                im_file = self.image_basename + str(frame_id) + "." + self.image_format
                                save_im_path = os.path.join(self.save_imdir,im_file)
                                if not os.path.exists(save_im_path):
                                    cv2.imwrite(save_im_path,im)
                                else:
                                    logging.info(f'image exists :{save_im_path}')
                                
                    except json.JSONDecodeError as e:
                        logging.error(f"Error decoding JSON: {e}")
                    except Exception as e:
                        logging.error(f"Unexpected error: {e}")
        
        if self.show_distanceplot:
            # Plotting the data
            plt.figure(figsize=(200, 100))
            plt.plot(self.frame_ids, self.distances, label=self.plot_label)

            plt.xlabel('FrameID')
            plt.ylabel('tailingObj.distanceToCamera')
            plt.title('Distance to Camera over Frames')
            plt.legend()
            plt.grid(True)

            plt.show()


        return frame_ids, distances
    

    def draw_bounding_boxes(self,frame_ID, tailing_objs,detect_objs,vanish_objs,ADAS_objs,lane_info):
        """
        Draws bounding boxes, labels, and other annotations on an image based on detected objects and information.

        Parameters:
        - `frame_ID`: Identifier for the current frame, used to load the corresponding image file.
        - `tailing_objs`: List of dictionaries containing details about tailing objects.
        - `detect_objs`: List of dictionaries containing details about detected objects.
        - `vanish_objs`: List of dictionaries containing information about vanish lines.
        - `ADAS_objs`: List of dictionaries containing ADAS (Advanced Driver Assistance Systems) information.
        - `lane_info`: List of dictionaries containing information about lane lines.

        Steps:
        1. Construct the path to the image file using `frame_ID` and load the image.
        2. Resize the image to match the model's expected input dimensions.
        3. Check if the image was successfully loaded. Log an error if not found.
        4. Add a text label with `frame_ID` at the top-left corner of the image.
        5. If `tailing_objs` is not empty and `self.show_tailingobjs` is `True`, draw bounding boxes and labels for tailing objects:
        - Set custom text thickness, color, and thickness for the bounding boxes based on instance variables.
        - Draw bounding box corners or rectangles depending on `self.showtailobjBB_corner`.
        - Add text labels for each tailing object, including the label, ID, and distance to the camera.
        6. If `lane_info` is present and `self.show_laneline` is `True`, draw lane lines using the `draw_laneline_objs` method.
        7. If `detect_objs` is not empty and `self.show_detectobjs` is `True`, draw bounding boxes and labels for detected objects.
        8. If `vanish_objs` is not empty and `self.show_vanishline` is `True`, draw a line for the vanish line and add a text label for the vanish line position.
        9. If `ADAS_objs` is not empty and `self.show_adasobjs` is `True`, display ADAS alerts for collision and lane departure warnings.
        10. If `self.resize` is `True`, resize the image to new dimensions specified by `self.resize_w` and `self.resize_h`.
        11. If `self.show_airesultimage` is `True`, display the annotated image using `cv2.imshow`. Handle wait time based on ADAS alerts.
        12. If `self.save_airesultimage` is `True`, save the annotated image using the `img_saver.save_image` method.

        Attributes:
        - `self`: The instance of the class this method belongs to. Used to access instance variables and methods.

        Returns:
        - None. The image `im` is modified in place with bounding boxes and labels drawn on it.
        """
        image_path = os.path.join(self.im_dir, f'{self.image_basename}{frame_ID}.png')
        image = cv2.imread(image_path)
        image = cv2.resize(image, (self.model_w, self.model_h), interpolation=cv2.INTER_AREA)

        if image is None:
            logging.info(f"Image not found: {image_path}")
            return
        
        cv2.putText(image, 'frame_ID:'+str(frame_ID), (10,10), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
        logging.info("============================")
        logging.info(f"frame_ID:{frame_ID}")
        if tailing_objs and self.show_tailingobjs:
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
                tailingObj_label = obj["tailingObj.label"]
                distance_to_camera = obj['tailingObj.distanceToCamera']
                tailingObj_id = obj['tailingObj.id']
                tailingObj_label = obj['tailingObj.label']
                # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)           
                im = image

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
                        text_thickness = 0.45
                    elif distance<7:
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
                elif not self.showtailobjBB_corner and self.show_tailingobjs:
                    cv2.rectangle(im, (tailingObj_x1, tailingObj_y1), (tailingObj_x2, tailingObj_y2), custom_color, custom_thickness)
                    # cv2.putText(image, f"{tailingObj_label} ({distance:.2f}m)", (tailingObj_x1, tailingObj_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                if self.show_tailingobjs:
                    if not self.showtailobjBB_corner:
                        cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, custom_text_thickness, custom_color, 1, cv2.LINE_AA)
                        cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,custom_text_thickness+0.05, custom_color, 1, cv2.LINE_AA)
                    else:
                        cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
                        cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.05, color, 1, cv2.LINE_AA)
                


        # Draw lane lines if LaneInfo is present
        if lane_info and lane_info[0]["isDetectLine"] and self.show_laneline:
            self.draw_laneline_objs(lane_info,im)

        if detect_objs and self.show_detectobjs:
    
            for obj in detect_objs:
                x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
                x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
                confidence = obj["detectObj.confidence"]
                label = obj["detectObj.label"]
                if tailingObj_x1!=x1 and tailingObj_y1!=y1:
                    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 200, 0), 1)
                    cv2.putText(image, f"{label} ({confidence:.2f})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)
        
        if vanish_objs and self.show_vanishline:
            vanishlineY = vanish_objs[0].get('vanishlineY', None)
            logging.info(f'vanishlineY:{vanishlineY}')
            x2 = im.shape[1]
            cv2.line(im, (0, vanishlineY), (x2, vanishlineY), (0, 255, 255), thickness=1)
            cv2.putText(im, 'VanishLineY:' + str(round(vanishlineY,3)), (10,30), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)

        if self.show_adasobjs:
            self.ADAS_FCW = ADAS_objs[0].get('FCW',None)
            self.ADAS_LDW = ADAS_objs[0].get('LDW',None)
            logging.info(f'ADAS_FCW:{self.ADAS_FCW}')
            logging.info(f'ADAS_LDW:{self.ADAS_LDW}')
            if self.ADAS_FCW==True:
                cv2.putText(im, 'Collision Warning', (150,50), cv2.FONT_HERSHEY_SIMPLEX,1.3, (0, 128, 255), 2, cv2.LINE_AA)
            if self.ADAS_LDW==True:
                cv2.putText(im, 'Departure Warning', (150,80), cv2.FONT_HERSHEY_SIMPLEX,1.3, (128, 0, 255), 2, cv2.LINE_AA)

        if self.resize:
            image = cv2.resize(image, (self.resize_w, self.resize_h), interpolation=cv2.INTER_AREA)
        if self.show_airesultimage:
            cv2.imshow("Annotated Image", image)
            if self.ADAS_LDW or self.ADAS_FCW:
                if self.sleep_zeroonadas:
                    cv2.waitKey(0)  # Display the image for a short time
                else:
                    cv2.waitKey(self.sleep_onadas)
            else:
                cv2.waitKey(self.sleep)
        
        if self.save_airesultimage:
            self.img_saver.save_image(image,frame_ID)



    def draw_tailing_obj(self,tailing_objs,im):
        """
        Draws bounding boxes and labels for tailing objects on an image.

        Parameters:
        - `tailing_objs`: A list containing dictionaries with details of tailing objects. Each dictionary includes:
            - 'tailingObj.distanceToCamera': The distance of the object from the camera.
            - 'tailingObj.id': The unique identifier of the tailing object.
            - 'tailingObj.x1': The x-coordinate of the top-left corner of the bounding box.
            - 'tailingObj.y1': The y-coordinate of the top-left corner of the bounding box.
            - 'tailingObj.x2': The x-coordinate of the bottom-right corner of the bounding box.
            - 'tailingObj.y2': The y-coordinate of the bottom-right corner of the bounding box.
            - 'tailingObj.label': The label of the tailing object (e.g., 'VEHICLE').

        - `im`: The image on which the bounding boxes and labels will be drawn.

        Steps:
        1. Extract details (distance to camera, ID, coordinates, and label) from the first tailing object in the list.
        2. Update instance variables `self.tailingObj_x1` and `self.tailingObj_y1` with the coordinates of the tailing object.
        3. Set parameters for drawing the bounding box:
            - `text_thickness`: Thickness of the text used for labels.
            - `color`: Color for the bounding box and text, which varies based on the distance to the camera.
            - `thickness`: Thickness of the bounding box lines.
        4. If `self.showtailobjBB_corner` is `True`, draw bounding box corners using lines instead of a rectangle:
            - Draw lines at each corner of the bounding box with varying thickness and color based on the distance to the camera.
        5. If `self.showtailobjBB_corner` is `False`, draw a standard rectangle bounding box around the object.
        6. Draw text labels above the bounding box:
            - Display the object label and ID.
            - Display the distance to the camera.
        7. Append the distance to `self.distances` list. If the distance is not available, append `float('nan')`.

        Attributes:
        - `self`: The instance of the class this method belongs to. Used to access instance variables like `self.showtailobjBB_corner` and `self.distances`.

        Returns:
        - None. The image `im` is modified in place with the bounding box and labels drawn on it.
        """
        distance_to_camera = tailing_objs[0].get('tailingObj.distanceToCamera', None)
        tailingObj_id = tailing_objs[0].get('tailingObj.id', None)
        tailingObj_x1 = tailing_objs[0].get('tailingObj.x1', None)
        tailingObj_y1 = tailing_objs[0].get('tailingObj.y1', None)
        tailingObj_x2 = tailing_objs[0].get('tailingObj.x2', None)
        tailingObj_y2 = tailing_objs[0].get('tailingObj.y2', None)
        
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
        cv2.rectangle(im,(tailingObj_x1, tailingObj_y1-10),(tailingObj_x2 , tailingObj_y1-10),(50,50,50), -1)
        cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
    
        cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.1, color, 1, cv2.LINE_AA)

        if distance_to_camera is not None:
            self.distances.append(distance_to_camera)
        else:
            self.distances.append(float('nan'))  # Handle missing values

    
    def draw_detect_objs(self,detect_objs,im):
        """
        Draws detected objects with bounding boxes and labels on an image.

        Parameters:
        - `detect_objs`: A dictionary where each key represents an object type and the corresponding value is a 
        list of objects detected. Each object is a dictionary containing keys:
            - 'detectObj.label': The label of the detected object (e.g., 'VEHICLE', 'HUMAN').
            - 'detectObj.x1': The x-coordinate of the top-left corner of the bounding box.
            - 'detectObj.y1': The y-coordinate of the top-left corner of the bounding box.
            - 'detectObj.x2': The x-coordinate of the bottom-right corner of the bounding box.
            - 'detectObj.y2': The y-coordinate of the bottom-right corner of the bounding box.
            - 'detectObj.confidence': The confidence score of the detection.
        - `im`: The image on which the detected objects will be drawn.

        Steps:
        1. Iterate over each object type and its list of detected objects in `detect_objs`.
        2. For each detected object:
        - Extract the label, bounding box coordinates (x1, y1, x2, y2), and confidence score.
        - Skip drawing the bounding box if it matches the specified tailing object coordinates (`self.tailingObj_x1` and `self.tailingObj_y1`).
        - Otherwise, draw the bounding box around the detected object using a specific color based on the label:
            - `VEHICLE`: Orange color.
            - `HUMAN`: Light orange color.
        - Add the label and confidence score text above the bounding box.

        Attributes:
        - `self`: The instance of the class this method belongs to. Used to access the instance variables `self.show_tailingobjs`, `self.tailingObj_x1`, and `self.tailingObj_y1`.

        Returns:
        - None. The image `im` is modified in place with the bounding boxes and labels drawn on it.
        """
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
        """
        Draws lane lines on an image based on lane information.

        Parameters:
        - `lane_info`: A list of dictionaries containing lane line information. The dictionary should have keys 
        "pLeftCarhood.x", "pLeftCarhood.y", "pLeftFar.x", "pLeftFar.y", "pRightCarhood.x", "pRightCarhood.y", 
        "pRightFar.x", and "pRightFar.y", representing points on the left and right sides of the lane.
        - `im`: The image on which the lane lines will be drawn.

        Steps:
        1. Extract points from the `lane_info` for left and right carhood and far points.
        2. Compute the width of the lane at the carhood and far points.
        3. Calculate the main lane points by shifting the left and right carhood and far points towards the center.
        4. Create an array of points defining the lane polygon and another for the main lane polygon.
        5. Create an overlay image and fill the main lane polygon with a green color.
        6. Blend the overlay with the original image using a transparency factor.
        7. Optionally draw the polygon border and direction line (commented out in the code).
        8. Draw the left and right lane lines on the image:
        - Left lane line: Drawn in blue.
        - Right lane line: Drawn in red.

        Attributes:
        - `self`: The instance of the class this method belongs to. Not used directly in this method but included for context.

        Returns:
        - None. The image `im` is modified in place with the lane lines drawn on it.
        """
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