# Class representing a file. Holds basename of file and metadata (verionsing info)
class FileInfo:
    def __init__(self, file_basename, version_history):
        self.file_basename = file_basename
        self.version_history = version_history