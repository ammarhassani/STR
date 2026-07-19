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

# Windows error codes a SHARE raises that a local disk never does. All of them
# are transient: the file is held by another PC, or the session dropped and the
# redirector is reconnecting. Retrying is correct; failing the caller is not.
#   5    ERROR_ACCESS_DENIED        lost a rename race with another client
#   32   ERROR_SHARING_VIOLATION    another PC has the file open
#   53   ERROR_BAD_NETPATH          share not reachable right now
#   55   ERROR_DEV_NOT_EXIST        the redirector dropped the connection
#   59   ERROR_UNEXP_NET_ERR        session error, reconnecting
#   64   ERROR_NETNAME_DELETED      the share went away (sleep/cable/DFS failover)
#   121  ERROR_SEM_TIMEOUT          the server did not answer in time
#   1231 ERROR_NETWORK_UNREACHABLE  network down between us and the host
_TRANSIENT_SHARE_ERRORS = {5, 32, 53, 55, 59, 64, 121, 1231}


def _is_transient(exc) -> bool:
    """True when this failure is the share misbehaving rather than a real error
    (a missing source file, a bad path) that retrying will never fix."""
    code = getattr(exc, "winerror", None)
    if code is not None:
        return code in _TRANSIENT_SHARE_ERRORS
    # POSIX: EACCES/EBUSY are the closest equivalents
    return getattr(exc, "errno", None) in (13, 16)


def replace_with_retry(tmp, dest, timeout=10.0, interval=0.05):
    """os.replace(tmp, dest), retrying while the share is busy or blipping.

    Covers more than a locked destination: a real share also drops the session
    outright (ERROR_NETNAME_DELETED) when a PC sleeps, a cable moves, or a DFS
    target fails over. That surfaced as an OSError, not a PermissionError, and
    took the host's replica publish down with it -- which in run_once() aborts
    the command ACK the client is waiting on.
    """
    deadline = time.time() + timeout
    while True:
        try:
            os.replace(tmp, dest)
            return
        except OSError as e:
            if not _is_transient(e) or time.time() >= deadline:
                raise
            time.sleep(interval)
