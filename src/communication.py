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
    def __init__(self):
        self.daemon_thread = threading.Thread(target=self.run_daemon)
        self.daemon_thread.start()

        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()

    def run_daemon(self):
        utils.run_command(['dtnd', '-c', './dtn.conf'])

    def listen(self):
        cur_dir = os.path.abspath(os.path.dirname(__file__))
        callback_path = cur_dir + '/callback.sh'
        utils.run_command(['dtntrigger', 'pager', '-g', 'dtn://dtnnet', callback_path])

    def send(self, patch_file_path):
        # Broadcast data
        utils.run_command(['dtnsend', '-g', 'dtn://dtnnet', patch_file_path])
