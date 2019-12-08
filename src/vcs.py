import subprocess
import os
import errno
import threading
import time
import utils
import uuid
import shutil
import logging

from enum import Enum
from serialization import Serializable

RDIFF_EMPTY_SIGNATURE = b'rs\x016\x00\x00\x08\x00\x00\x00\x00\x08'

def rdiff_empty_signature():
    return RDIFF_EMPTY_SIGNATURE

def rdiff_signature(file):
    return utils.run_command(["rdiff", "signature", file, "-"])

def rdiff_delta(signature, file):
    return utils.run_command(["rdiff", "delta", "-", file], signature)

def rdiff_delta_apply(file, delta, new_file):
    return utils.run_command(["rdiff", "patch", file, "-", new_file], delta)

class Commit(Serializable):
    def __init__(self):
        self.author = None
        self.id = None


# This structrue contains all information about file version (it is stored on-disk)
# XXX: think about vector clocks https://queue.acm.org/detail.cfm?id=2917756
class VersionHistory(Serializable):
    def __init__(self):
        self.commits = []
        self.signatures = [] #XXX: signatures can be prunned sometimes


# Class representing patch to a file. Holds basename of file, commit info and delta
class FilePatch(Serializable):
    def __init__(self):
        self.file_basename = None
        self.commits = []
        self.delta = None


class SynchronizationType(Enum):
    FAST_FORWARD = 0
    DUPLICATE = 1
    OUT_OF_ORDER = 2
    CONFLICT = 3


# This structure is used to control version of a file
class FileVersionControl:
    def __init__(self, file_path, metapath, lock):
        self.lock = lock
        self.file_path = file_path
        self.metapath = metapath

        # If conflicted path is set this means that now there are per-node files
        # XXX: we can have node name in filename from the beggining (just keep on link per
        # file without nodename)
        if os.path.exists(self.__conflict_flag_path()):
            # In this case, we do not know which file to update - decision is made in apply_patch
            return

        self.patched_file_path = os.path.join(metapath, os.path.basename(self.file_path) + ".new")
        self.version_history_file_path = os.path.join(metapath, os.path.basename(self.file_path) + ".version")

        self.__init_file()
        self.__init_version()

    def __exit__(self, exception_type, exception_value, traceback):
        self.lock.release()

    def __enter__(self):
        self.lock.acquire()
        return self

    def __conflict_flag_path(self):
        return os.path.join(self.metapath, os.path.basename(self.file_path) + ".conflicted")

    def __init_file(self):
        # Create file if not exists
        # XXX implement rename_no_replace, this is a race with user creation
        if not os.path.exists(self.file_path):
            # Use rename to avoid inotify crate event event
            tmp = utils.get_tmp_file()
            open(tmp, 'w').close()
            os.rename(tmp, self.file_path)

    def __init_version(self):
        # Load version from file or create empty version if file does not exist
        if not os.path.exists(self.version_history_file_path):
            self.version_history = VersionHistory()
        else:
            with open(self.version_history_file_path, 'rb') as f:
                content = f.read()
                self.version_history = VersionHistory.from_bytes(content)

    # Saves version to file
    def __flush_version(self):
        with open(self.version_history_file_path, 'wb') as f:
            f.write(self.version_history.to_bytes())

    # Returns diff between current version and version represented by signature file
    def __get_delta(self):
        signature = None
        if len(self.version_history.signatures) > 0:
            signature = self.version_history.signatures[-1]
        else:
            signature = rdiff_empty_signature()

        return rdiff_delta(signature, self.file_path)

    def __waiting_patch_location(self, commit_id):
        return os.path.join(self.metapath, os.path.basename(self.file_path) + ".patch" + str(commit_id))

    def __load_patch(self, commit_id):
        with open(self.__waiting_patch_location(commit_id), 'rb') as f:
            content = f.read()
            return FilePatch.from_bytes(content)

    def __apply_waiting_patches(self, waiting):
        for commit in waiting:
            self.apply_patch(self.__load_patch(commit.id))

        for commit in waiting:
            os.remove(self.__waiting_patch_location(commit.id))

    # Saves patch which cannot be applied (waiting for other patch)
    def __save_patch(self, patch):
        last_commit_id = patch.commits[-1].id

        with open(self.__waiting_patch_location(last_commit_id), 'wb') as f:
            f.write(patch.to_bytes())

    def __patch_exists(self, commit_id):
        return os.path.exists(self.__waiting_patch_location(commit_id))

    # Save information about change and update file signature
    def __create_commit(self):
        c = Commit()
        c.author = utils.get_node_name()
        c.id = uuid.uuid1()

        return c

    # Commits changes and returns patch (which can be applied on other nodes)
    #
    # If application crashes in the middle of this operation a change made to
    # a file might not be recorded. This is problematic for apply_patch function
    # so, in apply_patch we verify that a file hase the same signature as the one
    # stored in self.signature_file_path. If signatures do not match we perform
    # recovery
    def commit(self):
        delta = self.__get_delta()
        signature = rdiff_signature(self.file_path)

        # Commit changes
        commit = self.__create_commit()
        self.version_history.commits.append(commit)
        self.version_history.signatures.append(signature)
        self.__flush_version()

        # Create patch
        patch = FilePatch()
        patch.file_basename = os.path.basename(self.file_path)
        patch.delta = delta
        patch.commits = self.version_history.commits

        # XXX: what if application crashes here? Should we handle that?
        # Patch won't be send to other nodes. We could have some "flag" stored on-disk
        # to notify about started but not completed operation.

        return patch

    # def __verify_signature(self):
    #     tmp_file = utils.get_tmp_file()
    #     rdiff_signature(tmp_file, self.file_path)

    #     hash_actual = utils.get_file_checksum(tmp_file)
    #     hash_expected = utils.get_file_checksum(self.signature_file_path)

    #     os.remove(tmp_file)

    #     return hash_actual == hash_expected

    # Appends nodename to basename(filename) keeping the file extension.
    # Returns new filename
    def __append_node_name_to_file_name(self, filename, nodename):
        basename = os.path.basename(filename)
        dirname = os.path.dirname(filename)

        dot_index = None
        try:
            dot_index = basename.index('.')
        except ValueError as e:
            dot_index = len(basename)

        new_basename = basename[:dot_index] + nodename + basename[dot_index:]
        new_filename = os.path.join(dirname, new_basename)

        return new_filename

    def __resolve_conflict(self, patch):
        tmp_copy_location = os.path.join(self.metapath, os.path.basename(self.file_path) + ".conflict_copy")

        already_conflicted = os.path.exists(self.__conflict_flag_path())

        # Create conflict flag
        open(self.__conflict_flag_path(), 'w').close()

        shutil.copy2(self.file_path, tmp_copy_location)

        if not already_conflicted:
            new_filename1 = self.__append_node_name_to_file_name(self.file_path, utils.get_node_name())
        else:
            new_filename1 = self.file_path

        new_filename2 = self.__append_node_name_to_file_name(self.file_path, patch.commits[-1].author)

        # Create two files
        os.rename(tmp_copy_location, new_filename1)
        os.rename(self.file_path, new_filename2)

        local_file_vcs = FileVersionControl(new_filename1, self.metapath, None)
        shutil.copy2(self.version_history_file_path, local_file_vcs.version_history_file_path)
        local_file_vcs.__init_version()

        remote_file_vcs = FileVersionControl(new_filename2, self.metapath, None)
        shutil.copy2(self.version_history_file_path, remote_file_vcs.version_history_file_path)
        remote_file_vcs.__init_version()
        
        common_commits = self.__common_commits_n(remote_file_vcs.version_history.commits, patch.commits)
        remote_file_vcs.version_history.commits = remote_file_vcs.version_history.commits[:common_commits]
        remote_file_vcs.version_history.signatures = remote_file_vcs.version_history.signatures[:common_commits]

        remote_file_vcs.apply_patch(patch)

    def __synchronization_type(self, patch):
        common_commits = self.__common_commits_n(self.version_history.commits, patch.commits)

        if common_commits == len(self.version_history.commits) and len(self.version_history.commits) + 1 == len(patch.commits):
            return SynchronizationType.FAST_FORWARD
        elif common_commits == len(self.version_history.commits) and common_commits == len(patch.commits):
            return SynchronizationType.DUPLICATE
        elif common_commits + 1 < len(patch.commits):
            return SynchronizationType.OUT_OF_ORDER
        else:
            return SynchronizationType.CONFLICT
        

    # Applies patch (obtained from remote commit)
    def apply_patch(self, patch):
        # XXX: check signature
        # If signature do not match it means that file is either being
        # updated by the user or application was interrupted when commiting changes.
        # (to avoid the second case we can store signature in db and use transactions)
        # To avoid first case, we can drop the lock and restart the operation (if file is
        # being updated it means that user started updating file and we called
        # apply_patch before taking lock).
        #
        # Additionally we should always work on copy of a file instead of original. The copy
        # should be done BEFORE applying rdiff delta (so that we can check that copy has proper
        # signature). Original file can always be modified by the user (even in the middle of 
        # appy_patch operation).
        #while not self.__verify_signature():
        #    pass

        # If file is marked as conflicted this means that there are multiple versions of this file.
        # If possible, find version to which the patch can be applied. If that's not possible take
        # whichever
        if os.path.exists(self.__conflict_flag_path()):
            dir = os.path.dirname(self.file_path)
            for file in os.listdir(dir):
                if file.startswith(os.path.basename(self.file_path)):
                    candidate = FileVersionControl(os.path.join(dir, file), self.metapath, None)
                    if candidate.__synchronization_type(patch) != SynchronizationType.CONFLICT:
                        self = candidate
                        break

        common_commits = self.__common_commits_n(self.version_history.commits, patch.commits)
        logging.debug("VCS-apply_patch: common_commits: %d -- %d %d" % (common_commits, len(self.version_history.commits), len(patch.commits)))

        sync_type = self.__synchronization_type(patch)

        if sync_type == SynchronizationType.FAST_FORWARD:
            logging.debug("VCS-apply_patch: fast forward")
            rdiff_delta_apply(self.file_path, patch.delta, self.patched_file_path)

            # XXX: This is a race with user updates, see https://github.com/chorig9/dtn-sync/issues/15
            # for solutions (replace itself is atomic operation)
            os.replace(self.patched_file_path, self.file_path)
            self.version_history.commits = patch.commits
            self.version_history.signatures.append(rdiff_signature(self.file_path))
            self.__flush_version()
        elif sync_type == SynchronizationType.DUPLICATE:
            logging.debug("VCS-apply_patch: duplicate")
            pass
        elif sync_type == SynchronizationType.OUT_OF_ORDER:
            logging.debug("VCS-apply_patch: out of order")
            # Out-of-order patch (patch which depends on a previous one, which possibly did not arrive yet)
            # This includes conflicting patches, eg.
            #
            #     * -- received patch
            #    /
            # * *
            # |/
            # *     -- 2 common commits
            # |
            # *
            self.__save_patch(patch)

            # Check whether all required patches are present
            dependencies = patch.commits[common_commits:]
            for commit in dependencies:
                if not self.__patch_exists(commit.id):
                    return

            # We have all the required patches (dependencies)
            self.__apply_waiting_patches(dependencies)

            # XXX: add some recovery mechanism (restore after restart?)
            # Both for case when we crashed during applying patches and
            # before even handling one.
        else:
            logging.debug("VCS-apply_patch: conflict")
            self.__resolve_conflict(patch)

    def __common_commits_n(self, local_commits, remote_commits):
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
        self.metapath = os.path.join(self.directory, ".sync")

        # XXX: lock per file
        self.lock = threading.Lock()

        try:
            os.makedirs(self.metapath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def _file_path(self, basename):
        return os.path.join(self.directory, basename)

    # Returns instance of FileVersionControl
    def file_version_control(self, file_basename):
        return FileVersionControl(self._file_path(file_basename), self.metapath, self.lock)
