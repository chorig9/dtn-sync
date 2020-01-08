import socket
import threading
import io
import os
import utils
import subprocess

import logging

# Class responsible for communication. Allows sending files to the network
# via send_file() function and calls registerd on_receive_callback every time
# new file is received from the network.
#
# Also responsible for broadcasting data to other nodes in DTN.
#
class Communicator:
    def __init__(self, on_receive_callback):
        self.on_receive_callback = on_receive_callback

        self.daemon_thread = threading.Thread(target=self.run_daemon)
        self.daemon_thread.start()

        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('localhost', 10000))

        threading.Thread(target=self.accept_trigger).start()

    def run_daemon(self):
        utils.run_command(['dtnd', '-c', './dtn.conf'])

    def accept_trigger(self):
        self.sock.listen(1)
        while True:
            connection, client_address = self.sock.accept()
            try:
                data = connection.recv(1024)
                data = data.decode()                   
            finally:
                connection.close()

            with open(data, 'rb') as f:
                buffer = f.read()
                self.on_receive_callback(buffer)

    def listen(self):
        cur_dir = os.path.abspath(os.path.dirname(__file__))
        callback_path = cur_dir + '/callback.sh'
        utils.run_command(['dtntrigger', 'pager', callback_path])

    def send(self, patch_file_path):
        # Broadcast data
        utils.run_command(['dtnsend', 'dtn://CoreNode2/pager', patch_file_path])
