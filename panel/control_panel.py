"""`--panel` operator CLI. Thin text menu over PanelController; all logic lives
in the controller so this file stays trivial + a Flet skin could replace it."""
import os
from config import Config
from panel.panel_controller import PanelController


def build_controller():
    Config.load()
    bus = Config.get_bus_dir()
    # host/panel operate on the real local DB; a client-only PC uses its replica copy
    local_db = Config.DATABASE_PATH or Config.get_client_replica_path()
    return PanelController(bus, local_db, Config.ensure_host_id())


def _fmt_status(st):
    hb = st["heartbeat"]
    who = f"{st['host_id']} (term {st['term']})" if hb else "— none —"
    online = "ONLINE" if st["host_online"] else "OFFLINE/STALE"
    return (f"Host: {online}  {who}\n"
            f"Queue: {st['queue_pending']} pending, {st['queue_processing']} processing\n"
            f"Replica version: {st['replica_version']}\n"
            f"Backups: {len(st['backups'])} (newest: {st['backups'][0] if st['backups'] else '—'})")


def run_action(controller, choice, config):
    if choice == "status":
        return _fmt_status(controller.status())
    if choice == "designate":
        return controller.designate_host(config)[1]
    if choice == "start":
        return controller.start_host()[1]
    if choice == "become":
        ok, msg, term = controller.become_host_now()
        return msg
    if choice == "integrity":
        return controller.run_integrity()[1]
    if choice == "backup":
        return controller.manual_backup()[1]
    if choice == "list":
        b = controller.list_backups()
        return "\n".join(b) if b else "(no backups)"
    if choice.startswith("restore:"):
        return controller.restore_backup(choice.split(":", 1)[1])[1]
    return f"unknown choice: {choice}"


MENU = """
STR Host Control Panel
  1) status        2) designate this PC as host   3) start host (this PC)
  4) become host now (promote)   5) integrity check   6) manual backup
  7) list backups  8) restore backup   q) quit
> """


def main():
    controller = build_controller()
    actions = {"1": "status", "2": "designate", "3": "start", "4": "become",
               "5": "integrity", "6": "backup", "7": "list"}
    while True:
        choice = input(MENU).strip().lower()
        if choice in ("q", "quit"):
            break
        if choice == "8":
            name = input("backup filename to restore: ").strip()
            print(run_action(controller, f"restore:{name}", Config))
        else:
            print(run_action(controller, actions.get(choice, choice), Config))


if __name__ == "__main__":
    main()
