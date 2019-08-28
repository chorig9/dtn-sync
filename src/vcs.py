import subprocess
import os
import errno
import time

from serialization import Serializable
from enum import Enum

# This structrue contains all information about file version (it is stored on-disk)
class VersionHistory(Serializable):
    def __init__(self):
        self.timestamp = 0

# Class representing patch to a file. Holds basename of file, version and patch data (diff)
class FilePatch(Serializable):
    class Type(Enum):
        CONTENT = 1
        QUERY = 2
        ANSWER = 3
        REQUEST = 4

    def __init__(self, file_basename, version, diff, type):
        self.file_basename = file_basename
        self.diff = diff
        self.version = version
        self.type = type

    def get_version(self):
        return self.version.timestamp

# This structure is used to control version of a file
class FileVersionControl:
    def __init__(self, file_path, metadata_path):
        self.file_path = file_path
        self.metadata_path = metadata_path

        try:
            with open(self.metadata_path, "rb") as f:
                self.version_history = VersionHistory.from_bytes(f.read())
        except OSError as e:
            if e.errno == errno.ENOENT:
                self.version_history = VersionHistory()
            else:
                raise
            
    def commit(self):
        self.version_history.timestamp = time.time()

    def get_version(self):
        return self.version_history.timestamp

    def create_patch(self, type, from_version=None):
        patch = FilePatch(os.path.basename(self.file_path), self.version_history, None, type)
        if type == FilePatch.Type.CONTENT:
            with open(self.file_path, "rb") as f:
                patch.diff = f.read()
        return patch

    def apply_patch(self, patch):
        with open(self.file_path, "wb+") as f:
            print(patch.diff)
            f.write(patch.diff)
        self.version_history = patch.version

    def save_metadata(self):
        with open(self.metadata_path, "wb+") as f:
            f.write(self.version_history.to_bytes())

    # __exit__ + __enter__ allow to use FileVersionControl in 'with' block like this:
    # with FileVersionControl() as f:
    #    do something
    # which is the same as:
    # f = FileVersionControl.__enter__()
    # try:
    #    do something
    # finally:
    #    f.__exit__(type, value, traceback)
    # 
    def __exit__(self, exception_type, exception_value, traceback):
        self.save_metadata()

    def __enter__(self):
        return self

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

    def file_path(self, basename):
        return os.path.join(self.directory, basename)

    # Returns instance of FileVersionControl
    def file_version_control(self, file_basename):
        return FileVersionControl(self.file_path(file_basename),
                                self.metadata_path(file_basename))
