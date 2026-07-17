"""Manual confirmed promotion — no election race. A designated backup adopts
the newest replica, re-queues in-flight commands, and bumps the term so the
old host (if it wakes) steps down."""
import os
import uuid
import shutil

from host.heartbeat import read_heartbeat, is_stale, write_heartbeat
from host.lease import bump_lease


def _atomic_copy(src, dst):
    tmp = dst + ".tmp-" + uuid.uuid4().hex
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    for sfx in ("-wal", "-shm"):
        try:
            os.remove(dst + sfx)
        except OSError:
            pass


def become_host(bus_dir, local_db_path, host_id, stale_seconds=60, force=False):
    hb = read_heartbeat(bus_dir)
    if hb and not is_stale(hb, stale_seconds) and not force:
        return False, f"A live host holds the lease (term {hb.get('term', 0)})", None

    replica = os.path.join(bus_dir, "replica", "fiu_ro.db")
    if not os.path.exists(replica):
        return False, "no replica to adopt", None
    _atomic_copy(replica, local_db_path)

    # re-queue anything the dead host had claimed but not completed
    proc = os.path.join(bus_dir, "queue", "processing")
    pend = os.path.join(bus_dir, "queue", "pending")
    orphaned = []
    for name in list(os.listdir(proc)):
        if name.endswith(".json"):
            try:
                os.replace(os.path.join(proc, name), os.path.join(pend, name))
            except OSError as e:
                # left in processing/: the new host won't re-claim it, but the
                # client's outbox resubmits (same id, idempotent). Surface it.
                orphaned.append(name)
                print(f"[FAILOVER][WARN] could not re-queue in-flight command {name}: {e}")
    if orphaned:
        print(f"[FAILOVER][WARN] {len(orphaned)} in-flight command(s) left in processing/ "
              f"(clients will resubmit via outbox)")

    from database.db_manager import DatabaseManager
    dbm = DatabaseManager(local_db_path)
    prior_term = hb.get("term", 0) if hb else 0
    new_term = bump_lease(dbm, host_id, min_term=prior_term)

    import socket
    write_heartbeat(bus_dir, host_id, new_term, 0, os.getpid(), socket.gethostname())
    return True, f"promoted to host (term {new_term})", new_term
