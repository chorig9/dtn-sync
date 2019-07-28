import subprocess
import os
import errno
import time

import utils
from serialization import Serializable

# This structure is used to control version of a file
class FileVersionControl:
    def __init__(self, filepath, metadata_path):
        self.filepath = filepath
        self.metadata_path = metadata_path
        self.work_tree = os.path.dirname(self.filepath)
        self.git_vars = [("GIT_DIR", self.metadata_path),
                         ("GIT_WORK_TREE", self.work_tree)]

                # It is safe to run git init on already initialized repo
        self.run_git_command(["init"])

    def run_git_command(self, command):
        return utils.run_command(["git", "-c", "user.name=XXX", "-c", "user.email=XXX"] + command, self.git_vars)

    def commit(self):
        self.run_git_command(["add", self.filepath])
        self.run_git_command(["commit", "--allow-empty-message", "-m", ""])

    def create_patch(self):
        # XXX - instead of --root - specify some version
        return self.run_git_command(["format-patch", "--root", "--stdout"]) # XXX - is stdout/in a good idea?

    def apply_patch(self, patch):
        # XXX conflicts

        patch_file = utils.get_tmp_filename() + ".patch"

        with open(patch_file, "wb+") as f:
            f.write(patch)

        self.run_git_command(["-C", self.work_tree, "apply", patch_file])
        self.commit()

        os.remove(patch_file)

# Version Control System - Class which creates abstraction for versioning system
class VCS:
    def __init__(self, directory):
        self.directory = directory
        self.metadata_dir = os.path.join(directory, ".vcs")

        try:
            os.mkdir(self.metadata_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    # Returns path to a file which holds information about provided file
    def metadata_path(self, basename):
        return os.path.join(self.metadata_dir, basename)

    # Returns instance of FileVersionControl
    def file_version_history(self, file_basename):
        return FileVersionControl(os.path.join(self.directory, file_basename), self.metadata_path(file_basename))
