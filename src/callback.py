#!/usr/bin/env python3
import sys
import os
import socket
import sys

def main():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ('localhost', 10000)
    sock.connect(server_address)

    try:
        message = str.encode(sys.argv[1])
        sock.sendall(message)
    finally:
        sock.close()

if __name__ == '__main__':
    main()
