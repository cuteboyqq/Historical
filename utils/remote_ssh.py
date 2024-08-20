import sys
import time
import threading
import paramiko

class RemoteSSH:
    def __init__(self, hostname, username, password, port):
        """
        Initializes a RemoteResourceMonitor instance.

        Args:
            hostname: The hostname or IP address of the remote host
            username: The username to use for SSH authentication
            password: The password to use for SSH authentication
            port: The port to use for SSH authentication
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.client = None

    def _progress_indicator(self):
        chars = "|/-\\"
        i = 0
        while self.connecting:
            url = f"\033[1;37;42m{self.hostname}:{self.port}\033[0m"
            user = f"\033[1;37;42m{self.username}\033[0m"
            msg = f"🔌 Connecting to Go-Focus: {url} as {user} ..."
            sys.stdout.write(f'\r{msg} {chars[i % len(chars)]}')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def connect(self):
        """
        Establishes an SSH connection to the remote host using the provided credentials.
        """
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.connecting = True
        indicator_thread = threading.Thread(target=self._progress_indicator)

        try:
            indicator_thread.start()

            self.client.connect(
                self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            name = "Device"
            self.connecting = False
            indicator_thread.join()
            print(f"\n\n✅ {name.capitalize():13} Connection \t \033[32mSuccessful\033[0m")
            return True
        except Exception as e:
            print(f"\n\n❌ {name.capitalize():13} Connection \t \033[31mFailed: {str(e)}\033[0m")
            self.connecting = False
            indicator_thread.join()
            return False

    def disconnect(self):
        """
        Closes the SSH connection if it exists.
        """
        if self.client:
            self.client.close()

    def execute_command(self, command):
        """
        Executes a command on the remote host.

        Args:
            command: The command to execute on the remote host

        Returns:
            The output of the command
        """
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode('utf-8').strip()
        return stdout.read().decode('utf-8').strip()