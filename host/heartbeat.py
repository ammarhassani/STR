"""Host liveness + term broadcast on the share. Clients and other hosts read
this to sense host-down and to detect a higher-term promotion."""
import os
import json
import time
import uuid


def write_heartbeat(bus_dir, host_id, term, db_version, pid, hostname):
    hb = {"host_id": host_id, "term": term, "db_version": db_version,
          "pid": pid, "hostname": hostname, "epoch_ms": int(time.time() * 1000)}
    dest = os.path.join(bus_dir, "host", "heartbeat.json")
    tmp = os.path.join(bus_dir, ".tmp", uuid.uuid4().hex + ".hb")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hb, f)
    os.replace(tmp, dest)


def read_heartbeat(bus_dir):
    path = os.path.join(bus_dir, "host", "heartbeat.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def is_stale(hb, stale_seconds=60):
    if not hb:
        return True
    return (time.time() * 1000 - hb.get("epoch_ms", 0)) > stale_seconds * 1000
