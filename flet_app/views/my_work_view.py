"""My Work — an agent/supervisor's personal queue of their own reports, grouped
into lanes so returned/reworked reports (and the reviewer's message) are never
lost. Clicking a report opens it for editing.
"""
import flet as ft
from typing import Any

from theme.theme_manager import theme_manager
from dialogs.report_dialog import show_report_dialog
from i18n import t


# lane order matters: Rework first (the thing an agent must act on), then Drafts,
# then in-flight, then done.
def _lanes(colors):
    return [
        ('rework', t("mywork.lane.rework"), ft.Icons.REPLAY, colors['danger']),
        ('draft', t("mywork.lane.draft"), ft.Icons.EDIT_NOTE, colors['text_secondary']),
        ('pending_approval', t("mywork.lane.pending"), ft.Icons.HOURGLASS_TOP, colors['warning']),
        ('approved', t("mywork.lane.approved"), ft.Icons.CHECK_CIRCLE, colors['success']),
    ]


def build_my_work_view(page: ft.Page, app_state: Any) -> ft.Control:
    colors = theme_manager.get_colors()
    reports_svc = app_state.report_service
    approval_svc = app_state.approval_service
    user = app_state.current_user or {}
    username = user.get('username', '')

    body = ft.Column(spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    def open_report(report_id):
        rep = reports_svc.get_report(report_id)
        if rep:
            show_report_dialog(page, app_state, report_data=rep, on_save=refresh)

    def review_banner(report_id, color):
        rc = approval_svc.get_review_comment(report_id) if approval_svc else None
        if not rc:
            return None
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=14, color=color),
                    ft.Text(f"{rc.get('reviewer') or t('common.reviewer')}: {rc.get('comment')}",
                            size=12, color=color, italic=True, expand=True, selectable=True),
                ],
                spacing=6,
            ),
            bgcolor=ft.Colors.with_opacity(0.08, color),
            padding=ft.padding.symmetric(6, 10), border_radius=4,
        )

    def report_card(rep, status, color):
        rid = rep['report_id']
        rows = [
            ft.Row(
                controls=[
                    ft.Text(rep.get('report_number') or '—', size=13, weight=ft.FontWeight.W_600,
                            color=colors['text_primary']),
                    ft.Text(rep.get('reported_entity_name') or t('common.no_entity'), size=13,
                            color=colors['text_secondary'], expand=True),
                    ft.Text(rep.get('report_date') or '', size=11, color=colors['text_muted']),
                ],
                spacing=10,
            )
        ]
        if status == 'rework':
            banner = review_banner(rid, color)
            if banner:
                rows.append(banner)
        return ft.Container(
            content=ft.Column(rows, spacing=6, tight=True),
            padding=12, border_radius=6,
            border=ft.border.all(1, colors['border']),
            bgcolor=colors['bg_secondary'], ink=True,
            on_click=lambda e, r=rid: open_report(r),
        )

    def refresh():
        body.controls.clear()
        for status, title, icon, color in _lanes(colors):
            reports, total = reports_svc.get_reports(status=status, created_by=username, limit=None)
            header = ft.Row(
                controls=[
                    ft.Icon(icon, color=color, size=20),
                    ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=colors['text_primary']),
                    ft.Container(
                        content=ft.Text(str(total), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=color, border_radius=10,
                        padding=ft.padding.symmetric(1, 8),
                    ),
                ],
                spacing=8,
            )
            cards = [report_card(r, status, color) for r in reports]
            if not cards:
                cards = [ft.Text(t('mywork.nothing'), size=12, italic=True, color=colors['text_muted'])]
            body.controls.append(
                ft.Container(
                    content=ft.Column([header, ft.Container(height=6)] + cards, spacing=8, tight=True),
                    padding=16, border_radius=8,
                    bgcolor=colors['bg_secondary'],
                    border=ft.border.all(1, colors['border']),
                )
            )
        try:
            page.update()
        except Exception:
            pass

    refresh()
    return ft.Container(content=body, padding=8, expand=True)
