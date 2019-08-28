import os

import vcs
import communication
import time
import threading

# Class which monitores changes to local files and sends updates to other DTN nodes.
# It's also responsible for handling received files by calling conflict_resolution_callback
class SyncWorker:
    def __init__(self, directory, port, conflict_resolution_callback):
        self.conflict_resolution_callback = conflict_resolution_callback
        self.comm = communication.Communicator(port, self._on_data_received)
        self.vcs = vcs.VCS(directory)

        self.update_in_progress = {""}
        self.answers = {}

    def _on_data_received(self, buffer, sender_address):
        patch = vcs.FilePatch.from_bytes(buffer)

        print("received: ", patch.file_basename, patch.get_version(), patch.diff)

        with self.vcs.file_version_control(patch.file_basename) as local_file_vcs:
            print(patch.get_version(), local_file_vcs.get_version())
            if patch.type == vcs.FilePatch.Type.QUERY:
                if patch.get_version() < local_file_vcs.get_version():
                    self.answer_query(local_file_vcs, sender_address)
            elif patch.type == vcs.FilePatch.Type.ANSWER:
                if patch.file_basename in self.answers:
                    self.answers[patch.file_basename].append((sender_address, patch))
            elif patch.type == vcs.FilePatch.Type.REQUEST:
                self.answer_request(local_file_vcs, sender_address)
            elif patch.type == vcs.FilePatch.Type.CONTENT:
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
            self.comm.broadcast(file_vcs.create_patch(vcs.FilePatch.Type.CONTENT).to_bytes())

    def wait_for_answers(self, filename):
        time.sleep(5)
        answer = self.answers.pop(filename)
        with self.vcs.file_version_control(filename) as local_file_vcs:
            newest_patch = None
            for sender_address, patch in answer:
                if patch.get_version() > local_file_vcs.get_version():
                    newest_patch = patch

            if newest_patch is not None:
                self.request_from_neighbour(local_file_vcs, sender_address)

    def query_neighbours(self, filename):
        if any(filename in pair for pair in self.answers):
            print("File " + filename + " already being queried for.")
            return

        self.answers[filename] = []
        with self.vcs.file_version_control(filename) as file_vcs:
            answers_thread = threading.Thread(target=self.wait_for_answers, args=[filename])
            answers_thread.start()
            self.comm.broadcast(file_vcs.create_patch(vcs.FilePatch.Type.QUERY).to_bytes())

    def answer_query(self, file_vcs, address):
        self.comm.send(file_vcs.create_patch(vcs.FilePatch.Type.ANSWER).to_bytes(), address)

    def request_from_neighbour(self, file_vcs, address):
        self.comm.send(file_vcs.create_patch(vcs.FilePatch.Type.REQUEST).to_bytes(), address)

    def answer_request(self, file_vcs, address):
        self.comm.send(file_vcs.create_patch(vcs.FilePatch.Type.CONTENT).to_bytes(), address)
