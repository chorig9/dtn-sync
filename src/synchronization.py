import communication

class UpdateMetric:
    LONGEST_CHAIN = 1
    NEWEST = 2

class SyncWorker:
    def __init__(self, path, conflict_resolution_callback, update_metric=UpdateMetric.LONGEST_CHAIN):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.update_metric = update_metric

        self.comm = communication.Communicator(self._on_file_received)

    def _on_file_received(self, file):
        print("XXX")
    