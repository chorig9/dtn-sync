#!/usr/bin/python3

import argparse
import synchronization
import logging
import sys
import os
import utils

import daemon

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interfaces", nargs='+', help="Network interface(s) connected to other dtn nodes", required=True)
    parser.add_argument("-d", "--directory", help="Directory which will be synchronized - it must exist", required=True)
    parser.add_argument("-l", "--log", help="Logging level", required=False)
    parser.add_argument("-o", "--stdout", help="Stdout file", required=False)

    args = parser.parse_args(args)

    utils.generate_dtn_config(args.interfaces)

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

    f = open(os.path.abspath(os.path.dirname(__file__)) + "/workdir.txt", "w+")
    f.write(args.directory)
    f.close()

    with daemon.DaemonContext(stdout=stdout, stderr=stdout):
        sync = synchronization.SyncWorker(args.directory)

if __name__ == '__main__':
    main()
