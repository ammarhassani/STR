"""os.replace() that tolerates Windows file locking.

POSIX replaces a file even while readers hold it open; Windows raises
PermissionError (WinError 5/32) instead. Both sides of the replica pipeline hit
this on the workstation LAN: the host republishes bus/replica/fiu_ro.db while
clients are copying it, and each client swaps its own local replica while its
read-only sqlite connections come and go. Every holder keeps the file for
milliseconds, so a bounded retry clears the collision.

ponytail: bounded retry, not versioned filenames. If the DB ever grows big
enough that reads overlap continuously, publish to fiu_ro.<version>.db and point
version.txt at the name instead.
"""
import os
import time


def replace_with_retry(tmp, dest, timeout=10.0, interval=0.05):
    """os.replace(tmp, dest), retrying while dest is locked by a reader."""
    deadline = time.time() + timeout
    while True:
        try:
            os.replace(tmp, dest)
            return
        except PermissionError:
            if time.time() >= deadline:
                raise
            time.sleep(interval)
