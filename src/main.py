import synchronization

sync = synchronization.SyncWorker("XXX", lambda file1, file2 : print(str(file1) + " " + str(file2)))
