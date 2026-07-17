"""Client-side host liveness sensor (reads the shared heartbeat)."""
from host.heartbeat import read_heartbeat, is_stale


class HostStatus:
    def __init__(self, bus_dir, stale_seconds=60):
        self.bus = bus_dir
        self.stale_seconds = stale_seconds

    def info(self):
        return read_heartbeat(self.bus)

    def online(self):
        return not is_stale(read_heartbeat(self.bus), self.stale_seconds)
