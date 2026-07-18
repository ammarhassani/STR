"""Client-side transport: writes become commands sent to the host; reads
delegate to a local read-only service (the replica). One session token is
held per gateway."""
import uuid
from services import command_registry as cr


class RemoteError(Exception):
    pass


class HostOfflineError(RemoteError):
    pass


class RemoteGateway:
    def __init__(self, transport, timeout: float = 30.0, outbox=None):
        self.t = transport
        self.timeout = timeout
        self.token = None
        self.outbox = outbox

    def login(self, username, password):
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": "login", "args": [username, password], "kwargs": {}})
        resp = self.t.await_response(cid, timeout=self.timeout)
        if resp.get("ok"):
            self.token = resp["result"]["token"]
            return True, resp["result"].get("user"), "ok"
        return False, None, resp.get("error", "login failed")

    def complete_onboarding(self, username, full_name, password):
        """Pre-auth write (like login): the user self-registers name + password
        against the host. No session token yet."""
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": "complete_onboarding",
                       "args": [username, full_name, password], "kwargs": {}})
        try:
            resp = self.t.await_response(cid, timeout=self.timeout)
        except TimeoutError:
            return False, "Host offline — cannot complete registration right now."
        if resp.get("ok"):
            r = resp.get("result") or [False, "unknown error"]
            return bool(r[0]), (r[1] if len(r) > 1 else "")
        return False, resp.get("error", "registration failed")

    def call(self, command_name, args, kwargs):
        cid = uuid.uuid4().hex
        command = {"id": cid, "command": command_name,
                   "args": list(args), "kwargs": dict(kwargs), "token": self.token}
        self.t.submit(command)
        try:
            resp = self.t.await_response(cid, timeout=self.timeout)
        except TimeoutError:
            if self.outbox is not None:
                self.outbox.add(command)            # SAME id — idempotent resubmit
                raise HostOfflineError("Host offline — write queued, will sync when a host returns")
            raise
        if not resp.get("ok"):
            raise RemoteError(resp.get("error", "command failed"))
        return resp["result"]

    def drain(self):
        """Resubmit queued commands under the CURRENT token, keeping the same
        STABLE id so the host's ledger applies each exactly once. Remove a
        command only once the host actually applied it (ok=True). A host-level
        failure (ok=False: auth after a failover/session-timeout, or the host is
        down again) is retryable — keep it so no acknowledged write is ever lost,
        and stop draining for now (a later drain, after re-login, retries)."""
        if self.outbox is None:
            return (0, 0)
        sent = 0
        for command in self.outbox.pending():
            # The stored token may be stale (new host / expired session). Refresh
            # to the current token and persist it before resubmitting.
            command["token"] = self.token
            self.outbox.add(command)
            self.t.submit(command)
            try:
                resp = self.t.await_response(command["id"], timeout=self.timeout)
            except Exception:
                break  # host away / torn response — leave this + the rest queued
            if resp.get("ok"):
                self.outbox.remove(command["id"])
                sent += 1
            else:
                break  # not applied (auth/host failure) — keep for retry, never drop
        return (sent, len(self.outbox.pending()))


class RemoteServiceProxy:
    """Write methods -> gateway (host); everything else -> local read service."""
    def __init__(self, service_attr, local_service, gateway):
        self._attr = service_attr
        self._local = local_service
        self._gw = gateway

    def __getattr__(self, name):
        full = f"{self._attr}.{name}"
        if cr.is_write_command(full):
            def _remote(*args, **kwargs):
                return self._gw.call(full, args, kwargs)
            return _remote
        return getattr(self._local, name)
