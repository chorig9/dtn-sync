import communication
import pyinotify
import time
import threading
import os
from file import FileInfo

class UpdateMetric:
    LONGEST_CHAIN = 1
    NEWEST = 2

# Watches for changes in a directory
# http://seb.dbzteam.org/pyinotify/
class Watcher:
    def __init__(self, path, event_handler, interval=1):
        self.interval = interval

        # watched events
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE |\
               pyinotify.IN_MODIFY | pyinotify.IN_OPEN |\
               pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CLOSE_NOWRITE

        wm = pyinotify.WatchManager()

        # Check directory for events every 1000ms
        self.notifier = pyinotify.Notifier(wm, event_handler, timeout=self.interval * 1000)
        wdd = wm.add_watch(path, mask)

        self._run_check_events()

    # Periodically check events and make actions (defined in EventHandler)
    def _run_check_events(self):
        self._check_events()
        threading.Timer(self.interval, self._run_check_events).start()

    def _check_events(self):
        self.notifier.process_events()
        while self.notifier.check_events():
            self.notifier.read_events()
            self.notifier.process_events()

# Class which monitores changes to local files and sends updates to other DTN nodes.
# It's also responsible for handling received files by calling conflict_resolution_callback
class SyncWorker(pyinotify.ProcessEvent):
    def __init__(self, path, conflict_resolution_callback, update_metric=UpdateMetric.LONGEST_CHAIN):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.update_metric = update_metric

        self.comm = communication.Communicator(self._on_file_received)
        self.files_watcher = Watcher(path, self)

    def _on_file_received(self, file, store_path):
        print(file.file_basename, store_path)
        # move and overwrite if exists
        # shutil.move(store_path, file.pathname)

    ############ defines handlers for different fs events ############

    def process_IN_CREATE(self, event):
        pass

    def process_IN_MODIFY(self, event):
        # XXX does in_modify event gurantee write completion?
        dir = os.path.dirname(event.pathname)
        basename = os.path.basename(event.pathname)
        self.comm.send_file(dir, FileInfo(basename))

    def process_IN_DELETE(self, event):
        pass

    def process_IN_OPEN(self, event):
        pass

    def process_IN_CLOSE_WRITE(self, event):
        pass

    def process_IN_CLOSE_NOWRITE(self, event):
        pass

    ##################################################################
    