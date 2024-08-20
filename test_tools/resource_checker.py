import tqdm
import time
from datetime import datetime


class RemoteResourceChecker:
    def __init__(self, remoteSSH, config):
        """
        Initializes a RemoteResourceMonitor instance.

        Args:
            remoteSSH: RemoteSSH instance
        """
        # RemoteSSH instance
        self.remoteSSH = remoteSSH
        self.adas_process_name = "cardv"

        # Get the real-time detection result
        self.check_duration = config.test_check_duration
        self.check_interval = config.test_check_interval

        # Monitor parameters
        self.cpu_usage_list = []
        self.mem_usage_list = []
        self.cpu_usage = None
        self.mem_usage = None

        # Threshold
        self.cpu_threshold = config.test_cpu_threshold
        self.mem_threshold = config.test_mem_threshold

        # Result
        self.result = False

    def execute_command(self, command):
        """
        Executes a command on the remote host.
        """
        return self.remoteSSH.execute_command(command)

    def get_disk_usage(self):
        """
        Retrieves the current disk usage percentage for the root partition.

        Returns:
            Disk usage as a string percentage
        """
        return self.execute_command("df -h / | awk 'NR==2 {print $5}'")

    def get_process_resources(self, process_name):
        try:
            cmd = f"top -bn1 | grep {process_name} | grep -v grep | grep -v logger | awk '{{print $1, $6, $7, $8}}'"
            result = self.execute_command(cmd)
            if not result:
                return f"Process {process_name} not found"

            parts = result.split()
            if len(parts) >= 4:
                pid = parts[0]
                mem = parts[1]
                cpu = parts[3]
                return [pid, mem, cpu]

        except Exception as e:
            return f"Error getting process resources: {str(e)}"

    def _get_cpu_usage(self):
        average_cpu = sum(self.cpu_usage_list) / len(self.cpu_usage_list)
        return average_cpu

    def _get_mem_usage(self):
        average_mem = sum(self.mem_usage_list) / len(self.mem_usage_list)
        return average_mem

    def _monitor_resources(self):
        start_time = time.time()
        iterations = 0
        total_iterations = int(self.check_duration / self.check_interval)
        
        with tqdm.tqdm(total=total_iterations, desc="Monitoring ADAS resources", unit="check") as pbar:
            while iterations < total_iterations:
                pid, mem, cpu = self.get_process_resources(self.adas_process_name)

                # Update results
                self.cpu_usage_list.append(float(cpu))
                self.mem_usage_list.append(float(mem))

                time.sleep(self.check_interval)
                iterations += 1
                pbar.update(1)

    def check_resource(self):
        """
        Monitors system resources for a specified duration.
        """
        is_resource_ok = True

        # Get the real-time detection result
        self._monitor_resources()

        # Get the average CPU and MEM usage
        self.cpu_usage = self._get_cpu_usage()
        if self.cpu_usage > self.cpu_threshold:
            print(f"❌ Average CPU usage: {self.cpu_usage}% exceeds threshold: {self.cpu_threshold}%")
            is_resource_ok = False

        self.mem_usage = self._get_mem_usage()
        if self.mem_usage > self.mem_threshold:
            print(f"❌ Average Memory usage: {self.mem_usage}% exceeds threshold: {self.mem_threshold}%")
            is_resource_ok = False

        self.result = is_resource_ok
        return is_resource_ok

    def get_results(self):
        """
        Returns the results of the resource check.
        """
        res = " ✅ Passed" if self.result else " ❌ Failed"
        return {
            "Average CPU usage": f"{self.cpu_usage:.2f}" + "%" + res,
            "Average Memory usage": f"{self.mem_usage:.2f}" + "%" + res,
            # "overall": "✅ Passed" if self.result else "❌ Failed"
        }

