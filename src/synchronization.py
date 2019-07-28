import pyinotify
import time
import threading
import os
import errno

from vcs import *
import communication
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
    def __init__(self, path, port, conflict_resolution_callback, update_metric=UpdateMetric.LONGEST_CHAIN):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.update_metric = update_metric
        self.directory = path

        self.comm = communication.Communicator(port, self._on_file_received)
        self.files_watcher = Watcher(path, self)

        self.vcs = VCS(path)

        self.conflict_store_directory = os.path.join(path, ".conflicts")

        self.update_in_progress = {""}

        try:
            os.mkdir(self.conflict_store_directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def _on_file_received(self, file, store_path):
        # XXX: remove print
        print(file.file_basename, store_path)

        file_vcs = self.vcs.file_version_history(file.file_basename)

        self.update_in_progress.add(file.file_basename)
        try:
            file_vcs.apply_patch(file.patch)
        except Exception as e:
            print(e)
        self.update_in_progress.remove(file.file_basename)

    def update_file_info(self, basename):
        file_vcs = self.vcs.file_version_history(basename)
        file_vcs.commit()
        patch = file_vcs.create_patch()

        file_info = FileInfo(basename, patch)
        self.comm.send_file(self.directory, file_info)

    # If, file should not be processed (because it is metadata) returns true
    def skip_file(self, filename):
        return filename.startswith(".")

    ############ defines handlers for different fs events ############
    # XXX currently, only one level directory is supoorted - changes
    # in sub directoreis are NOT handled

    def process_IN_CREATE(self, event):
        pass

    def process_IN_MODIFY(self, event):
        pass

    def process_IN_DELETE(self, event):
        pass

    def process_IN_OPEN(self, event):
        pass

    def process_IN_CLOSE_WRITE(self, event):
        basename = os.path.basename(event.pathname)

        if self.skip_file(basename):
            return

        print(os.listdir(os.path.dirname(event.pathname)))

        # Check if file is being updated
        # This is a workaround for infinite loop which would occur
        # when file is updated in _on_file_received callback (git will modify the file
        # which will trigger this event which will send update to other nodes, etc.)
        if not basename in self.update_in_progress:
            self.update_file_info(basename)

    def process_IN_CLOSE_NOWRITE(self, event):
        pass

    ##################################################################
    