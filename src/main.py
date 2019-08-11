import argparse
import synchronization
import logging

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", help="Port on which dtn-sync operates", type=int, required=True)
parser.add_argument("-d", "--directory", help="Directory which will be synchronized - it must exist", required=True)
parser.add_argument("-l", "--log", help="Logging level", required=False)

args = parser.parse_args()

# Set logging level
if args.log:
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log)
    logging.basicConfig(level=numeric_level)

sync = synchronization.SyncWorker(args.directory, args.port)
