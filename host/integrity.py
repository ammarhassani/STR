"""Startup self-heal: verify the local DB, restore the newest backup if broken."""
import os
import glob
import uuid
import shutil
import sqlite3


def _newest_backup(backups_dir):
    files = glob.glob(os.path.join(backups_dir, "*.db"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def check_and_restore(db_path, backups_dir, log=None):
    def _ok():
        try:
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute("PRAGMA integrity_check").fetchone()
                return bool(row) and row[0] == "ok"
            finally:
                conn.close()
        except sqlite3.DatabaseError:
            return False

    if _ok():
        return True, "ok"
    newest = _newest_backup(backups_dir)
    if not newest:
        if log: log.error("Integrity check FAILED and no backup to restore from")
        return False, "integrity failed, no backup"
    tmp = db_path + ".restore-" + uuid.uuid4().hex
    shutil.copyfile(newest, tmp)
    os.replace(tmp, db_path)
    # drop any stale WAL sidecars from the broken db
    for sfx in ("-wal", "-shm"):
        try:
            os.remove(db_path + sfx)
        except OSError:
            pass
    if log: log.warning(f"Integrity check failed; restored from {os.path.basename(newest)}")
    return True, f"restored from {os.path.basename(newest)}"
