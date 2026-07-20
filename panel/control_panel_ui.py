"""The operator control panel, as a window instead of a text menu.

Design rule for this screen: an operator under pressure should never have to
read a paragraph or remember a previous step. So it is one column of big
labelled buttons grouped by intent, a plain-English health line at the top that
says what is WRONG rather than what is true, and every action reports its result
inline instead of in a console the operator cannot see.

Everything here is a thin skin over PanelController. No logic lives in this file.
"""
import os
import threading

import flet as ft

from config import Config
from panel.panel_controller import PanelController

# Deliberately not the app's theme module: this window must render even when the
# app itself is misconfigured, which is exactly when an operator opens it.
OK_COLOR = "#2f855a"
BAD_COLOR = "#c53030"
WARN_COLOR = "#b7791f"
INK = "#1a202c"
MUTED = "#4a5568"


def _ago(seconds):
    """'15 hours ago', not '54065 seconds ago'.

    An operator reading this is trying to answer "is that bad?" in one glance.
    Raw seconds forces mental arithmetic at exactly the wrong moment.
    """
    if seconds is None:
        return "never"
    s = int(seconds)
    if s < 60:
        return f"{s} seconds ago"
    if s < 3600:
        m = s // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if s < 86400:
        h = s // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = s // 86400
    return f"{d} day{'s' if d != 1 else ''} ago"


def _controller():
    Config.load()
    bus = Config.get_bus_dir()
    local_db = Config.DATABASE_PATH or Config.get_client_replica_path()
    return PanelController(bus, local_db, Config.ensure_host_id())


def build_panel(page: ft.Page):
    page.title = "STR Control Panel"
    page.window.width = 780
    page.window.height = 860
    page.bgcolor = "#f7f8fa"
    page.padding = 0

    controller = _controller()
    log = ft.Text("", size=13, selectable=True, color=INK)
    health_box = ft.Column(spacing=4)

    def say(msg, good=True):
        log.value = msg
        log.color = OK_COLOR if good else BAD_COLOR
        page.update()

    def run(fn, *a, **kw):
        """Run an action off the UI thread; a share that has gone away can block
        for many seconds and a frozen window reads as a crashed app."""
        def worker():
            try:
                ok, msg = fn(*a, **kw)
                say(msg, ok)
            except Exception as e:
                say(f"{type(e).__name__}: {e}", False)
            refresh_health()
        threading.Thread(target=worker, daemon=True).start()

    def refresh_health(_=None):
        try:
            h = controller.health(share_path=Config.SHARE_PATH)
        except Exception as e:
            health_box.controls = [ft.Text(f"Could not read status: {e}",
                                           color=BAD_COLOR, size=14)]
            page.update()
            return

        rows = []
        if h["healthy"]:
            rows.append(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=OK_COLOR),
                ft.Text("Everything is working.", size=16,
                        weight=ft.FontWeight.BOLD, color=OK_COLOR)]))
        else:
            rows.append(ft.Row([
                ft.Icon(ft.Icons.ERROR, color=BAD_COLOR),
                ft.Text("Needs attention", size=16,
                        weight=ft.FontWeight.BOLD, color=BAD_COLOR)]))
            for p in h["problems"]:
                rows.append(ft.Text("• " + p, size=13, color=BAD_COLOR))

        def fact(label, value):
            return ft.Row([ft.Text(f"{label}:", size=12, color=MUTED, width=150),
                           ft.Text(str(value), size=12, color=INK)])

        age = h["heartbeat_age_seconds"]
        rows += [
            ft.Divider(height=12),
            fact("This PC", h["this_pc"]),
            fact("Host PC", h["host_pc"] or "— none —"),
            fact("Host", "running" if h["host_online"] else "NOT running"),
            fact("Host last seen", _ago(age)),
            fact("Waiting to save", h["queue_pending"]),
            fact("Data copy updated",
                 _ago(h["replica_age_seconds"]) if h["replica_age_seconds"] is not None
                 else "no copy yet"),
            fact("Shared folder", h["share_message"]),
            fact("Backups", len(h["backups"])),
        ]
        health_box.controls = rows
        page.update()

    def big_button(text, icon, on_click, color="#0d7377"):
        return ft.Container(
            content=ft.Row([ft.Icon(icon, color="white", size=20),
                            ft.Text(text, color="white", size=14,
                                    weight=ft.FontWeight.BOLD)],
                           spacing=10),
            bgcolor=color, padding=ft.padding.symmetric(14, 18),
            border_radius=4, on_click=on_click, ink=False, width=330,
        )

    def section(title, buttons):
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=MUTED),
                ft.Row(buttons, wrap=True, spacing=10, run_spacing=10),
            ], spacing=8),
            padding=ft.padding.only(bottom=18),
        )

    # ---- the client kit: the deployment story, reduced to one button ----
    share_field = ft.TextField(label="Shared folder (UNC path)",
                               value=Config.SHARE_PATH or "", width=430, dense=True)
    dest_field = ft.TextField(label="Build the client folder here",
                              value=os.path.join(os.path.expanduser("~"),
                                                 "Desktop", "STR_Client"),
                              width=430, dense=True)

    def do_kit(_):
        exe = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "dist", "FIU_System.exe")
        run(controller.make_client_kit, dest_field.value, share_field.value,
            exe if os.path.isfile(exe) else None)

    def do_designate(_):
        Config.SHARE_PATH = share_field.value or Config.SHARE_PATH
        run(controller.designate_host, Config)

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.DASHBOARD, color="#0d7377", size=26),
                        ft.Text("STR Control Panel", size=22,
                                weight=ft.FontWeight.BOLD, color=INK)], spacing=10),
                ft.Container(content=health_box, bgcolor="white", padding=16,
                             border_radius=4, border=ft.border.all(1, "#e2e8f0")),
                ft.Container(height=8),

                section("RUN", [
                    big_button("Start host on this PC", ft.Icons.PLAY_ARROW,
                               lambda _: run(controller.start_host)),
                    big_button("Stop host", ft.Icons.STOP,
                               lambda _: run(controller.stop_host), BAD_COLOR),
                    big_button("Open the app", ft.Icons.LAUNCH,
                               lambda _: run(controller.start_client), "#4a5568"),
                ]),

                section("SET UP THIS PC", [
                    big_button("Make this PC the host", ft.Icons.DNS, do_designate),
                    big_button("Start automatically at login", ft.Icons.BOLT,
                               lambda _: run(controller.install_startup_shortcut),
                               "#4a5568"),
                    big_button("Check the shared folder", ft.Icons.FOLDER_SHARED,
                               lambda _: run(controller.check_share, share_field.value),
                               "#4a5568"),
                ]),

                section("DEPLOY TO A CLIENT PC", [share_field, dest_field,
                                                 big_button("Build client folder",
                                                            ft.Icons.INVENTORY_2, do_kit)]),

                section("DATA", [
                    big_button("Back up now", ft.Icons.BACKUP,
                               lambda _: run(controller.manual_backup)),
                    big_button("Check data is healthy", ft.Icons.HEALTH_AND_SAFETY,
                               lambda _: run(controller.run_integrity), "#4a5568"),
                    big_button("Refresh", ft.Icons.REFRESH, refresh_health, "#4a5568"),
                ]),

                ft.Container(content=log, bgcolor="white", padding=14,
                             border_radius=4, border=ft.border.all(1, "#e2e8f0")),
            ], scroll=ft.ScrollMode.AUTO, spacing=10),
            padding=22, expand=True,
        )
    )
    refresh_health()


def main():
    ft.app(target=build_panel)


if __name__ == "__main__":
    main()
