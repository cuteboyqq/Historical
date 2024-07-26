from config.config import get_connection_args
from tqdm import tqdm
import paramiko
import time
import subprocess
from scp import SCPClient
import os
import re
import json
import cv2
import pandas as pd


class Connection():

    def __init__(self,args):
        self.hostname = args.host_name
        self.port = args.port
        self.username = args.user_name
        self.password = args.password
        self.remote_path = args.remote_path
        self.local_path = args.local_path

    # Function to transfer file using SCP
    def transfer_file(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print(f"Connecting to {self.hostname}...")
            ssh.connect(self.hostname, self.port, self.username, self.password)
            print("Connected!")

            with SCPClient(ssh.get_transport()) as scp:
                scp.get(self.remote_path, self.local_path)

            ssh.close()
            print(f"File transferred successfully to {self.local_path}")
        except paramiko.ssh_exception.AuthenticationException as auth_err:
            print(f"Authentication failed: {auth_err}")
        except paramiko.ssh_exception.SSHException as ssh_err:
            print(f"SSH error: {ssh_err}")
        except Exception as e:
            print(f"An error occurred: {e}")


    def execute_remote_command_with_progress(self,command):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.hostname, self.port, self.username, self.password)
            print(f"Connected to {self.hostname}")

            # Execute the command
            stdin, stdout, stderr = ssh.exec_command(command)

            # Initialize progress bar
            with tqdm(total=100, desc="Processing", unit="%", dynamic_ncols=True) as pbar:
                while not stdout.channel.exit_status_ready():
                    line = stdout.readline().strip()
                    if line:
                        # Update progress bar description or postfix with current status
                        pbar.set_description(f"Progress: {line}")
                        # Simulate progress increment; adjust this based on your actual progress
                        pbar.update(1)
                    time.sleep(1)  # Adjust the sleep interval as needed

                # Print final output
                final_output = stdout.read().strip()
                final_errors = stderr.read().strip()
                print("Final Output:")
                print(final_output)
                print("Final Errors:")
                print(final_errors)

            ssh.close()
        except paramiko.ssh_exception.AuthenticationException as auth_err:
            print(f"Authentication failed: {auth_err}")
        except paramiko.ssh_exception.SSHException as ssh_err:
            print(f"SSH error: {ssh_err}")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    # Execute local commands
    # Function to execute a command locally
    def execute_local_command(self,command):
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Command executed: {command}")
            print("Output:")
            print(result.stdout.decode())
            print("Errors:")
            print(result.stderr.decode())
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
            print("Output:")
            print(e.stdout.decode())
            print("Errors:")
            print(e.stderr.decode())

    

if __name__ == "__main__":
    args = get_connection_args()
    Con = Connection(args)
    HAVE_LOCAL_IMAGES = False
    #check local images exit or not
    if os.path.exists('/home/ali/Projects/GitHub_Code/ali/Historical/assets/images/2024-7-26-16-28'):
        HAVE_LOCAL_IMAGES = True
    else:
        HAVE_LOCAL_IMAGES = False

    print(f"HAVE_LOCAL_IMAGES:{HAVE_LOCAL_IMAGES}")
    if not HAVE_LOCAL_IMAGES:

        if os.path.exists('/home/ali/Public/tftp/2024-7-26-16-28.tar'):
            print("tar file :2024-7-26-16-28.tar exists in tftp folder, mv to the assets/images/")
            local_commands = (
            "cd /home/ali/Public/tftp && "
            "sudo chmod 777 2024-7-26-16-28.tar && "
            "tar -xvf 2024-7-26-16-28.tar && "
            "chmod 777 -R 2024-7-26-16-28 && "
            "mv 2024-7-26-16-28 /home/ali/Projects/GitHub_Code/ali/Historical/assets/images"
            )
            Con.execute_local_command(local_commands)
        
        else:
            print("tar file :2024-7-26-16-28.tar does not exists in tftp folder")
            print("Start to download raw images from the LI80 camera....")
            # Combine commands into a single string separated by &&
            remote_commands = (
                "cd /mnt/mmc/adas/debug/raw_images/ && "
                "tar cvf 2024-7-26-16-28.tar 2024-7-26-16-28/ && "
                "tftp -l 2024-7-26-16-28.tar -p 192.168.1.10 && "
                "rm 2024-7-26-16-28.tar"
            )

            

            # Execute commands on the camera
            Con.execute_remote_command_with_progress(remote_commands)

            local_commands = (
                "cd /home/ali/Public/tftp && "
                "sudo chmod 777 2024-7-26-16-28.tar && "
                "tar -xvf 2024-7-26-16-28.tar && "
                "chmod 777 -R 2024-7-26-16-28 && "
                "mv 2024-7-26-16-28 /home/ali/Projects/GitHub_Code/ali/Historical/assets/images"
            )

            # Wait for transfer to complete (if needed) and then execute local commands
            Con.execute_local_command(local_commands)
    else:
        print(f"HAVE_LOCAL_IMAGES:{HAVE_LOCAL_IMAGES}")

    # Transfer and process images
    # transfer_images()
    # Transfer CSV file
    Con.transfer_file()

    # while True:
    #     # # Parse CSV and draw bounding boxes
    #     parse_and_draw()
    #     time.sleep(60)  # Adjust the interval as needed
    # parse_and_draw()