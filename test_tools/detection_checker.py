import re
import time
import tqdm
from datetime import datetime
from utils.adas_log_parser import AdasLogParser

class DetectionChecker:
    def __init__(self, remote_host, config):

        # Connect to the remote host
        self.remote_host = remote_host

        # ADAS log parser
        self.adas_log_parser = AdasLogParser()

        # Get the real-time detection result
        self.check_duration = config.test_check_duration
        self.check_interval = config.test_check_interval
        self.curr_frame_id  = None
        self.prev_frame_id  = None

        # Get the latest log file path
        self.remote_log_path = self._get_remmote_latest_log_path()

        # Get the detection result
        self.detection_result_dict_list = []
        self.result = False

    def _get_latest_csv_file(self, log_file_list):
        parsed_files = []

        for log_file in log_file_list:
            match = re.match(r'(\d+)_video-adas_(\d{4}-\d{2}-\d{2})(\.(\d+))?\.csv', log_file)
            if match:
                token, date, _, subversion = match.groups()
                token = int(token)
                date = datetime.strptime(date, '%Y-%m-%d')
                subversion = int(subversion) if subversion else 0
                parsed_files.append((token, date, subversion, log_file))

        if not parsed_files:
            print("No valid ADAS detection log found! (1)")
            return False

        parsed_files.sort(key=lambda x: (-x[0], x[1], -x[2]), reverse=True)

        latest_token, latest_date, latest_subversion, latest_file = parsed_files[0]

        if latest_date.year == 1970:
            for token, date, subversion, log_file, in parsed_files:
                if token == latest_token and date == latest_date and subversion == 0:
                    return log_file
            else:
                print("No valid ADAS detection log found! (2)")
                return False
        else:
            for token, date, subversion, log_file in parsed_files:
                if token == latest_token and date == latest_date and subversion == 0:
                    return log_file
            else:
                print("No valid ADAS detection log found! (3)")
                return False

    def _get_remmote_latest_log_path(self):
        """Get the latest log file path from the remote host

        Returns:
            str: The latest log file path
        """
        command = f"ls /logging/video-adas/"
        log_files_str = self.remote_host.execute_command(command)
        log_files = []
        for line in log_files_str.split("\n"):
            log_files.append(line)
        latest_log_file = self._get_latest_csv_file(log_files)
        # print(f">>> latest_log_file = {latest_log_file}")
        log_file_path = f"/logging/video-adas/{latest_log_file}"
        return log_file_path

    def _get_latest_completed_json_log(self, log_file_path):
        command = f"tail -n 10 {log_file_path}"
        recv_log_str = self.remote_host.execute_command(command)
        json_log_str = None
        for line in recv_log_str.split("\n"):
            if "[JSON] [debug] json:" in line:
                json_log_str = line
        return json_log_str

    def _get_detection_result(self):

        json_log_str = self._get_latest_completed_json_log(self.remote_log_path)
        self.adas_log_parser.parse(json_log_str)
        self.curr_frame_id = self.adas_log_parser.get_frame_id()

        detection_result_dict = {
            "timestamp ": self.adas_log_parser.get_timestamp(),
            "frame_id": self.adas_log_parser.get_frame_id(),
            "vanishing_y": self.adas_log_parser.get_vanishing_line_y(),
            "vehicle_list": self.adas_log_parser.get_detect_vehicle_list(),
            "tailing_obj": self.adas_log_parser.get_tailing_obj(),
            "fcw_event": self.adas_log_parser.get_fcw_event(),
            "ldw_event": self.adas_log_parser.get_ldw_event()
        }
        # print('e')

        if (self.curr_frame_id is not None) and (self.curr_frame_id is None):
            self.prev_frame_id = self.curr_frame_id
            return True, detection_result_dict
        elif (self.curr_frame_id is not None) and \
            (self.prev_frame_id is not None) and \
            (self.curr_frame_id == self.prev_frame_id):
            return False, None
        elif (self.curr_frame_id is not None):
            self.prev_frame_id = self.curr_frame_id
            return True, detection_result_dict
        else:
            return False, detection_result_dict

    def _monitor_detection_result(self):
        iterations = 0
        total_iterations = int(self.check_duration / self.check_interval)
        start_time = time.time()
        with tqdm.tqdm(total=total_iterations, desc="Monitoring ADAS detection", unit="check") as pbar:
            while iterations < total_iterations:
                is_new_result, detection_result_dict = self._get_detection_result()
                if is_new_result:
                    self.detection_result_dict_list.append(detection_result_dict)
                time.sleep(self.check_interval)
                iterations += 1
                pbar.update(1)

    def _is_detection_result_changed(self):
        if len(self.detection_result_dict_list) < 2:
            return True

        # Get the last two detection result
        last_result = self.detection_result_dict_list[-1]
        prev_result = self.detection_result_dict_list[-2]

        # Compare the vehicle list
        last_vehicles = last_result.get('vehicle_list', [])
        prev_vehicles = prev_result.get('vehicle_list', [])

        # If the vehicle list length is different, we think the result has changed
        if len(last_vehicles) != len(prev_vehicles):
            return True

        # Compare the vehicle list
        for last_vehicle, prev_vehicle in zip(last_vehicles, prev_vehicles):
            if self._is_same_vehicles(last_vehicle, prev_vehicle):
                return False

        return True

    def _is_same_vehicles(self, vehicle1, vehicle2):
        # Compare the two vehicle objects
        if vehicle1.bbox.x1 != vehicle2.bbox.x1:
            # print(f"Vehicle box.x1 is different")
            return False
        elif vehicle1.bbox.x2 != vehicle2.bbox.x2:
            # print(f"Vehicle box.x2 is different")
            return False
        elif vehicle1.bbox.y1 != vehicle2.bbox.y1:
            # print(f"Vehicle box.y1 is different")
            return False
        elif vehicle1.bbox.y2 != vehicle2.bbox.y2:
            # print(f"Vehicle box.y2 is different")
            return False
        elif vehicle1.bbox.confidence != vehicle2.bbox.confidence:
            # print(f"Vehicle confidence is different")
            return False

        return True

    def check_detection(self):

        is_detection_ok = True

        # Monitor the detection result
        self._monitor_detection_result()

        # Check if the detection result has changed
        if not self._is_detection_result_changed():
            is_detection_ok = False
            print(f"❌ Detection result has not changed")
            self.result = False
        else:
            self.result = True
        return is_detection_ok

    def get_results(self):
        result = {
            "Detection Functionality": "✅ Passed" if self.result else "❌ Failed",
            # "overall": "✅ Passed" if self.result else "❌ Failed"
        }
        return result

