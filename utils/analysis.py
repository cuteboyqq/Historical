import os
import json
import csv
import glob
import logging
import sys
from utils.connection import Connection
from tqdm import tqdm
from utils.plotter import Plotter
from engine.BaseDataset import BaseDataset
import time
from config.args import Args
# from task.Historical import Historical
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')


class Analysis(BaseDataset):
    def __init__(self,args):
        super().__init__(args)

        self.pred_dist = None
        self.static_GT_dist_list = None
        self.pred_dist_list = None
        self.frame_ids_list = None

        self.Plot = Plotter(args)
        self.Plot.json_log_path = args.analysis_json_log_path

        self.analysis_jsonlog_dir = args.analysis_jsonlog_dir

        self.static_10m_list = None
        self.static_20m_list = None
        self.static_30m_list = None
        self.static_40m_list = None
        self.static_50m_list = None
        self.static_60m_list = None

        # Initialize dictionaries to store results
        self.avg_dist_dict = {}
        self.avg_error_dist_dict = {}
        self.static_performance_dict = {}
        self.GT_label_list = []
        self.scenary_label_list = ["0","1","2"]

        self.set_frameids_distance_list()
        # self.set_static_GT_dist_list(GT_dist_value=30)
        self.display_parameters()

        


    def display_parameters(self):
        """
        Displays the initialized parameters of the Analysis class with emojis, along with class information.
        """
        logging.info("🎯 Analysis Class Information 🎯")
        logging.info(f"📦 Class Name: {self.__class__.__name__}")
        logging.info(f"📝 Documentation: {self.__class__.__doc__}")
        logging.info(f"🔧 Module: {self.__module__}")
        logging.info(f"💡 Base Class: {self.__class__.__bases__}")

        logging.info("🎯 Analysis Class Parameters 🎯")
        logging.info(f"📏 Predicted Distance: {self.pred_dist}")
        logging.info(f"📏 Static Ground Truth Distance List: {self.static_GT_dist_list}")
        logging.info(f"📋 Predicted Distance List: {self.pred_dist_list}")
        logging.info(f"🗂️ Frame IDs List: {self.frame_ids_list}")
        logging.info(f"📂 Plot JSON Log Path: {self.Plot.json_log_path}")


    def calc_all_static_performance(self):
        """
        Processes all static scenarios, calculates distances, errors, and performance.
        """
        # Initialize dictionaries if not already done
        if not hasattr(self, 'avg_dist_dict'):
            self.avg_dist_dict = {}
        if not hasattr(self, 'avg_error_dist_dict'):
            self.avg_error_dist_dict = {}
        if not hasattr(self, 'static_performance_dict'):
            self.static_performance_dict = {}
        
        json_log_path_list = sorted(glob.glob(os.path.join(self.analysis_jsonlog_dir, "***", "**", "*.txt")))
        
        if not json_log_path_list:
            logging.error("🚫 No JSON log files found in the specified directory.")
            return
        
        self.GT_label_list = []  # Initialize GT_label_list if not done elsewhere
        
        for json_log_path in json_log_path_list:
            logging.info(f"📝 Processing JSON log path: {json_log_path}")
            
            # Extract the data type and ground truth distance from the file name
            data_type = ((json_log_path.split("/")[-1]).split(".")[0]).split("_")[0]
            
            if data_type == "Static":
                GT_dist = ((json_log_path.split("/")[-1]).split(".")[0]).split("_")[2].split("m")[0]
                # GT_dist = int(GT_dist)  # Ensure GT_dist is an integer
                self.GT_label_list.append(GT_dist)
                if GT_dist not in self.avg_dist_dict:
                    self.avg_dist_dict[GT_dist] = {}
                if GT_dist not in self.avg_error_dist_dict:
                    self.avg_error_dist_dict[GT_dist] = {}
                if GT_dist not in self.static_performance_dict:
                    self.static_performance_dict[GT_dist] = {}
                logging.info(f"-------------------------------------------------------------------------------")
                logging.info(f"📏 Ground Truth Distance: {GT_dist}")
            else:
                logging.error(f"❌ Incorrect data type: {data_type}. Expected 'Static'. Skipping this file.")
                continue
            
            scenary = ((json_log_path.split("/")[-1]).split(".")[0]).split("_")[-1]
            
            self.Plot.json_log_path = json_log_path
            self.set_frameids_distance_list()
            self.set_static_GT_dist_list(GT_dist_value=int(GT_dist))
            
            logging.info(f"🏞️ Static Scenario: {scenary}")
            
            avg_dist = self.calc_avg_dist()
            self.avg_dist_dict[GT_dist][scenary] = avg_dist
            # logging.info(f"📊 Average Distance: {avg_dist:.2f} meters")
            
            avg_error_dist = self.calc_avg_error_dist()
            self.avg_error_dist_dict[GT_dist][scenary] = avg_error_dist
            # logging.info(f"⚖️ Average Error Distance: {avg_error_dist:.2f} meters")
            
            static_performance = self.calc_static_performance()
            self.static_performance_dict[GT_dist][scenary] = static_performance
            # logging.info(f"🚀 Static Performance: {static_performance:.2f}%")
            
            logging.info(f"✅ Finished processing {json_log_path}")



        self.GT_label_list = sorted(set(self.GT_label_list))
        # self.GT_label_list = unique_sorted_list

        logging.info("📊 All Static Scenarios - Summary:")

        for GT_label in self.GT_label_list:
            headers = ["scenary " + str(scenary) for scenary in self.scenary_label_list]
            
            avg_dist_row = [self.avg_dist_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
            avg_error_dist_row = [self.avg_error_dist_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
            static_performance_row = [self.static_performance_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
            
            logging.info(f"---------------------------------------------------------------------------------------")
            logging.info(f"   📏 Static GT_label: {GT_label}m")
            logging.info( "                          " + "    ".join(f"{header:<10}" for header in headers))
            logging.info(f"   📊 Predict Distance:   " + "    ".join(f"{round(value,4):<10}" for value in avg_dist_row))
            logging.info(f"   ⚖️ Avg Error Distance:  " + "    ".join(f"{round(value,4):<10}" for value in avg_error_dist_row))
            logging.info(f"   🚀 Static Performance: " + "    ".join(f"{round(value,4):<10}" for value in static_performance_row))

        # Call the function with the desired file path
        self.save_summary_to_txt('static_performance_report.txt')


    
    def save_summary_to_txt(self, file_path):
        """
        Saves the static scenarios summary to a text file.
        """
        with open(file_path, 'w') as file:
            file.write("📊 All Static Scenarios - Summary:\n")
            
            for GT_label in self.GT_label_list:
                headers = ["scenary " + str(scenary) for scenary in self.scenary_label_list]
                
                avg_dist_row = [self.avg_dist_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
                avg_error_dist_row = [self.avg_error_dist_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
                static_performance_row = [self.static_performance_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
                
                file.write(f"---------------------------------------------------------------------------------------\n")
                file.write(f"   📏 Static GT_label: {GT_label}m\n")
                file.write("                          " + "    ".join(f"{header:<10}" for header in headers) + "\n")
                file.write(f"   📊 Predict Distance:   " + "    ".join(f"{round(value,4) if value != 'N/A' else 'N/A':<10}" for value in avg_dist_row) + "\n")
                file.write(f"   ⚖️ Avg Error Distance:  " + "    ".join(f"{round(value,4) if value != 'N/A' else 'N/A':<10}" for value in avg_error_dist_row) + "\n")
                file.write(f"   🚀 Static Performance: " + "    ".join(f"{round(value,4) if value != 'N/A' else 'N/A':<10}" for value in static_performance_row) + "\n")

    
    def save_summary_to_csv(self, file_path):
        """
        Saves the static scenarios summary to a CSV file.
        """
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            
            # Write header
            headers = ["GT_label"] + [f"scenary {scenary}" for scenary in self.scenary_label_list]
            writer.writerow(headers)
            
            for GT_label in self.GT_label_list:
                avg_dist_row = [self.avg_dist_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
                avg_error_dist_row = [self.avg_error_dist_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
                static_performance_row = [self.static_performance_dict.get(GT_label, {}).get(scenary, 'N/A') for scenary in self.scenary_label_list]
                
                writer.writerow([f"{GT_label}m"] + avg_dist_row)
                writer.writerow(["📊 Avg Distance:"] + avg_dist_row)
                writer.writerow(["⚖️ Avg Error Distance:"] + avg_error_dist_row)
                writer.writerow(["🚀 Static Performance:"] + static_performance_row)
                writer.writerow([])  # Empty row for separation


    def set_static_GT_dist_list(self,GT_dist_value=None):
        if GT_dist_value is not None:
            self.static_GT_dist_list = [GT_dist_value] * len(self.pred_dist_list)
        else:
            logging.error("❌ Gorund truth distance value is None.")


    def set_frameids_distance_list(self):
        frame_ids_list,distances_list = self.Plot.plot_distance_value_on_each_frame_ID_txt(show_plot=False)
        self.pred_dist_list = distances_list
        self.frame_ids_list = frame_ids_list
        # print(f"self.pred_dist_list={self.pred_dist_list}")
        # print(f"self.frame_ids_list={self.frame_ids_list}")


    def calc_avg_dist(self):
        """
        Calculates the average predicted distance.

        Returns:
            float: The average predicted distance.
        """
        if not self.pred_dist_list or len(self.pred_dist_list) == 0:
            logging.warning("🚨 Predicted distance list is empty. Cannot calculate average distance.")
            return None

        total_dist = sum(self.pred_dist_list)
        avg_dist = total_dist / len(self.pred_dist_list)
        
        logging.info(f"📏 Calculated average predicted distance: {avg_dist:.6f}")
        return avg_dist
    

    def calc_avg_error_dist(self):
        """
        Calculates the average error between predicted and ground truth distances.

        Returns:
            float: The average error distance.
        """
        if not self.pred_dist_list or not self.static_GT_dist_list:
            logging.warning("🚨 Predicted or ground truth distance list is empty. Cannot calculate average error distance.")
            return None

        total_error = 0
        for pred_dist, gt_dist in zip(self.pred_dist_list, self.static_GT_dist_list):
            total_error += abs(pred_dist - gt_dist)
        
        avg_error = total_error / len(self.pred_dist_list)
        
        logging.info(f"📉 Calculated average error distance: {avg_error:.6f}")
        return avg_error

    
    def calc_static_performance(self):
        """
        Calculates the static performance metric.

        Returns:
            float: A performance score (for example, accuracy or some other metric).
        """
        # Example metric: Mean Absolute Percentage Error (MAPE)
        if not self.pred_dist_list or not self.static_GT_dist_list:
            logging.warning("⚠️ Predicted or ground truth distance list is empty. Cannot calculate static performance.")
            return None

        total_percentage_error = 0
        for pred_dist, gt_dist in zip(self.pred_dist_list, self.static_GT_dist_list):
            if gt_dist != 0:  # Avoid division by zero
                total_percentage_error += abs(pred_dist - gt_dist) / gt_dist

        mape = 100.0 - ((total_percentage_error / len(self.pred_dist_list)) * 100)
        
        logging.info(f"📊 Calculated static performance (MAPE): {mape:.6f}%")
        return mape
    

# if __name__=="__main__":
#     import yaml
#     # Load the YAML configuration file and return its content as a dictionary
#     def load_config(config_file):
#         with open(config_file, 'r') as file:
#             config = yaml.safe_load(file)
#         return config

#     # Load configuration settings from the specified YAML file
#     config = load_config('config/config.yaml')
    
#     # Initialize Args object with the loaded configuration
#     args = Args(config)
#     an = Analysis(args)

#     # Initialize Args object with the loaded configuration
#     # Calculate and log average distance
#     avg_dist = an.calc_avg_dist()
#     logging.info(f"📏 Average Distance: {avg_dist}")

#     # Calculate and log average error distance
#     avg_err = an.calc_avg_error_dist()
#     logging.info(f"📉 Average Error Distance: {avg_err}")
    
#     # Calculate and log static performance
#     avg_performance = an.calc_static_performance()
#     logging.info(f"🏁 Static Performance: {avg_performance}")