"""Client-side durable queue for writes made while the host is down. Each
command is stored under its STABLE id, so re-submitting it is idempotent."""
import os
import time
import json
import uuid


class Outbox:
    def __init__(self, dir_path):
        self.dir = dir_path
        os.makedirs(self.dir, exist_ok=True)

    def add(self, command):
        # Filename is stable per id (so a token-refresh re-add overwrites rather
        # than duplicating). Ordering is carried by an internal _queued_at stamp
        # set once on first enqueue, so pending() replays oldest-first (causal
        # order: a create before its later update).
        cid = command["id"]
        if "_queued_at" not in command:
            command["_queued_at"] = int(time.time() * 1000)
        dest = os.path.join(self.dir, cid + ".json")
        tmp = os.path.join(self.dir, "." + uuid.uuid4().hex + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(command, f, default=str)
        os.replace(tmp, dest)

    def pending(self):
        out = []
        for name in (n for n in os.listdir(self.dir) if n.endswith(".json")):
            try:
                with open(os.path.join(self.dir, name), "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass
        out.sort(key=lambda c: c.get("_queued_at", 0))  # oldest first (causal order)
        return out

    def remove(self, command_id):
        try:
            os.remove(os.path.join(self.dir, command_id + ".json"))
        except OSError:
            pass
