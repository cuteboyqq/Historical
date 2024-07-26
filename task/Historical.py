import csv
import json
import matplotlib.pyplot as plt
import os
import cv2
from engine.BaseDataset import BaseDataset
from utils.connection import Connection
from config.config import get_connection_args

class Historical(BaseDataset):
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
                            print(f"frame_id:{frame_id}")
                            
                            # Get image path
                            im_file = self.image_basename + frame_id + "." + self.image_format
                            im_path = os.path.join(self.im_dir,im_file)
                            print(im_path)
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
                        print(f"Error decoding JSON: {e}")
                    except Exception as e:
                        print(f"Unexpected error: {e}")
        
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
    

    def visualize_hisotircal_main(self):
        args = get_connection_args()
        Connect = Connection(args)
        HAVE_LOCAL_IMAGES = False
        self.im_folder = os.path.basename(self.im_dir)
        # self.csv_file = os.path.basename(self.csv_file_path)
        #check local images exit or not
        if os.path.exists(self.im_dir):
            HAVE_LOCAL_IMAGES = True
        else:
            HAVE_LOCAL_IMAGES = False

        print(f"HAVE_LOCAL_IMAGES:{HAVE_LOCAL_IMAGES}")
        if not HAVE_LOCAL_IMAGES:

            if os.path.exists(f'/home/ali/Public/tftp/{self.im_folder}.tar'):
                print(f"tar file :{self.im_folder}.tar exists in tftp folder, mv to the assets/images/")
                local_commands = (
                    "cd /home/ali/Public/tftp && "
                    f"sudo chmod 777 {self.im_folder}.tar && "
                    f"tar -xvf {self.im_folder}.tar && "
                    f"sudo chmod 777 -R {self.im_folder} && "
                    f"mv {self.im_folder} /home/ali/Projects/GitHub_Code/ali/Historical/assets/images"
                )
                Connect.execute_local_command(local_commands)
            
            else:
                print(f"tar file :{self.im_folder}.tar does not exists in tftp folder")
                print("Start to download raw images from the LI80 camera....")
                # Combine commands into a single string separated by &&
                remote_commands = (
                    "cd /mnt/mmc/adas/debug/raw_images/ && "
                    f"tar cvf {self.im_folder}.tar {self.im_folder}/ && "
                    f"tftp -l {self.im_folder}.tar -p {self.tftp_ip} && "
                    f"rm {self.im_folder}.tar"
                )

                

                # Execute commands on the camera
                Connect.execute_remote_command_with_progress(remote_commands)

                local_commands = (
                    "cd /home/ali/Public/tftp && "
                    f"sudo chmod 777 {self.im_folder}.tar && "
                    f"tar -xvf {self.im_folder}.tar && "
                    f"sudo chmod 777 -R {self.im_folder} && "
                    f"mv {self.im_folder} /home/ali/Projects/GitHub_Code/ali/Historical/assets/images"
                )

                # Wait for transfer to complete (if needed) and then execute local commands
                Connect.execute_local_command(local_commands)
        else:
            print(f"HAVE_LOCAL_IMAGES:{HAVE_LOCAL_IMAGES}")


        if not os.path.exists(self.csv_file_path):
            print(self.csv_file)
            remote_commands = (
                "cd /logging/video-adas && "
                f"tftp -l {self.csv_file} -p {self.tftp_ip}"
            )
            Connect.execute_remote_command_with_progress(remote_commands)
            local_commands = (
                    "cd /home/ali/Public/tftp && "
                    f"mv {self.csv_file} /home/ali/Projects/GitHub_Code/ali/Historical/assets/csv_file"
            )
            Connect.execute_local_command(local_commands)
        # Transfer and process images
        # transfer_images()
        # Transfer CSV file
        # remote_csv_path = '/logging/video-adas/117_video-adas_2024-07-26.csv'
        # local_csv_path = 'JSON_log.csv'
        # self.csv_file = local_csv_path
        self.draw_AI_result_to_images()



    