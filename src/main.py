import synchronization
from conflict_resolution import resolve_conflict 

sync = synchronization.SyncWorker("/tmp/xxx", resolve_conflict)