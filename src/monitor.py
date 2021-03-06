import pyinotify
import time
import threading

# Watches for changes in a directory
# http://seb.dbzteam.org/pyinotify/
class Watcher:
    def __init__(self, directory, event_handler, interval=1):
        self.interval = interval

        # watched events
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE |\
               pyinotify.IN_MODIFY | pyinotify.IN_OPEN |\
               pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CLOSE_NOWRITE |\
               pyinotify.IN_MOVED_FROM | pyinotify.IN_MOVED_TO

        wm = pyinotify.WatchManager()

        # Check directory for events every 1000ms timeout=self.interval * 1000
        self.notifier = pyinotify.Notifier(wm, event_handler, timeout=0)
        wdd = wm.add_watch(directory, mask)

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

class Monitor(pyinotify.ProcessEvent):
    def __init__(self, directory, callback):
        self.files_watcher = Watcher(directory, self)
        self.callback = callback

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
        self.callback.file_updated(event.pathname)

    def process_IN_CLOSE_NOWRITE(self, event):
        pass

    def process_IN_MOVED_FROM(self, event):
        pass

    def process_IN_MOVED_TO(self, event):
        pass