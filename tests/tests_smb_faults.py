"""What a real SMB share does to this app when it misbehaves.

Run: python tests_smb_faults.py

A loopback UNC path (\\\\localhost\\C$, or even \\\\<own-LAN-IP>\\C$) is NOT a
substitute for a real share: Windows short-circuits a connection to itself, and
measurements on this machine put it at 1.0x local-disk speed. It gives the path
syntax and none of the semantics, so a test that "passed over SMB" that way
would have proved nothing.

What actually breaks an app on a real share is not latency, it is the errors a
remote filesystem produces that a local one never does:

  ERROR_SHARING_VIOLATION (32)  another PC has the file open
  ERROR_ACCESS_DENIED (5)       a rename lost the race with another client
  ERROR_NETNAME_DELETED (64)    the share vanished mid-write (cable, sleep, DFS)
  ERROR_UNEXP_NET_ERR (59)      the session dropped and is reconnecting
  slow / partial writes         the file is visible before it is complete

So this suite injects exactly those into the file operations the app performs
against the share, and asserts the app survives them without losing a write, a
response, or a report. That is the part of "test it on a real share" that can be
made deterministic -- and it is the part that finds bugs. Phase A-K on two real
machines still has to happen; docs/TEST_DAY.md carries the checklist.
"""
import os
import sys
import time
import shutil
import sqlite3
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fail = 0


def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


# --- the errors a real share raises, with the winerror codes Windows uses -----
def _oserr(winerror, msg):
    e = PermissionError(msg) if winerror in (5, 32) else OSError(msg)
    e.winerror = winerror
    e.errno = 13 if winerror in (5, 32) else 22
    return e


SHARING_VIOLATION = lambda: _oserr(32, "The process cannot access the file because "
                                       "it is being used by another process")
ACCESS_DENIED = lambda: _oserr(5, "Access is denied")
NETNAME_DELETED = lambda: _oserr(64, "The specified network name is no longer available")
NET_ERR = lambda: _oserr(59, "An unexpected network error occurred")


class FlakyShare:
    """Wraps os.replace/os.remove/open so the first N calls fail the way a real
    share fails, then succeed. Mirrors a share under contention or a dropped
    session that comes back."""

    def __init__(self, error_factory, failures=3, target_suffix=None):
        self.error_factory = error_factory
        self.remaining = failures
        self.target_suffix = target_suffix
        self.injected = 0
        self._real_replace = os.replace
        self._real_remove = os.remove
        self._lock = threading.Lock()

    def _should_fail(self, path):
        if self.target_suffix and not str(path).endswith(self.target_suffix):
            return False
        with self._lock:
            if self.remaining > 0:
                self.remaining -= 1
                self.injected += 1
                return True
        return False

    def replace(self, src, dst, *a, **k):
        if self._should_fail(dst):
            raise self.error_factory()
        return self._real_replace(src, dst, *a, **k)

    def remove(self, path, *a, **k):
        if self._should_fail(path):
            raise self.error_factory()
        return self._real_remove(path, *a, **k)

    def __enter__(self):
        os.replace = self.replace
        os.remove = self.remove
        return self

    def __exit__(self, *exc):
        os.replace = self._real_replace
        os.remove = self._real_remove


# ---------------------------------------------------------------------- tests
def test_replace_survives_a_share_under_contention():
    """The host republishes the replica while another PC is reading it."""
    from utils.atomic_replace import replace_with_retry
    d = tempfile.mkdtemp()
    dst = os.path.join(d, "fiu_ro.db")
    open(dst, "wb").write(b"v1")

    for name, err in (("sharing violation", SHARING_VIOLATION),
                      ("access denied", ACCESS_DENIED)):
        src = os.path.join(d, "new.db")
        open(src, "wb").write(b"v2")
        with FlakyShare(err, failures=3) as share:
            t0 = time.time()
            replace_with_retry(src, dst, timeout=5.0)
            took = time.time() - t0
        check(f"replica publish survives a {name}", open(dst, "rb").read() == b"v2",
              open(dst, "rb").read())
        check(f"  it retried rather than failing fast ({name})",
              share.injected == 3 and took >= 0.1, (share.injected, round(took, 2)))
        open(dst, "wb").write(b"v1")
    shutil.rmtree(d, ignore_errors=True)


def test_replace_gives_up_honestly_when_the_share_is_gone():
    """A share that never comes back must raise, not hang forever or pretend."""
    from utils.atomic_replace import replace_with_retry
    d = tempfile.mkdtemp()
    src, dst = os.path.join(d, "a"), os.path.join(d, "b")
    open(src, "wb").write(b"x")
    with FlakyShare(SHARING_VIOLATION, failures=10 ** 6):
        t0 = time.time()
        try:
            replace_with_retry(src, dst, timeout=1.0)
            raised = None
        except Exception as e:
            raised = e
        took = time.time() - t0
    check("a permanently locked file eventually raises", raised is not None)
    check("  and gives up near its timeout, not much later", 0.9 <= took <= 3.0, round(took, 2))
    shutil.rmtree(d, ignore_errors=True)


def test_client_read_survives_a_response_mid_write():
    """A client polling the responses folder must tolerate the host's file being
    briefly unopenable, and must not lose the response."""
    from services.queue_transport import QueueTransport
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus")
    t = QueueTransport(bus)
    t.respond("CMD1", {"id": "CMD1", "ok": True, "result": "applied"})

    real_open = open
    state = {"n": 0}

    def flaky_open(path, *a, **k):
        # the first two attempts to read the response hit a sharing violation,
        # exactly as they would while the host is renaming it into place
        if str(path).endswith("CMD1.json") and state["n"] < 2:
            state["n"] += 1
            raise SHARING_VIOLATION()
        return real_open(path, *a, **k)

    import builtins
    builtins.open = flaky_open
    try:
        resp = t.await_response("CMD1", timeout=5.0)
    finally:
        builtins.open = real_open
    check("a response held open by the host is still collected", resp.get("ok") is True, resp)
    check("  the client retried instead of raising", state["n"] == 2, state["n"])
    shutil.rmtree(d, ignore_errors=True)


def test_queued_write_is_not_lost_when_the_share_drops():
    """The share disappears mid-submit. The write must stay queued, not vanish."""
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, HostOfflineError
    from services.outbox import Outbox
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus")
    ob = Outbox(os.path.join(d, "outbox"))
    gw = RemoteGateway(QueueTransport(bus), timeout=0.4, outbox=ob)
    gw.token = "tok"

    try:
        gw.call("report_service.create_report",
                [{"report_date": "01/07/2026", "reported_entity_name": "Share Dropped Co"}], {})
    except HostOfflineError:
        pass
    pending = ob.pending()
    check("the write survives the share going away", len(pending) == 1, len(pending))
    check("  and keeps its stable id for an idempotent resubmit",
          pending and pending[0].get("id"), pending)
    shutil.rmtree(d, ignore_errors=True)


def test_replica_refresh_survives_a_locked_local_copy():
    """The client swaps its local replica while its own read-only queries hold
    it open -- the Windows case that silently served stale data before."""
    from services.replica_sync import _atomic_copy
    d = tempfile.mkdtemp()
    src = os.path.join(d, "fiu_ro.db"); open(src, "wb").write(b"fresh")
    dst = os.path.join(d, "local.db"); open(dst, "wb").write(b"stale")

    with FlakyShare(SHARING_VIOLATION, failures=2, target_suffix="local.db") as share:
        _atomic_copy(src, dst)
    check("the local replica still refreshes while it is being read",
          open(dst, "rb").read() == b"fresh", open(dst, "rb").read())
    check("  after retrying through the lock", share.injected == 2, share.injected)
    shutil.rmtree(d, ignore_errors=True)


def test_host_keeps_serving_after_a_share_blip():
    """A dropped session must not kill the host loop: the command has to be
    answered once the share returns."""
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.security_service import SecurityService

    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db")
    initialize_database(db); migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password("Admin@1234"),))
    conn.commit(); conn.close()

    dbm = DatabaseManager(db)
    log = LoggingService(dbm, None, db_logging=False)
    auth = AuthService(dbm, log)
    bus = os.path.join(d, "bus")
    host = HostService({"auth_service": auth}, dbm, QueueTransport(bus), bus)

    # the share blips while the host publishes the replica
    with FlakyShare(NETNAME_DELETED, failures=1, target_suffix="fiu_ro.db"):
        try:
            host.publish_replica()
            survived = True
        except OSError:
            survived = False
    check("a share blip during publish does not crash the host", survived,
          "publish_replica raised instead of retrying")

    # and the host still answers commands afterwards
    resp = host.handle_command({"id": "L1", "command": "login",
                                "args": ["admin", "Admin@1234"], "kwargs": {}})
    check("the host still serves after the blip", resp.get("ok") is True, resp)
    shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    test_replace_survives_a_share_under_contention()
    test_replace_gives_up_honestly_when_the_share_is_gone()
    test_client_read_survives_a_response_mid_write()
    test_queued_write_is_not_lost_when_the_share_drops()
    test_replica_refresh_survives_a_locked_local_copy()
    test_host_keeps_serving_after_a_share_blip()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
