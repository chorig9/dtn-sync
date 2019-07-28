import os

import vcs
import communication

# Class which monitores changes to local files and sends updates to other DTN nodes.
# It's also responsible for handling received files by calling conflict_resolution_callback
class SyncWorker:
    def __init__(self, directory, port, conflict_resolution_callback):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.comm = communication.Communicator(port, self._on_data_received)
        self.vcs = vcs.VCS(directory)

        self.update_in_progress = {""}

    def _on_data_received(self, buffer):
        patch = vcs.FilePatch.from_bytes(buffer)

        print("received: ", patch.file_basename, patch.get_version(), patch.diff)
        
        with self.vcs.file_version_control(patch.file_basename) as local_file_vcs:
            print(patch.get_version(), local_file_vcs.get_version())
            if patch.get_version() > local_file_vcs.get_version():
                self.update_in_progress.add(patch.file_basename)
                local_file_vcs.apply_patch(patch)

    def file_updated(self, pathname):
        print("Update file: ", pathname)

        dir = os.path.dirname(pathname)
        basename = os.path.basename(pathname)

        # Check if file is being updated
        # This is a workaround for infinite loop which would occur
        # when file is updated in _on_file_received callback (git will modify the file
        # which will trigger this event which will send update to other nodes, etc.)
        if basename in self.update_in_progress:
            self.update_in_progress.remove(basename)
            return

        # Update revision and time and save
        with self.vcs.file_version_control(basename) as file_vcs:
            file_vcs.commit()
            self.comm.send(file_vcs.create_patch().to_bytes())
    