import subprocess
import os
import errno
import time

from serialization import Serializable

class HistoryNode:
    def __init__(self, author):
        self.timestamp = time.time()
        self.previous_node = None
        self.author = author

# This structrue contains all information about file version (it is stored on-disk)
class VersionHistory(Serializable):
    def __init__(self):
        self.history = []
        self.version = 0
        self.timestamp = time.time()

# This structure is used to control version of a file
class FileVersionControl:
    def __init__(self, file_basename, metadata_path, version_history):
        self.version_history = version_history
        self.file_basename = file_basename
        self.metadata_path = metadata_path

    def increment_version():
        self.version_history.version += 1
        self.version_history.timestamp = time.time()

    def save(self):
        with open(self.metadata_path, "wb+") as f:
            f.write(self.version_history.to_bytes())

    def __exit__(self, exception_type, exception_value, traceback):
        self.save()

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

        self.initialize_metadata()

    # Returns path to a file which holds information about provided file
    def metadata_path(self, basename):
        return os.path.join(self.metadata_dir, basename)

    def initialize_metadata(self):
        # Skip all files which start with "." - those are treated as metadata files
        files = (self.metadata_path(f) for f in 
                 os.listdir(self.directory) if not f.startswith("."))

        for filepath in files:
            try:
                # Skip if file already exists
                with open(filepath, "xb") as f:
                    f.write(VersionHistory().to_bytes())
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    # Returns instance of FileVersionControl
    def file_version_history(self, file_basename):
        with open(self.metadata_path(file_basename), "rb") as f:
            content = f.read()
            return FileVersionControl(file_basename,
                                        self.metadata_path(file_basename),
                                        VersionHistory.from_bytes(content))
