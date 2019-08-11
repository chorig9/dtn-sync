import os
import threading

import utils
import vcs
import communication

# Class which monitores changes to local files and sends updates to other DTN nodes.
# It's also responsible for handling received files by calling conflict_resolution_callback
class SyncWorker:
    def __init__(self, directory, port, conflict_resolution_callback):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.comm = communication.Communicator(port, self._on_data_received)
        self.directory = directory
        self.vcs = vcs.VCS(directory)

        # XXX: lock per file?
        self.lock_update = threading.RLock()

        # This dictionary holds checksums of files after applying patch
        # If inside file_updated checksum of a file is equal to checksum stored in self.checksums
        # it means that file_updated was called because of that update (and not user action), we should skip this event
        self.checksums = {}

    def _on_data_received(self, buffer):
        # XXX: Additionally we should also prevent user from modyfing file?
        # We could for example, change permissions to the file for time of receiving patch (to raad-only)
        # XXX: what about text editors (they usually open file for reading, load data to memory and close the file, they write to file only when necessary)
        # We could parse ps aux | grep "filename" ?
        self.lock_update.acquire()

        patch = vcs.FilePatch.from_bytes(buffer)

        print("received: ", patch.file_basename)
        
        with self.vcs.file_version_control(patch.file_basename) as local_file_vcs:
            local_file_vcs.apply_patch(patch, self.conflict_resolution_callback)

            full_path = os.path.join(self.directory, patch.file_basename)
            self.checksums[patch.file_basename] = utils.get_file_checksum(full_path)

        self.lock_update.release()

    def file_updated(self, pathname):
        self.lock_update.acquire()

        print("Update file: ", pathname)

        dir = os.path.dirname(pathname)
        basename = os.path.basename(pathname)

        try:
            if self.checksums[basename] == utils.get_file_checksum(pathname):
                self.lock_update.release()
                return
        except Exception as e:
            pass

        # Update revision and time and save
        with self.vcs.file_version_control(basename) as file_vcs:
            file_vcs.commit()
            self.comm.send(file_vcs.create_patch().to_bytes())

        self.lock_update.release()
    