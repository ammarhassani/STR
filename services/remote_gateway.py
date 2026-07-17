"""Client-side transport: writes become commands sent to the host; reads
delegate to a local read-only service (the replica). One session token is
held per gateway."""
import uuid
from services import command_registry as cr


class RemoteError(Exception):
    pass


class RemoteGateway:
    def __init__(self, transport, timeout: float = 30.0):
        self.t = transport
        self.timeout = timeout
        self.token = None

    def login(self, username, password):
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": "login", "args": [username, password], "kwargs": {}})
        resp = self.t.await_response(cid, timeout=self.timeout)
        if resp.get("ok"):
            self.token = resp["result"]["token"]
            return True, resp["result"].get("user"), "ok"
        return False, None, resp.get("error", "login failed")

    def call(self, command_name, args, kwargs):
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": command_name,
                       "args": list(args), "kwargs": dict(kwargs), "token": self.token})
        resp = self.t.await_response(cid, timeout=self.timeout)
        if not resp.get("ok"):
            raise RemoteError(resp.get("error", "command failed"))
        return resp["result"]


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
