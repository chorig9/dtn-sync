import socket
import threading
import io
import os
import argparse

# This class is used to forward packets with some delay.
# For example, if skip == 2, it will buffer 2 packets and when third
# one arrives it will send those 2 packets to the destination and quit
class Receiver:
    def __init__(self, port, send_to, skip):
        self.port = port
        self.send_to = send_to
        self.skip = skip

        self.out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.out_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", self.port))

        self.skipped = []

        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()

        with open("/tmp/log.txt", "w") as f:
            f.write("Started\n")

    def listen(self):
        while True:
            buffer = bytearray(4096) # XXX bigger buffer size/split recv
            nbytes, addr = self.client.recvfrom_into(buffer)

            self.skipped.append(buffer)

            if self.skip + 1 == len(self.skipped):
                for packet in self.skipped[:-1]:
                    self.send(packet)

                with open("/tmp/log.txt", "a+") as f:
                    f.write("Send\n")

                sys.exit()
            else:
                with open("/tmp/log.txt", "a+") as f:
                    f.write("Skipped\n")

    def send(self, data):
        self.out_sock.sendto(data, (self.send_to, self.port))

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, required=True)
parser.add_argument("-s", "--send_to", required=True)
parser.add_argument("-k", "--skip", required=True)

args = parser.parse_args()

receiver = Receiver(args.port, args.send_to, int(args.skip))
