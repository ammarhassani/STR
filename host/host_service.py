"""Single-writer host: consumes commands, runs the real services against the
local DB in one transaction each, enforces idempotency + host-side sessions,
publishes a read-only replica. Single-threaded by design."""
import os
import json
import time
import uuid
import sqlite3
import socket
from host.lease import read_lease
from host import heartbeat as hb
from utils.atomic_replace import replace_with_retry

SESSION_TIMEOUT_SECONDS = 1800
BACKUP_EVERY_SECONDS = 300
BACKUP_KEEP = 20


class HostService:
    def __init__(self, services: dict, db_manager, transport, bus_dir: str, host_id: str = None):
        self.services = services
        self.db = db_manager
        self.t = transport
        self.bus = bus_dir
        self.auth = services["auth_service"]
        self._sessions = {}  # token -> {"user_id","username","role","last_seen"}
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        # A promoted host MUST serve under the SAME host_id it wrote to the
        # heartbeat during become_host (else it could read its own heartbeat as
        # a rival and refuse to start / mis-tiebreak). Callers that fail over
        # pass that host_id in; standalone hosts get a stable-per-process one.
        self.host_id = host_id or f"{self.hostname}-{uuid.uuid4().hex[:8]}"
        _hid, self.term = read_lease(self.db)   # term this host serves under
        self._db_version = 0

    # ---- sessions ----
    def login(self, username, password):
        ok, user, msg = self.auth.authenticate(username, password)
        if not ok:
            return False, None, msg, None
        token = uuid.uuid4().hex
        self._sessions[token] = {"user_id": user["user_id"], "username": user["username"],
                                 "role": user["role"], "last_seen": time.time()}
        return True, token, "ok", user

    def _resolve(self, token):
        s = self._sessions.get(token)
        if not s:
            return None
        if time.time() - s["last_seen"] > SESSION_TIMEOUT_SECONDS:
            self._sessions.pop(token, None)
            return None
        s["last_seen"] = time.time()
        # rebuild the auth context this command runs under
        return {"user_id": s["user_id"], "username": s["username"], "role": s["role"]}

    # ---- command handling (pure, testable) ----
    def handle_command(self, cmd: dict) -> dict:
        cid = cmd["id"]
        # idempotency: re-emit stored response if already applied
        prior = self.db.execute_with_retry(
            "SELECT response_json FROM applied_commands WHERE command_id = ?", (cid,))
        if prior:
            return json.loads(prior[0][0])

        name = cmd.get("command")
        try:
            if name == "login":
                ok, token, msg, user = self.login(cmd["args"][0], cmd["args"][1])
                resp = {"id": cid, "ok": ok,
                        "result": {"token": token, "message": msg,
                                   "user": {"user_id": user["user_id"], "username": user["username"],
                                            "full_name": user.get("full_name"), "role": user["role"],
                                            "language": user.get("language", "en")}}} if ok \
                    else {"id": cid, "ok": False, "error": msg}
            elif name == "complete_onboarding":
                # pre-auth write (two-way handshake #1): the user self-registers
                # their name + password. No token; the method itself only allows
                # a still-pending user, so it can't hijack a registered account.
                ok, msg = self.auth.complete_onboarding(*cmd.get("args", []))
                resp = {"id": cid, "ok": True, "result": [ok, msg]}
            else:
                user = self._resolve(cmd.get("token"))
                if not user:
                    resp = {"id": cid, "ok": False, "error": "Not authenticated (re-login)"}
                else:
                    from services import command_registry as cr
                    # set the auth context for THIS command, then dispatch
                    self.auth.current_user = user
                    result = cr.dispatch(self.services, name, cmd.get("args", []), cmd.get("kwargs", {}))
                    resp = {"id": cid, "ok": True, "result": result}
        except Exception as e:
            resp = {"id": cid, "ok": False, "error": f"{type(e).__name__}: {e}"}

        # record applied ONLY when the command was actually dispatched (ok=True,
        # whether it returned success or a business (False,msg) rejection). A
        # host-level failure (ok=False: not-authenticated, dispatch exception →
        # txn rolled back) means the command did NOT apply, so it must stay
        # retryable — recording it would poison the stable id and make a later
        # resubmit (after re-login / session-timeout / failover) replay the
        # failure instead of applying the write. Login excluded (tokens one-shot).
        if name not in ("login", "complete_onboarding") and resp.get("ok"):
            try:
                self.db.execute_with_retry(
                    "INSERT OR IGNORE INTO applied_commands (command_id, response_json) VALUES (?, ?)",
                    (cid, json.dumps(resp, default=str)))
            except Exception as e:
                # safety-critical: if the idempotency ledger write fails, a
                # post-restart replay could re-run this command. Never silent.
                print(f"[HOST][WARN] failed to record applied_command {cid}: {e}")
        return resp

    # ---- replica ----
    def publish_replica(self):
        dest = os.path.join(self.bus, "replica", "fiu_ro.db")
        tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".db")
        src = sqlite3.connect(self.db.db_path)
        dst = sqlite3.connect(tmp)
        try:
            with dst:
                src.backup(dst)  # consistent snapshot
            # Publish a NON-WAL file: journal_mode lives in the SQLite file
            # header and src.backup() copies it, so without this the replica is
            # WAL-tagged and read-only clients still spawn -wal/-shm sidecars
            # (which get stranded when the refresher swaps the file underneath).
            dst.execute("PRAGMA journal_mode=DELETE")
        finally:
            dst.close(); src.close()
        replace_with_retry(tmp, dest)
        version = int(time.time() * 1000)
        vtmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".ver")
        with open(vtmp, "w", encoding="utf-8") as f:
            f.write(str(version))
        replace_with_retry(vtmp, os.path.join(self.bus, "replica", "version.txt"))
        self._db_version = version

    def _beat(self):
        hb.write_heartbeat(self.bus, self.host_id, self.term, self._db_version, self.pid, self.hostname)

    def should_step_down(self) -> bool:
        beat = hb.read_heartbeat(self.bus)
        if not beat:
            return False
        if beat.get("host_id") == self.host_id:
            return False  # our own heartbeat is never a rival
        other_term = beat.get("term", 0)
        if other_term > self.term:
            return True
        # Equal-term collision — only possible if TWO operators promote two
        # backups simultaneously, which is OUTSIDE the operational model (failover
        # is single-operator manual confirmed; the org has no lock server and SMB
        # byte-range locking is exactly what this architecture avoids, so hard
        # mutual exclusion is not achievable here). Best-effort tiebreak: the
        # higher host_id wins. This is CONVERGENT, not instantaneous — the loser
        # retires as soon as its loop reads the winner's heartbeat (the step-down
        # check runs before every beat, so it stops clobbering once it sees the
        # winner). Worst case is a bounded (~1 poll) two-writer window that
        # reconciles (each host writes only its own local DB; the queue is
        # idempotent), never corruption.
        return other_term == self.term and beat.get("host_id", "") > self.host_id

    # ---- startup / self-heal ----
    def startup(self):
        from host.integrity import check_and_restore
        from host.sleep_guard import prevent_sleep
        backups_dir = os.path.join(self.bus, "backups")
        ok, msg = check_and_restore(self.db.db_path, backups_dir)
        print(f"[HOST] integrity: {msg}")
        if not ok:
            # Corruption-fatal app: never serve (or publish) an unrecoverable DB.
            raise RuntimeError(f"[HOST] DB integrity unrecoverable, refusing to serve: {msg}")
        prevent_sleep()
        self.publish_replica()
        self._beat()
        self._last_backup = 0.0

    def _maybe_backup(self):
        now = time.time()
        if now - getattr(self, "_last_backup", 0.0) < BACKUP_EVERY_SECONDS:
            return
        self._last_backup = now
        try:
            backups_dir = os.path.join(self.bus, "backups")
            dest = os.path.join(backups_dir, f"fiu_{int(now * 1000)}.db")
            tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".bak")
            src = sqlite3.connect(self.db.db_path); dst = sqlite3.connect(tmp)
            try:
                with dst:
                    src.backup(dst)
                dst.execute("PRAGMA journal_mode=DELETE")
            finally:
                dst.close(); src.close()
            os.replace(tmp, dest)
            # prune to newest BACKUP_KEEP
            import glob
            files = sorted(glob.glob(os.path.join(backups_dir, "*.db")), key=os.path.getmtime, reverse=True)
            for old in files[BACKUP_KEEP:]:
                try: os.remove(old)
                except OSError: pass
        except Exception as e:
            print(f"[HOST][WARN] backup failed: {e}")

    # ---- loop ----
    def run_once(self) -> bool:
        cmd = self.t.claim_next()
        if cmd is None:
            return False
        resp = self.handle_command(cmd)
        # Publish the replica BEFORE the client ACK: the client only sees success
        # once the write is in the replica a failover would adopt, so a host
        # crash in this window can never lose an acknowledged write.
        self.publish_replica()
        self._beat()
        self.t.respond(cmd["id"], resp)
        self.t.complete(cmd["id"])
        return True

    def serve_forever(self, poll: float = 0.1):
        # Retire BEFORE publishing/serving if a newer term already holds the
        # lease — a restarted old host must not clobber the current heartbeat or
        # apply commands against its stale local DB.
        if self.should_step_down():
            print(f"[HOST] not starting: a newer term holds the lease (mine={self.term})")
            return
        self.startup()
        while True:
            if self.should_step_down():
                print(f"[HOST] stepping down: a newer term holds the lease (mine={self.term})")
                return
            try:
                if not self.run_once():
                    self._beat()
                    self._maybe_backup()
                    time.sleep(poll)
                else:
                    self._maybe_backup()
            except Exception as e:
                print(f"[HOST][ERROR] run_once failed, continuing: {e}")
                time.sleep(poll)
