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
        from i18n import t
        n = app_state.pending_writes()
        if not online:
            text.value = t("hostbanner.offline", n=n)
            container.bgcolor = ft.Colors.ORANGE_800
            container.visible = True
        elif n:
            # Host is back but the writes are still queued — they carry the token
            # of the session that died with the old host, so only a fresh login
            # can drain them. Saying nothing here reads as "everything synced".
            text.value = t("hostbanner.stuck", n=n)
            container.bgcolor = ft.Colors.AMBER_900
            container.visible = True
        else:
            container.visible = False

    container.refresh = refresh
    refresh()
    return container
