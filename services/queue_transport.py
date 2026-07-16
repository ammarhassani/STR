"""Atomic folder-queue transport between clients and the single host.
Every placed file is written to .tmp then renamed into place, so readers
never see a partial file. Command filenames are globally unique."""
import os
import json
import time
import uuid

SUBDIRS = ["queue/pending", "queue/processing", "queue/done",
           "responses", "replica", "host", "backups", ".tmp"]


class QueueTransport:
    def __init__(self, bus_dir: str):
        self.bus = bus_dir
        for d in SUBDIRS:
            os.makedirs(os.path.join(bus_dir, d), exist_ok=True)

    def _p(self, *parts):
        return os.path.join(self.bus, *parts)

    def _atomic_write(self, dest_path: str, data: dict):
        tmp = self._p(".tmp", uuid.uuid4().hex)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        os.replace(tmp, dest_path)  # atomic within the same filesystem

    # ---- client side ----
    def submit(self, command: dict) -> str:
        cid = command["id"]
        # sortable, unique: <ms>_<id>.json
        name = f"{int(time.time() * 1000):013d}_{cid}.json"
        self._atomic_write(self._p("queue", "pending", name), command)
        return cid

    def await_response(self, command_id: str, timeout: float = 30.0, poll: float = 0.05) -> dict:
        path = self._p("responses", f"{command_id}.json")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        resp = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    time.sleep(poll); continue  # writer mid-rename; retry
                try:
                    os.remove(path)
                except OSError:
                    pass
                return resp
            time.sleep(poll)
        raise TimeoutError(f"No response for {command_id} within {timeout}s")

    # ---- host side ----
    def claim_next(self):
        pend = self._p("queue", "pending")
        names = sorted(n for n in os.listdir(pend) if n.endswith(".json"))
        for name in names:
            src = os.path.join(pend, name)
            dst = self._p("queue", "processing", name)
            try:
                os.replace(src, dst)  # atomic claim
            except (FileNotFoundError, OSError):
                continue  # another pass grabbed it / mid-write; skip
            try:
                with open(dst, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        return None

    def respond(self, command_id: str, response: dict) -> None:
        self._atomic_write(self._p("responses", f"{command_id}.json"), response)

    def complete(self, command_id: str) -> None:
        proc = self._p("queue", "processing")
        for name in os.listdir(proc):
            if name.endswith(f"_{command_id}.json"):
                try:
                    os.replace(os.path.join(proc, name), self._p("queue", "done", name))
                except OSError:
                    pass
                return
