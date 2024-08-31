import paramiko
from scp import SCPClient
from tqdm import tqdm
import os

class RemoteUploader:
    def __init__(self, args):
        self.host = args.camera_host_name
        self.port = args.camera_port
        self.username = args.camera_user_name
        self.password = args.camera_password

    def create_ssh_client(self):
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, port=self.port, username=self.username, password=self.password)
        return ssh

    def upload_file_with_progress(self, local_path, remote_path):
        # Get the file size
        file_size = os.path.getsize(local_path)
        
        # Create SSH client
        ssh = self.create_ssh_client()

        # Create a tqdm progress bar with a specific width (e.g., 30 columns)
        with tqdm(total=file_size, desc="Uploading", unit='B', unit_scale=True, ncols=80) as pbar:
            # Define a progress callback function
            def progress_callback(filename, size, sent):
                pbar.update(sent - pbar.n)

            # Use SCPClient to transfer the file
            with SCPClient(ssh.get_transport(), progress=progress_callback) as scp:
                scp.put(local_path, remote_path)

        # Close SSH connection
        ssh.close()

    def progress_callback(self, filename, size, sent):
        # Calculate and display progress
        progress = sent / size * 100
        print(f"Transfer progress for {filename}: {progress:.2f}%")

# if __name__ == "__main__":
#     # Remote device details
#     host = "192.168.1.10"
#     port = 22
#     username = "your_username"
#     password = "your_password"

#     # Local and remote file paths
#     local_tar_file = "your_file.tar"
#     remote_tar_file = "/remote/path/your_file.tar"

#     # Create an uploader object and upload the file with progress
#     uploader = RemoteUploader(host, port, username, password)
#     uploader.upload_file_with_progress(local_tar_file, remote_tar_file)
