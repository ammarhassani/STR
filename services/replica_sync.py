"""Client-side replica sync: copy the host's published read-only replica to a
local file and keep it fresh. The client reads its LOCAL copy so the shared
file (which the host republishes via os.replace) is never read mid-swap."""
import os
import time
import uuid
import shutil
import threading

from utils.atomic_replace import replace_with_retry


def _paths(bus_dir):
    rep = os.path.join(bus_dir, "replica", "fiu_ro.db")
    ver = os.path.join(bus_dir, "replica", "version.txt")
    return rep, ver


def _atomic_copy(src, dst):
    """Copy src -> dst atomically (temp in dst's dir, then os.replace)."""
    tmp = dst + ".tmp-" + uuid.uuid4().hex
    shutil.copyfile(src, tmp)
    # On Windows the swap fails while any read-only query holds the local
    # replica open, and the refresher swallows the error -> silently stale data.
    replace_with_retry(tmp, dst)
    # Best-effort: a read-only client never creates WAL sidecars itself, but
    # clean up any stale ones left behind so a swapped-in file is never
    # shadowed by an old -wal/-shm from a previous (writable) open.
    for sfx in ("-wal", "-shm"):
        try:
            os.remove(dst + sfx)
        except OSError:
            pass


def bootstrap_replica(bus_dir, local_path, timeout=30.0):
    """Wait (up to timeout) for the host replica to exist, copy it locally."""
    rep, _ = _paths(bus_dir)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(rep):
            try:
                _atomic_copy(rep, local_path)
                return True
            except Exception:
                pass  # mid-republish on the host; retry
        time.sleep(0.2)
    return False


def _read_version(ver):
    try:
        with open(ver, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


class ReplicaRefresher:
    """Daemon thread: when version.txt changes, re-copy the replica locally."""
    def __init__(self, bus_dir, local_path, poll=2.0, on_update=None):
        self.rep, self.ver = _paths(bus_dir)
        self.local = local_path
        self.poll = poll
        self.on_update = on_update
        self._last = _read_version(self.ver)
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        while not self._stop.is_set():
            v = _read_version(self.ver)
            if v is not None and v != self._last:
                try:
                    _atomic_copy(self.rep, self.local)
                    self._last = v
                    if self.on_update:
                        self.on_update()
                except Exception:
                    pass  # share briefly unavailable / mid-swap; retry next poll
            self._stop.wait(self.poll)
