import csv
import json
import matplotlib.pyplot as plt
import os
import cv2
from engine.BaseDataset import BaseDataset
from utils.connection import Connection
import numpy as np
from config.config import get_connection_args
import logging
import pandas as pd
# # Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Historical(BaseDataset):
    def __init__(self,args):
        super().__init__(args)
        self.tftpserver_dir = None
        self.camera_rawimages_dir = args.camerarawimage_dir
        self.camera_csvfile_dir = args.cameracsvfile_dir
        self.current_dir = os.getcwd() # .../Historical
        # self.logging = logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        # con_args = get_connection_args()
        self.Connect = Connection(args)
        self.tftpserver_dir = args.tftpserver_dir
        self.im_folder = os.path.basename(self.im_dir)

        self.get_raw_images_remote_commands = ( f"cd {self.camera_rawimages_dir} && "
                                                f"tar cvf {self.im_folder}.tar {self.im_folder}/ && "
                                                f"tftp -l {self.im_folder}.tar -p {self.tftp_ip} && "
                                                f"rm {self.im_folder}.tar")
        
        self.get_raw_images_local_commands = (  f"cd {self.tftpserver_dir} && "
                                                f"sudo chmod 777 {self.im_folder}.tar && "
                                                f"tar -xvf {self.im_folder}.tar && "
                                                f"sudo chmod 777 -R {self.im_folder} && "
                                                f"mv {self.im_folder} {self.current_dir}/assets/images")
       
        self.get_csv_file_remote_commands = ( f"cd {self.camera_csvfile_dir} && "
                                              f"tftp -l {self.csv_file} -p {self.tftp_ip}")
        
        self.get_csv_file_local_commands = ( f"cd {self.tftpserver_dir} && "
                                             f"mv {self.csv_file} {self.current_dir}/assets/csv_file")
        
    def plot_distance_in_one_csv_file(self):
        plt.figure(figsize=(200, 100))
        frame_ids, distances = self.extract_distance_data(self.csv_file_path)
        plt.plot(frame_ids, distances, label=self.plot_label)
        plt.xlabel('FrameID')
        plt.ylabel('tailingObj.distanceToCamera')
        plt.title('Distance to Camera over Frames')
        plt.legend()
        plt.grid(True)

        plt.show()


    def compare_distance_in_two_csv_file(self):
        return NotImplemented
    
    def compare_distance_in_multiple_csv_file(self):
        i = 0
        plt.figure(figsize=(200, 100))

        for csv_file  in self.csv_file_list:
            frame_ids, distances = self.extract_distance_data(csv_file)
            plt.plot(frame_ids, distances, label=self.list_label[i])
            i += 1

        plt.xlabel('FrameID')
        plt.ylabel('tailingObj.distanceToCamera')
        plt.title('Distance to Camera over Frames')
        plt.legend()
        plt.grid(True)

        plt.show()

    
    def visualize_hisotircal_main(self):
        HAVE_LOCAL_IMAGES = os.path.exists(self.im_dir)
        logging.info(f"HAVE_LOCAL_IMAGES: {HAVE_LOCAL_IMAGES}")
        # If local have no raw images or CSV file, download from camera device using SSH
        if not HAVE_LOCAL_IMAGES:
            tar_path = f'{self.tftpserver_dir}{os.sep}{self.im_folder}.tar'
            
            if not os.path.exists(tar_path):
                logging.info(f"tar file: {self.im_folder}.tar does not exist in tftp folder")
                logging.info("Start to download raw images from the LI80 camera...")
                self.Connect.execute_remote_command_with_progress(self.get_raw_images_remote_commands)  # Execute commands on the camera
            
            logging.info(f"tar file: {self.im_folder}.tar exists in tftp folder, moving to the assets/images/")
            self.Connect.execute_local_command(self.get_raw_images_local_commands) # Execut command on the local computer

        if not os.path.exists(self.csv_file_path):
            logging.info(self.csv_file)
            self.Connect.execute_remote_command_with_progress(self.get_csv_file_remote_commands) # Execute commands on the camera
            self.Connect.execute_local_command(self.get_csv_file_local_commands) # Execut command on the local computer

        # Start to darw AI result after local have raw images and CSV file
        self.draw_AI_result_to_images()

    def draw_AI_result_to_images(self):
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

                            if self.show_airesultimage:
                                # 按下任意鍵則關閉所有視窗
                                if self.resize:
                                    im = cv2.resize(im, (self.resize_w, self.resize_h), interpolation=cv2.INTER_AREA)
                                cv2.imshow("im",im)
                                if self.ADAS_FCW==True or self.ADAS_LDW==True:
                                    cv2.waitKey((self.sleep) * 5)
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
                                    print(f'image exists :{save_im_path}')
                                
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
    

    def draw_bounding_boxes(self,frame_ID, tailing_objs,detect_objs,vanish_objs,ADAS_objs):
        image_path = os.path.join(self.im_dir, f'{self.image_basename}{frame_ID}.png')
        image = cv2.imread(image_path)

        if image is None:
            print(f"Image not found: {image_path}")
            return
        
        cv2.putText(image, 'frame_ID:'+str(frame_ID), (10,10), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
        logging.info("============================")
        logging.info(f"frame_ID:{frame_ID}")
        if tailing_objs and self.show_tailingobjs:
        
            for obj in tailing_objs:
                tailingObj_x1, tailingObj_y1 = obj["tailingObj.x1"], obj["tailingObj.y1"]
                tailingObj_x2, tailingObj_y2 = obj["tailingObj.x2"], obj["tailingObj.y2"]
                distance = obj["tailingObj.distanceToCamera"]
                tailingObj_label = obj["tailingObj.label"]
                distance_to_camera = obj['tailingObj.distanceToCamera']
                tailingObj_id = obj['tailingObj.id']
                tailingObj_label = obj['tailingObj.label']
                # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                logging.info(f"tailingObj_label:{tailingObj_label}")
                logging.info(f"tailingObj_id:{tailingObj_id}")
                logging.info(f"tailingObj_x1:{tailingObj_x1}")
                logging.info(f"tailingObj_y1:{tailingObj_y1}")
                logging.info(f"tailingObj_x2:{tailingObj_x2}")
                logging.info(f"tailingObj_y2:{tailingObj_y2}")

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
                        text_thickness = 0.46
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
                    cv2.rectangle(im, (tailingObj_x1, tailingObj_y1), (tailingObj_x2, tailingObj_y2), color=(0,255,255), thickness=2)
                    cv2.putText(image, f"{label} ({distance:.2f}m)", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                if self.show_tailingobjs:
                    cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, text_thickness, color, 1, cv2.LINE_AA)
                    cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,text_thickness+0.05, color, 1, cv2.LINE_AA)

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
                cv2.waitKey(self.sleep*5)  # Display the image for a short time
            else:
                cv2.waitKey(self.sleep)

    
    
    

    def parse_live_mode_historical_csv_file(self):
    
        # Read the CSV file
        print(self.csv_file)
        df = pd.read_csv(self.csv_file_path)

        # Iterate over each row in the CSV file
        for index, row in df.iterrows():
            try:
                json_data = json.loads(row[0])  # Assuming the JSON is in the first column
                for frame_id, frame_data in json_data["frame_ID"].items():
                    tailing_objs = frame_data.get("tailingObj", [])
                    detect_objs = frame_data.get("detectObj", {}).get("VEHICLE", []) + frame_data.get("detectObj", {}).get("HUMAN", [])
                    vanish_objs = frame_data.get("vanishLineY", [])
                    ADAS_objs = frame_data.get("ADAS",[])
                    if tailing_objs:
                        self.draw_bounding_boxes(frame_id, tailing_objs,detect_objs,vanish_objs,ADAS_objs)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON on row {index}: {e}")
            except KeyError as e:
                print(f"Key error on row {index}: {e}")
            except Exception as e:
                print(f"Unexpected error on row {index}: {e}")


    