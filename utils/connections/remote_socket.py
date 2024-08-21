import sys
import time
import socket
import struct
import logging
import queue
import signal
import threading

class RemoteSocket:
    def __init__(self, server_ip, server_port, recv_data_keys):
        """Initialize the RemoteSocket instance.

        Args:
            server_ip (str): The IP address of the server.
            server_port (int): The port number for the server.
            recv_data_keys (list): The keys of the data to receive.
        """
        # Socket server configuration
        self.server = None          # Server socket object
        self.server_ip = server_ip  # IP address of the server

        # Socket client configuration
        self.client = None        # Client socket object
        self.client_ip = None     # IP address of the connected client

        # Server port
        self.port = server_port   # Port number for the server

        # Server status
        self.running = False       # Flag to indicate if the server is running

        # Data management
        self.data_queue = queue.Queue()  # Queue to store received data
        self.recv_data_keys = recv_data_keys

        # Threading
        self.thread = None        # Thread for data collection
        self.stop_thread = False

        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)  # Register SIGINT handler

    def start_server(self):
        """Start the server and begin listening for connections.
        Initializes the socket, binds it to the specified IP and port,
        and starts the data receiving thread.

        Returns:
            bool: True if the server started successfully, False otherwise.
        """
        name = "Host"
        connection_successful = False

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self.server.bind((self.server_ip, self.port))
            self.server.listen(5)

            self.thread = threading.Thread(
                target=self._recv_data_loop, daemon=True
            )
            self.thread.start()
            connection_successful = True

        except Exception as e:
            error_message = str(e)

        if connection_successful:
            print(f"✅ {name.capitalize():13} Build Socket Server \t \033[32mSuccessful\033[0m")
            print(f"🔌 Socket server started on {self.server_ip}:{self.port}")
            return True
        else:
            print(f"❌ {name.capitalize():13} Build Socket Server \t \033[31mFailed\033[0m")
            return False

    def stop_server(self):
        """Stop the server and clean up resources.
        Joins the data receiving thread and closes both server and client sockets.
        """
        self.stop_thread = True

        #
        if self.thread:
            self.thread.join()

        if self.server:
            self.server.close()

        if self.client:
            self.client.close()

    def is_ready(self):
        """Check if the server has received data.

        Returns:
            bool: True if the server has received data, False otherwise.
        """
        return self.data_queue.qsize() > 0

    def is_running(self):
        """Check if the server is currently running.

        Returns:
            bool: True if the server is running, False otherwise.
        """
        return not self.stop_thread

    def get_data(self):
        """Retrieve data from the data queue.

        Returns:
            Any: The next item in the data queue.
        """
        return self.data_queue.get()

    def _recv_data_loop(self):
        """Main loop for receiving data from clients.
        Accepts client connections and processes incoming data.
        """
        while not self.stop_thread:
            try:
                self.client, addr = self.server.accept()
                logging.info(f"Connection from {addr}")

                if self.recv_data_keys == ["log"]:
                    recv_data, recv_success = self._recv_log(self.client)
                elif "image_path" in self.recv_data_keys:
                    recv_data, recv_success = self._recv_image_and_log_and_impath(self.client)
                else:
                    recv_data, recv_success = self._recv_image_and_log(self.client)

                if recv_success:
                    self.data_queue.put(recv_data)
            except Exception as e:
                print(f"Error handling client: {e}")
            finally:
                if self.client:
                    self.client.close()

    def _recv_exact(self, sock, size):
        """Receive an exact number of bytes from the socket.

        Args:
            sock (socket.socket): The socket to receive data from.
            size (int): The exact number of bytes to receive.

        Returns:
            bytearray: The received data, or None if the connection closed prematurely.
        """
        buffer = bytearray(size)
        view = memoryview(buffer)
        bytes_received = 0
        while bytes_received < size:
            nbytes = sock.recv_into(view[bytes_received:], size - bytes_received)
            if nbytes == 0:
                logging.error(f"Connection closed. Received {bytes_received} out of {size} bytes.")
                return None
            bytes_received += nbytes
        return buffer

    def _recv_int(self, sock, size=4):
        """Receive an integer from the socket.

        Args:
            sock (socket.socket): The socket to receive data from.
            size (int, optional): The number of bytes to receive. Defaults to 4.

        Returns:
            int: The received integer, or None if the reception failed.
        """
        data = self._recv_exact(sock, size)
        return struct.unpack('>I', data)[0] if data else None

    def _recv_json(self, sock):
        """Receive JSON data from the socket.

        Args:
            sock (socket.socket): The socket to receive data from.

        Returns:
            str: The received JSON data as a string.
        """
        json_data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            json_data += chunk
            if b'\r\n\r\n' in chunk:
                break
        return json_data.decode('utf-8').strip()

    def _recv_log(self, client):
        """
        Receive a log from the client socket.

        Args:
            client (socket.socket): The client socket to receive data from.

        Returns:
            tuple: A tuple containing:
                - dict: The received data with 'log' key, or None if an error occurred.
                - bool: True if the operation completed (even with an error), False otherwise.
        """
        recv_data = {
            'log': None
        }
        try:
            # Read the remaining data for JSON log
            recv_data['log'] = self._recv_json(self.client)
            return recv_data, True
        except socket.error as e:
            # Handle socket-related errors
            logging.error(f"Socket error: {e}")
            return None, True
        except IOError as e:
            # Handle I/O-related errors
            logging.error(f"I/O error: {e}")
            return None, True
        except Exception as e:
            # Handle any other unexpected errors
            logging.error(f"Unexpected error: {e}", exc_info=True)
            return None, True

    def _recv_image_and_log(self, client):
        """Receive an image and associated log data from a client.

        Args:
            client (socket.socket): The client socket to receive data from.

        Returns:
            tuple: A tuple containing the received data (dict) and a success flag (bool).
        """
        recv_data = {
            'frame_index': None,
            'image': None,
            'log': None
        }
        try:
            # Receive the frame_index
            recv_data['frame_index'] = self._recv_int(self.client)
            logging.info(f"Received frame index: {recv_data['frame_index']}")

            size = self._recv_int(self.client)
            logging.info(f"Expected image size: {size} bytes")

            # Receive the image data
            recv_data['image'] = self._recv_exact(self.client, size)

            if recv_data['image'] is None or len(recv_data['image']) != size:
                logging.error(f"Failed to receive the complete image data. Received {len(recv_data['image'] or b'')} bytes out of {size}")
                return recv_data, False

            logging.info(f"Successfully received the complete image data. Total bytes: {len(recv_data['image'])}")

            # Read the remaining data for JSON log
            recv_data['log'] = self._recv_json(self.client)
            return recv_data, True
        except socket.error as e:
            logging.error(f"Socket error: {e}")
            return None, True
        except IOError as e:
            logging.error(f"I/O error: {e}")
            return None, True
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            return None, True



    #Alister 2024-08-21
    def _recv_image_and_log_and_impath(self, client):
        """Receive an image and associated log data from a client.

        Args:
            client (socket.socket): The client socket to receive data from.

        Returns:
            tuple: A tuple containing the received data (dict) and a success flag (bool).
        """
        recv_data = {
            'frame_index': None,
            'image': None,
            'image_path': None,
            'log': None

        }
        try:
            # Receive the frame_index
            recv_data['frame_index'] = self._recv_int(self.client)
            logging.info(f"Received frame index: {recv_data['frame_index']}")

            size = self._recv_int(self.client)
            logging.info(f"Expected image size: {size} bytes")

            # Receive the image data
            recv_data['image'] = self._recv_exact(self.client, size)

            if recv_data['image'] is None or len(recv_data['image']) != size:
                logging.error(f"Failed to receive the complete image data. Received {len(recv_data['image'] or b'')} bytes out of {size}")
                return recv_data, False

            logging.info(f"Successfully received the complete image data. Total bytes: {len(recv_data['image'])}")

            # Get img path size
            impath_size = self._recv_int(self.client)
            logging.info(f"Expected image size: {size} bytes")

            # Receive the image path
            recv_data['image_path'] = self._recv_exact(self.client, impath_size)

            # Read the remaining data for JSON log
            recv_data['log'] = self._recv_json(self.client)
            return recv_data, True
        except socket.error as e:
            logging.error(f"Socket error: {e}")
            return None, True
        except IOError as e:
            logging.error(f"I/O error: {e}")
            return None, True
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            return None, True


    def _signal_handler(self, signum, frame):
        """Handle interrupt signals to gracefully shut down the server.

        Args:
            signum (int): The signal number.
            frame (frame): The current stack frame.
        """
        print("\nReceived interrupt signal. Shutting down...")
        self.stop_thread = True
        if self.server:
            self.server.close()
        if self.client:
            self.client.close()


