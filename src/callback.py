#!/usr/bin/env python3
import sys
import synchronization
import os
import vcs

def main():
    f = open(os.path.abspath(os.path.dirname(__file__)) + "/workdir.txt", "r")
    workdir = f.read()
    f.close()
    
    v= vcs.VCS(workdir)

    f = open(sys.argv[1], 'rb')
    b = f.read()
    f.close()

    patch = vcs.FilePatch.from_bytes(b)

    with v.file_version_control(patch.file_basename) as file_vcs:
        file_vcs.apply_patch(patch)


if __name__ == '__main__':
    main()
