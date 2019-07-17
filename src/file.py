# Class representing a file. Holds basename of file and metadata (verionsing info)
class FileInfo:
    def __init__(self, file_basename):
        self.file_basename = file_basename