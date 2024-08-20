import time
import paramiko
from datetime import datetime


class RemoteResourceMonitor:
    def __init__(self, hostname, username, password, port, interval=5):
        """
        Initializes a RemoteResourceMonitor instance.

        Args:
            hostname: The hostname or IP address of the remote host
            username: The username to use for SSH authentication
            password: The password to use for SSH authentication
            port: The port to use for SSH authentication
            interval: The monitoring interval in seconds (default: 5)
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.interval = interval
        self.client = None
        self.adas_process_name = "cardv"

        # Monitoring results
        self.timestamp = None
        self.cpu_usage = 0
        self.mem_usage = 0
        self.frame_buffer_size = 0
        self.fps = 0

    def connect(self):
        """
        Establishes an SSH connection to the remote host using the provided credentials.
        """

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            print(f"Attempting to connect to {self.hostname}:{self.port} as {self.username}")
            self.client.connect(
                self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            print("Connection successful")
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            raise

    def disconnect(self):
        """
        Closes the SSH connection if it exists.
        """
        if self.client:
            self.client.close()

    def execute_command(self, command):
        """
        Executes a given command on the remote host and returns the output.

        Args:
            command: The command to execute

        Returns:
            The output of the command as a string
        """
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode('utf-8').strip()

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

    #TODO: TBD
    def get_input_buffer_size(self):
        """
        Retrieves the input buffer size (To be implemented).

        Returns:
            A string with the input buffer size
        """
        cmd = "command_to_get_buffer_size"  #TODO: TBD
        result = self.execute_command(cmd)
        return f"Input Buffer Size: {result}"

    #TODO: TBD
    def get_adas_fps(self):
        """
        Retrieves the ADAS FPS (Frames Per Second) (To be implemented).

        Returns:
            A string with the ADAS FPS
        """
        cmd = "command_to_get_adas_fps"  #TODO: TBD
        result = self.execute_command(cmd)
        return f"ADAS FPS: {result}"

    def monitor(self, duration=60):
        """
        Monitors system resources for a specified duration.

        Args:
            duration: The monitoring duration in seconds (default: -1: run indefinitely)
        """
        try:
            self.connect()
            start_time = time.time()
            unlimited = duration == -1

            while unlimited or time.time() - start_time < duration:
                self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # print(f"Timestamp: {timestamp}")

                if self.adas_process_name:
                    pid, mem, cpu = self.get_process_resources(self.adas_process_name)
                    print("[{}]: CPU: {}%, MEM: {}%".format(self.timestamp, cpu, mem))
                    # buffer_size = self.get_input_buffer_size()    #TODO: TBD
                    # adas_fps = self.get_adas_fps()                #TODO: TBD
                    # print(f"Input Buffer Size: {buffer_size}")    #TODO: TBD
                    # print(f"ADAS FPS: {adas_fps}")                #TODO: TBD

                    # Update results
                    self.cpu = cpu
                    self.mem = mem

                time.sleep(self.interval)
        except Exception as e:
            print(f"An error occurred during monitoring: {str(e)}")
        finally:
            self.disconnect()

    def get_results(self):
        """
        Returns the latest monitoring results.

        Returns:
            A dictionary containing the latest monitoring results.
        """
        return {
            "timestamp": self.timestamp,
            "cpu_usage": self.cpu_usage,
            "mem_usage": self.mem_usage,
            "frame_buffer_size": self.frame_buffer_size,
            "fps": self.fps
        }

# Use example
if __name__ == "__main__":
    monitor = RemoteResourceMonitor(
        hostname='192.168.1.1',
        username='root',
        password='ALUDS$#q',
        port=22,
        interval=1
    )
    monitor.monitor(duration=-1)