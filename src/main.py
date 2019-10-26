#!/usr/bin/python3

import argparse
import synchronization
import logging
import sys

import daemon

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Port on which dtn-sync operates", type=int, required=True)
    parser.add_argument("-d", "--directory", help="Directory which will be synchronized - it must exist", required=True)
    parser.add_argument("-l", "--log", help="Logging level", required=False)
    parser.add_argument("-o", "--stdout", help="Stdout file", required=False)

    args = parser.parse_args(args)

    # Set logging level
    if args.log:
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.log)
        logging.basicConfig(level=numeric_level)

    stdout = None
    if args.stdout:
        stdout = open(args.stdout, 'w')
    else:
        stdout = open("/dev/stdout", 'w')

    with daemon.DaemonContext(stdout=stdout, stderr=stdout):
        sync = synchronization.SyncWorker(args.directory, args.port)

if __name__ == '__main__':
    main()
