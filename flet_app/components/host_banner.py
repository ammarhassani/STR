"""Host-down banner: read-only + queued-writes notice, shown when the client
cannot see a live host. Hidden when the host is online."""
import flet as ft


def build_host_banner(app_state):
    text = ft.Text("", size=13, color=ft.Colors.WHITE)
    container = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.CLOUD_OFF, color=ft.Colors.WHITE, size=18), text], spacing=8),
        bgcolor=ft.Colors.ORANGE_800, padding=ft.padding.symmetric(8, 12),
        visible=False,
    )

    def refresh():
        online = True
        try:
            online = app_state.host_status.online() if app_state.host_status else True
        except Exception:
            online = True
        if online:
            container.visible = False
        else:
            n = app_state.pending_writes()
            text.value = (f"Host offline — read-only. New entries are queued and will "
                          f"sync when the host returns ({n} pending).")
            container.visible = True

    container.refresh = refresh
    refresh()
    return container
