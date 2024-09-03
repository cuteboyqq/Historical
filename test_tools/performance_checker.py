import re
import time
import tqdm
from datetime import datetime
from utils.adas_log_parser import AdasLogParser

class PerformanceChecker:
    def __init__(self, remoteSSH, config):
        """Initialize the performance checker
        Args:
            remoteSSH (RemoteSSH): The remote SSH object
            config (Config): The configuration object
        """
        # Connect to the remote host
        self.remoteSSH = remoteSSH

        # ADAS log parser
        self.adas_log_parser = AdasLogParser()

        # Get the real-time detection result
        self.check_duration = config.test_check_duration
        self.check_interval = config.test_check_interval
        self.curr_frame_id  = None
        self.prev_frame_id  = None

        # Get the latest log file path
        self.remote_log_path = self._get_remmote_latest_log_path()

        # Get the performance result
        self.inference_time = 0
        self.performance_result_dict_list = []
        self.buffer_size_distribution_ratio_dict = {}
        self.buffer_size_distribution_dict = {}

        # Threshold for buffer size and inference time
        self.threshold_buffer_ratio = config.test_threshold_buffer_size_ratio
        self.threshold_inference_time = config.test_threshold_inference_time

        # Result
        self.result = False

    def _get_latest_csv_file(self, log_file_list):
        """Get the latest CSV file from the remote host

        Args:
            log_file_list (list): The list of log file names

        Returns:
            str: The latest log file name
        """
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

        parsed_files.sort(key=lambda x: (x[0], x[1], -x[2]), reverse=True)

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
        log_files_str = self.remoteSSH.execute_command(command)
        log_files = []

        for line in log_files_str.split("\n"):
            log_files.append(line)

        latest_log_file = self._get_latest_csv_file(log_files)
        log_file_path = f"/logging/video-adas/{latest_log_file}"
        return log_file_path

    def _get_latest_completed_json_log(self, log_file_path):
        """Get the latest completed JSON log file path

        Args:
            log_file_path (str): The log file path

        Returns:
            str: The latest completed JSON log string
        """
        command = f"tail -n 10 {log_file_path}"
        recv_log_str = self.remoteSSH.execute_command(command)
        json_log_str = None
        for line in recv_log_str.split("\n"):
            if "[JSON] [debug] json:" in line:
                json_log_str = line
        return json_log_str

    def _get_performance_result(self):
        """Get the performance result

        Returns:
            bool: True if the performance result is new, False otherwise
            dict: The performance result
        """
        json_log_str = self._get_latest_completed_json_log(self.remote_log_path)
        self.adas_log_parser.parse(json_log_str)
        self.curr_frame_id = self.adas_log_parser.get_frame_id()

        result_dict = {
            "timestamp ": self.adas_log_parser.get_timestamp(),
            "frame_id": self.adas_log_parser.get_frame_id(),
            "inference_time": self.adas_log_parser.get_inference_time(),
            "buffer_size": self.adas_log_parser.get_buffer_size()
        }

        # if result_dict["inference_time"] is None:
        #     raise ValueError("Inference time is None")

        # if result_dict["buffer_size"] is None:
        #     raise ValueError("Buffer size is None")

        if (self.curr_frame_id is not None) and (self.curr_frame_id is None):
            self.prev_frame_id = self.curr_frame_id
            return True, result_dict
        elif (self.curr_frame_id is not None) and \
            (self.prev_frame_id is not None) and \
            (self.curr_frame_id == self.prev_frame_id):
            return False, None
        elif (self.curr_frame_id is not None):
            self.prev_frame_id = self.curr_frame_id
            return True, result_dict
        else:
            return False, result_dict

    def _monitor_performance_result(self):
        """Monitor the performance result
        """
        iterations = 0
        total_iterations = int(self.check_duration / self.check_interval)
        start_time = time.time()
        with tqdm.tqdm(total=total_iterations, desc="Monitoring ADAS performance", unit="check") as pbar:
            while iterations < total_iterations:
                is_new_result, result_dict = self._get_performance_result()
                if is_new_result:
                    self.performance_result_dict_list.append(result_dict)
                time.sleep(self.check_interval)
                iterations += 1
                pbar.update(1)

    def _get_average_inference_time(self):
        """Get the average inference time

        Returns:
            float: The average inference time
        """
        print(f"self.performance_result_dict_list = {self.performance_result_dict_list}")
        total_inference_time = sum([result_dict["inference_time"] for result_dict in self.performance_result_dict_list])
        return total_inference_time / len(self.performance_result_dict_list)

    def _get_buffer_size_distribution(self):
        """Get the buffer size distribution

        Returns:
            dict: The buffer size distribution (in ratio)
        """
        for result_dict in self.performance_result_dict_list:
            buffer_size = result_dict["buffer_size"]
            if buffer_size not in self.buffer_size_distribution_dict:
                self.buffer_size_distribution_dict[buffer_size] = 0
            self.buffer_size_distribution_dict[buffer_size] += 1

        for buffer_size, count in self.buffer_size_distribution_dict.items():
            self.buffer_size_distribution_ratio_dict[buffer_size] = count / len(self.performance_result_dict_list)

    def check_performance(self):
        """Check the performance

        Returns:
            bool: True if the performance is OK, False otherwise
        """
        is_performance_ok = True
        # Step1. Get the performance result
        self._monitor_performance_result()

        # Step2. Get the average inference time
        self.inference_time = self._get_average_inference_time()
        if self.inference_time > self.threshold_inference_time:
            print(f"❌ Average inference time = {self.inference_time} (threshold = {self.threshold_inference_time})")
            is_performance_ok = False

        # Step3. Get the buffer size distribution
        self._get_buffer_size_distribution()
        buffer_size_ratio_0 = self.buffer_size_distribution_ratio_dict.get(0, 0)
        buffer_size_ratio_1 = self.buffer_size_distribution_ratio_dict.get(1, 0)
        if 1 - (buffer_size_ratio_0 + buffer_size_ratio_1) > self.threshold_buffer_ratio:
            print(f"❌ Buffer size (0, 1) ratio = {buffer_size_ratio_0 + buffer_size_ratio_1} (threshold = {self.threshold_buffer_ratio})")
            is_performance_ok = False
        self.result = is_performance_ok
        return is_performance_ok

    def get_buffer_size_profile(self):
        """Get the buffer size profile

        Returns:
            str: The buffer size profile
        """
        profile_lines = []
        profile_lines.append('')
        for buffer_size, count in self.buffer_size_distribution_dict.items():
            ratio = self.buffer_size_distribution_ratio_dict.get(buffer_size, 0)
            percentage = ratio * 100
            profile_lines.append(f"\t- Buffer Size = {buffer_size} (ratio = {percentage:.0f}%)")

        return "\n".join(profile_lines)

    def get_results(self):
        """Get the performance results

        Returns:
            dict: The performance results
        """
        res = " ✅ Passed" if self.result else " ❌ Failed"
        results = {
            "Average Inference time": f"{self.inference_time*1000:.2f} ms" + res,
            "Buffer Size Profile":      self.get_buffer_size_profile()
        }
        return results






