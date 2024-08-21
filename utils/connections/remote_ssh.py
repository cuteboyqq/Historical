import sys
import time
import threading
import paramiko

class RemoteSSH:
    def __init__(self, hostname, username, password, port):
        """Initializes a RemoteResourceMonitor instance.

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
        """Establishes an SSH connection to the remote host using the provided credentials.
        """
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.connecting = True
        indicator_thread = threading.Thread(target=self._progress_indicator)
        indicator_thread.start()

        name = "Device"
        connection_successful = False
        try:
            self.client.connect(
                self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            connection_successful = True
        except Exception as e:
            error_message = str(e)

        self.connecting = False
        indicator_thread.join()

        if connection_successful:
            print(f"\n✅ {name.capitalize():13} Connection \t \033[32mSuccessful\033[0m")
            return True
        else:
            print(f"\n❌ {name.capitalize():13} Connection \t \033[31mFailed\033[0m")
            return False

    def disconnect(self):
        """Closes the SSH connection if it exists.
        """
        if self.client:
            self.client.close()

    def execute_command(self, command):
        """Executes a command on the remote host.

        Args:
            command: The command to execute on the remote host

        Returns:
            The output of the command
        """
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode('utf-8').strip()

    def execute_command_in_new_session(self, command):
        """Executes a command on the remote host in a new session.

        Args:
            command: The command to execute on the remote host

        Returns:
            The output of the command
        """
        transport = self.client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(command)
        output = channel.recv(1024).decode('utf-8')
        channel.close()
        return output.strip()

    def get_transport(self):
        """Gets the underlying Transport object for this SSH connection.

        Returns:
            paramiko.Transport: The Transport object if the connection is established, None otherwise.
        """
        if self.client and self.client.get_transport() and self.client.get_transport().is_active():
            return self.client.get_transport()
        else:
            return None