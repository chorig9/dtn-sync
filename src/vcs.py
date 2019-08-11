import subprocess
import os
import errno
import time
import utils
import uuid

from serialization import Serializable

def rdiff_signature(file):
    return utils.run_command(["rdiff", "signature", file, "-"])

def rdiff_delta(signature, file):
    return utils.run_command(["rdiff", "delta", "-", file], signature)

def rdiff_delta_apply(file, delta, new_file):
    # Make sure file exists
    open(file, 'a').close()

    return utils.run_command(["rdiff", "patch", file, "-", new_file], delta)

def rdiff_empty_signature():
    tmp_file = utils.get_tmp_file()
    open(tmp_file, 'a').close()
    signature = rdiff_signature(tmp_file)
    os.remove(tmp_file)

    return signature

class Commit():
    def __init__(self):
        self.author = None
        self.id = None


# This structrue contains all information about file version (it is stored on-disk)
# XXX: think about vector clocks https://queue.acm.org/detail.cfm?id=2917756
class VersionHistory(Serializable):
    def __init__(self):
        self.commits = []


# Class representing request for a patch
class FilePatchRequest(Serializable):
    def __init__(self):
        self.signature = rdiff_empty_signature()
        self.version_history = None


# Class representing patch to a file. Holds basename of file, commit info and delta
class FilePatch(Serializable):
    def __init__(self):
        self.file_basename = None
        self.base_commit = None
        self.commits = []
        self.delta = None


# This structure is used to control version of a file
class FileVersionControl:
    def __init__(self, file_path):
        self.file_path = file_path
        self.version_history = VersionHistory() # XXX: store this in some DB (lsm-db?)

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def __enter__(self):
        return self
    
    def commit(self):
        c = Commit()
        c.author = utils.get_node_name()
        c.id = uuid.uuid1()

        self.version_history.commits.append(c)

    # Creates request for a patch
    def patch_request(self):
        request = FilePatchRequest()
        request.signature = rdiff_signature(self.file_path)
        request.version_history = self.version_history

    # Creates patch for remote node accordignly to file_patch_request (obtained from patch_request)
    def create_patch(self, file_patch_request = FilePatchRequest()):
        common_commits_n = 0
        if file_patch_request.version_history is not None:
            common_commits_n = self._common_commits_n(self.version_history.commits, file_patch_request.version_history.commits)
        # Remote node alread has all local commits
        if common_commits_n == len(self.version_history.commits):
            return None

        patch = FilePatch()
        patch.file_basename = os.path.basename(self.file_path)
        patch.delta = rdiff_delta(file_patch_request.signature, self.file_path)

        if common_commits_n > 0:
            patch.base_commit = self.version_history.commits[common_commits_n - 1]

        patch.commits = self.version_history.commits[common_commits_n:-1]

        return patch

    # Applies patch (obtained from create_patch)
    def apply_patch(self, patch, conflict_callback):
        # Initial commit
        if patch.base_commit is None and len(self.version_history.commits) == 0:
            self.version_history.commits.append(patch.commits)
            rdiff_delta_apply(self.file_path, patch.delta, self.file_path)
        # Fast forward
        elif patch.base_commit.id == self.version_history.commits[-1].id:
            self.version_history.commits.append(patch.commits)
            rdiff_delta_apply(self.file_path, patch.delta, self.file_path)
        # Collision
        else:
            tmp_file = utils.get_tmp_file()
            rdiff_delta_apply(self.file_path, patch.delta, tmp_file)

            conflict_res = conflict_callback(self.file_path, tmp_file)
            if conflict_res is None:
                # reject patch
                # XXX: ban this situation or save patch somewhere
                return
            else:
                self.version_history.commits.append(patch.commits)
                shutil.move(conflict_res, self.file_path)
                os.remove(tmp_file)

    def _common_commits_n(self, local_commits, remote_commits):
        n_commits = min(len(local_commits), len(remote_commits))
        for i in range(0, n_commits):
            local_commit = local_commits[i]
            remote_commit = remote_commits[i]

            if local_commit.id != remote_commit.id:
                return i

        return n_commits

# Version Control System - Class which creates abstraction for versioning system
class VCS:
    def __init__(self, directory):
        self.directory = directory

    def file_path(self, basename):
        return os.path.join(self.directory, basename)

    # Returns instance of FileVersionControl
    def file_version_control(self, file_basename):
        return FileVersionControl(self.file_path(file_basename))
