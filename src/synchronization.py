import os
import threading
import logging

import utils
import vcs
import communication
import monitor

# Class which monitores changes to local files and sends updates to other DTN nodes.
class SyncWorker:
    def __init__(self, directory):
        self.comm = communication.Communicator()
        self.directory = directory
        self.vcs = vcs.VCS(directory)
        self.monitor = monitor.Monitor(self.directory, self)

        logging.info("Started")

    def on_data_received(self, buffer):
        try:
            patch = vcs.FilePatch.from_bytes(buffer)

            logging.info("Received: " + patch.file_basename)
            
            with self.vcs.file_version_control(patch.file_basename) as file_vcs:
                file_vcs.apply_patch(patch)
        except Exception:
            logging.exception("on_data_received")

    def file_updated(self, pathname):
        try:
            logging.info("File updated: " + pathname)

            basename = os.path.basename(pathname)

            # Update revision and time and save
            with self.vcs.file_version_control(basename) as file_vcs:
                patch = file_vcs.commit()

                patch_file_path = self.directory + '/.sync/patch_file'
                f = open(patch_file_path, 'wb+')
                f.write(patch.to_bytes())
                f.close()
                self.comm.send(patch_file_path)
                os.remove(patch_file_path)
        except Exception:
            logging.exception("file_updated")
    
