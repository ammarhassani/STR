"""Single-writer host: consumes commands, runs the real services against the
local DB in one transaction each, enforces idempotency + host-side sessions,
publishes a read-only replica. Single-threaded by design."""
import os
import json
import time
import uuid
import sqlite3


class HostService:
    def __init__(self, services: dict, db_manager, transport, bus_dir: str):
        self.services = services
        self.db = db_manager
        self.t = transport
        self.bus = bus_dir
        self.auth = services["auth_service"]
        self._sessions = {}  # token -> {"user_id","username","role","last_seen"}

    # ---- sessions ----
    def login(self, username, password):
        ok, user, msg = self.auth.authenticate(username, password)
        if not ok:
            return False, None, msg
        token = uuid.uuid4().hex
        self._sessions[token] = {"user_id": user["user_id"], "username": user["username"],
                                 "role": user["role"], "last_seen": time.time()}
        return True, token, "ok"

    def _resolve(self, token):
        s = self._sessions.get(token)
        if not s:
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
                ok, token, msg = self.login(cmd["args"][0], cmd["args"][1])
                resp = {"id": cid, "ok": ok, "result": {"token": token, "message": msg}} if ok \
                    else {"id": cid, "ok": False, "error": msg}
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

        # record applied (login excluded from idempotency ledger — tokens are one-shot anyway)
        if name != "login":
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
        finally:
            dst.close(); src.close()
        os.replace(tmp, dest)
        with open(os.path.join(self.bus, "replica", "version.txt"), "w") as f:
            f.write(str(int(time.time() * 1000)))

    # ---- loop ----
    def run_once(self) -> bool:
        cmd = self.t.claim_next()
        if cmd is None:
            return False
        resp = self.handle_command(cmd)
        self.t.respond(cmd["id"], resp)
        self.t.complete(cmd["id"])
        self.publish_replica()
        return True

    def serve_forever(self, poll: float = 0.1):
        self.publish_replica()
        while True:
            try:
                if not self.run_once():
                    time.sleep(poll)
            except Exception as e:
                print(f"[HOST][ERROR] run_once failed, continuing: {e}")
                time.sleep(poll)
