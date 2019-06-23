import communication
import pyinotify
import time
import threading

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

class SyncWorker:
    # Defines handlers for different fs events
    class EventHandler(pyinotify.ProcessEvent):
        def process_IN_CREATE(self, event):
            print("Creating:", event.pathname)

        def process_IN_MODIFY(self, event):
            # XXX does modify event gurantee write completion?

        def process_IN_DELETE(self, event):
            print("Removing:", event.pathname)

        def process_IN_OPEN(self, event):
            print("Opening:", event.pathname)

        def process_IN_CLOSE_WRITE(self, event):
            print("Closing write:", event.pathname)

        def process_IN_CLOSE_NOWRITE(self, event):
            print("Closing non write:", event.pathname)

    def __init__(self, path, conflict_resolution_callback, update_metric=UpdateMetric.LONGEST_CHAIN):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.update_metric = update_metric

        self.comm = communication.Communicator(self._on_file_received)
        self.files_watcher = Watcher("/home/igchor/xxx", SyncWorker.EventHandler())

    def _on_file_received(self, file):
        print("XXX")
    