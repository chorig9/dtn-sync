import subprocess
import os
import errno
import threading
import time
import utils
import uuid
import shutil
import logging

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


# This structure is used to control version of a file
class FileVersionControl:
    def __init__(self, file_path, metapath, lock):
        self.lock = lock
        self.file_path = file_path
        self.metapath = metapath

        self.patched_file_path = os.path.join(metapath, os.path.basename(self.file_path) + ".new")
        self.version_history_file_path = os.path.join(metapath, os.path.basename(self.file_path) + ".version")

        self.__init_file()
        self.__init_version()

    def __exit__(self, exception_type, exception_value, traceback):
        self.lock.release()

    def __enter__(self):
        self.lock.acquire()
        return self

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

    def __resolve_conflict(self):
        tmp_copy_location = os.path.join(self.metapath, os.path.basename(self.file_path) + ".conflict_copy")

        shutil.copy2(self.file_path, tmp_copy_location)

        basename = os.path.basename(self.file_path)
        dirname = os.path.dirname(self.file_path)
        dot_index = basename.index('.')

        new_basename1 = basename[:dot_index] + utils.get_node_name() + basename[dot_index:]
        new_basename2 = basename[:dot_index] + patch.commits[-1].author + basename[dot_index:]

        new_filename1 = os.path.join(dirname, new_basename1)
        new_filename2 = os.path.join(dirname, new_basename2)

        # Create two files
        os.rename(tmp_copy_location, new_filename1)
        os.rename(self.file_path, new_filename2)

    # Applies patch (obtained from remote commit)
    def apply_patch(self, patch):
        # If signature do not match it means that file is either being
        # updated by the user or application was interrupted when commiting changes.
        # (to avoid the second case we can store signature in db and use transactions)
        # To avoid first case, we can drop the lock and restart the operation (if file is
        # being updated it means that user started updating file and we called
        # apply_patch before taking lock).
        #while not self.__verify_signature():
        #    pass

        common_commits = self.__common_commits_n(self.version_history.commits, patch.commits)
        logging.debug("VCS-apply_patch: common_commits: %d -- %d %d" % (common_commits, len(self.version_history.commits), len(patch.commits)))

        if common_commits == len(self.version_history.commits) and len(self.version_history.commits) + 1 == len(patch.commits):
            logging.debug("VCS-apply_patch: fast forward")
            # Fast forward
            rdiff_delta_apply(self.file_path, patch.delta, self.patched_file_path)

            # This is a race with user updates, see https://github.com/chorig9/dtn-sync/issues/15
            # for solutions (replace itself is atomic operation)
            os.replace(self.patched_file_path, self.file_path)
            self.version_history.commits = patch.commits
            self.version_history.signatures.append(rdiff_signature(self.file_path))
            self.__flush_version()
        elif common_commits == len(self.version_history.commits) and common_commits == len(patch.commits):
            logging.debug("VCS-apply_patch: duplicate")
            # Duplicated patch
            pass
        elif common_commits + 1 < len(patch.commits):
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
        # Conflict
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
