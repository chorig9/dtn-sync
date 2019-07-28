import argparse
import synchronization
import monitor

from conflict_resolution import resolve_conflict 

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", help="Port on which dtn-sync operates", type=int, required=True)
parser.add_argument("-d", "--directory", help="Directory which will be synchronized - it must exist", required=True)

args = parser.parse_args()

sync = synchronization.SyncWorker(args.directory, args.port, resolve_conflict)
monitor = monitor.Monitor(args.directory, sync)