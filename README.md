# dtn-sync

File synchronization system for DTN

### How it works

dnt-sync uses linux inotify API (http://man7.org/linux/man-pages/man7/inotify.7.html) to watch file changes within a directory.
If a change is detected version of a file is increased and modification is send to other nodes (rsync is used to
send and apply only diffs, not whole files). 

### Limitations

#### No mmap/msync/munmap support
Inotify does not report events when file is changed because of mmap/msync/munmap which means that dtn-sync does
not know anything about those changes.

#### Renaming files
Because of problems with handling rename() events (described in inotify manpage) this operation is not supported
by dtn-sync. If a user renames a file - it can leave system in an inconsistent state.

#### Multiple writers
Currently writing to one file from more then one process is not allowed (it will leave file in inconsistent state).
