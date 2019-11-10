import socket
import threading
import io
import os
import utils

import logging

# Class responsible for communictation. Allows sending files to the network
# via send_file() function and calls registerd on_receive_callback every time
# new file is received from the network.
#
# Also responsible for broadcasting data to other nodes in DTN.
#
class Communicator:
    # on_receive_callback takes 2 parameters - instance of File class which
    # represents the file itself and path to where this file is stored
    def __init__(self, port, on_receive_callback):
        self.port = port
        self.on_receive_callback = on_receive_callback

        # XXX this is hack to obtain local ip address - replace with uuid
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.83.0.1", 5001))
        self.local_address = s.getsockname()[0]

        logging.debug("Local ip address: " + self.local_address)

        self.out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.out_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", self.port))

        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()

    def listen(self):
        while True:
            buffer = bytearray(4096) # XXX bigger buffer size/split recv
            nbytes, addr = self.client.recvfrom_into(buffer)

            incoming_addr, _ = addr

            # XXX Ignore messages from self
            if incoming_addr == self.local_address:
                continue

            # Call callback with data
            self.on_receive_callback(buffer)

    def send(self, data):
        # Broadcast data
        self.out_sock.sendto(data, ('10.83.255.255', self.port))
