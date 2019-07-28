import socket
import threading
import io
import os
import utils

from serialization import Serializable

# Class responsible for communictation. Allows sending files to the network
# via send_file() function and calls registerd on_receive_callback every time
# new file is received from the network.
#
# Also responsible for broadcasting data to other nodes in DTN.
#
class Communicator:
    # Definiton of data which is beeing sent over the network
    class Data(Serializable):
        def __init__(self):
            self.file_content = None
            self.file_info = None

    # on_receive_callback takes 2 parameters - instance of File class which
    # represents the file itself and path to where this file is stored
    def __init__(self, port, on_receive_callback):
        self.port = port
        self.on_receive_callback = on_receive_callback

        # XXX this is hack to obtain local ip address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.local_address = s.getsockname()[0]

        # Folder in which every incoming data will be stored
        self.store_folder = utils.get_tmp_folder()

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

            # Ignore messages from self
            if incoming_addr == self.local_address:
                return

            data = Communicator.Data.from_bytes(buffer)
            
            # Writes received file content to a file
            received_file = os.path.join(self.store_folder, data.file_info.file_basename)
            with open(received_file, 'wb+') as f:
                f.write(data.file_content)

            # Call callback with file_info and path to received file
            self.on_receive_callback(data.file_info, received_file)

    # root_dir - directory in which file_info.file_basaneme file is located
    # file_info - instance of FileInfo class
    def send_file(self, root_dir, file_info):
        data = Communicator.Data()

        data.file_info = file_info

        with open(os.path.join(root_dir, file_info.file_basename), 'rb') as f:
            data.file_content = f.read()

        # Broadcast data
        self.out_sock.sendto(data.to_bytes(), ('255.255.255.255', self.port))
