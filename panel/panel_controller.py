"""Operator-plane logic (UI-free, fully testable). Reads the shared heartbeat/
queue/backups and drives the Phase-3a primitives."""
import os
import sys
import glob
import uuid
import shutil
import sqlite3
import subprocess

from host.heartbeat import read_heartbeat, is_stale
from host.integrity import check_and_restore
from host.failover import become_host


class PanelController:
    def __init__(self, bus_dir, local_db_path, host_id):
        self.bus = bus_dir
        self.db_path = local_db_path
        self.host_id = host_id
        self.backups_dir = os.path.join(bus_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

    def status(self):
        hb = read_heartbeat(self.bus)
        pend = os.path.join(self.bus, "queue", "pending")
        proc = os.path.join(self.bus, "queue", "processing")
        ver_path = os.path.join(self.bus, "replica", "version.txt")
        version = None
        try:
            with open(ver_path) as f:
                version = f.read().strip()
        except OSError:
            pass
        return {
            "heartbeat": hb,
            "host_online": not is_stale(hb),
            "host_id": hb.get("host_id") if hb else None,
            "term": hb.get("term", 0) if hb else 0,
            "queue_pending": len([n for n in os.listdir(pend) if n.endswith(".json")]) if os.path.isdir(pend) else 0,
            "queue_processing": len([n for n in os.listdir(proc) if n.endswith(".json")]) if os.path.isdir(proc) else 0,
            "replica_version": version,
            "backups": self.list_backups(),
        }

    def designate_host(self, config):
        config.MODE = "host"
        config.ensure_host_id()
        config.save()
        return True, f"This PC designated as host (mode=host, id={config.HOST_ID})"

    def start_host(self, spawn=subprocess.Popen):
        main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "flet_app", "main.py")
        cmd = [sys.executable, main_py, "--host"]
        try:
            p = spawn(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"host started (pid {getattr(p, 'pid', '?')})"
        except Exception as e:
            return False, f"could not start host: {e}"

    def become_host_now(self, stale_seconds=60, force=False):
        return become_host(self.bus, self.db_path, self.host_id, stale_seconds, force)

    def run_integrity(self):
        return check_and_restore(self.db_path, self.backups_dir)

    def manual_backup(self):
        try:
            import time
            dest = os.path.join(self.backups_dir, f"fiu_{int(time.time() * 1000)}.db")
            tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".bak")
            src = sqlite3.connect(self.db_path); dst = sqlite3.connect(tmp)
            try:
                with dst:
                    src.backup(dst)
                dst.execute("PRAGMA journal_mode=DELETE")
            finally:
                dst.close(); src.close()
            os.replace(tmp, dest)
            return True, f"backup written: {os.path.basename(dest)}"
        except Exception as e:
            return False, f"backup failed: {e}"

    def list_backups(self):
        files = sorted(glob.glob(os.path.join(self.backups_dir, "*.db")), key=os.path.getmtime, reverse=True)
        return [os.path.basename(f) for f in files]

    def restore_backup(self, name):
        src = os.path.join(self.backups_dir, name)
        if not os.path.exists(src):
            return False, f"backup not found: {name}"
        tmp = self.db_path + ".restore-" + uuid.uuid4().hex
        shutil.copyfile(src, tmp)
        os.replace(tmp, self.db_path)
        for sfx in ("-wal", "-shm"):
            try:
                os.remove(self.db_path + sfx)
            except OSError:
                pass
        return True, f"restored from {name}"
