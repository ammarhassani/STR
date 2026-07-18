"""Pending FIU basket — every report that is saved but still waiting for the
number the FIU issues.

This is a SHARED queue, not a personal one: anyone can see what is outstanding,
so a report does not sit forgotten because the agent who filed it is on leave.
Opening a report from here is the normal edit dialog — the analyst adds the FIU
details and submits it, which is the moment it reaches a supervisor.
"""
import flet as ft
from typing import Any
from datetime import datetime

from theme.theme_manager import theme_manager
from dialogs.report_dialog import show_report_dialog
from i18n import t


def _waiting_days(report) -> int:
    """How long this report has been sitting in the basket."""
    raw = report.get('created_at') or ''
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return max(0, (datetime.now() - datetime.strptime(str(raw)[:26], fmt)).days)
        except ValueError:
            continue
    return 0


def build_fiu_basket_view(page: ft.Page, app_state: Any) -> ft.Control:
    colors = theme_manager.get_colors()
    reports_svc = app_state.report_service
    can_edit = bool(app_state.auth_service
                    and app_state.auth_service.has_permission('add_report'))

    body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def open_report(report_id):
        rep = reports_svc.get_report(report_id)
        if rep:
            show_report_dialog(page, app_state, report_data=rep, on_save=refresh)

    def missing_fields(rep):
        pretty = {'fiu_number': t("field.fiu_number"), 'fiu_date': t("field.fiu_date")}
        out = []
        for f in getattr(reports_svc, 'REQUIRED_FIU_FIELDS', ('fiu_number', 'fiu_date')):
            if not str(rep.get(f) or '').strip():
                label = pretty.get(f, f)
                out.append(label if label != f"field.{f}" else f.replace('_', ' ').title())
        return out

    def card(rep):
        days = _waiting_days(rep)
        missing = missing_fields(rep)
        # A report that has waited a long time is the one most at risk of being
        # forgotten, so it is the one that gets the loud colour.
        tone = colors['danger'] if days >= 7 else (
            colors['warning'] if days >= 3 else colors['text_secondary'])
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(rep.get('report_number') or '—', size=13,
                                            weight=ft.FontWeight.W_600, color=colors['text_primary']),
                                    ft.Text(rep.get('reported_entity_name') or t("common.no_entity"),
                                            size=13, color=colors['text_primary'], expand=True),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(f"{t('fiu.owner')}: {rep.get('created_by') or '—'}",
                                            size=11, color=colors['text_muted']),
                                    ft.Text("·", size=11, color=colors['text_muted']),
                                    ft.Text(t("fiu.waiting_days", n=days), size=11, color=tone),
                                    ft.Text("·", size=11, color=colors['text_muted']),
                                    ft.Text(t("fiu.missing", fields=", ".join(missing)) if missing else "",
                                            size=11, color=colors['text_muted'], expand=True),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=4, expand=True,
                    ),
                    ft.TextButton(
                        t("fiu.open"),
                        icon=ft.Icons.EDIT_NOTE,
                        on_click=lambda e, rid=rep['report_id']: open_report(rid),
                        disabled=not can_edit,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=colors['bg_secondary'],
            border=ft.border.all(1, colors['border']),
            border_radius=4,
            padding=ft.padding.symmetric(10, 14),
        )

    def refresh():
        body.controls.clear()
        status = getattr(reports_svc, 'STATUS_PENDING_FIU', 'pending_fiu')
        rows, total = reports_svc.get_reports(status, None, None, None, None, 500, 0)
        body.controls.append(
            ft.Text(t("fiu.count", n=total), size=12, color=colors['text_secondary']))
        if not rows:
            body.controls.append(
                ft.Container(content=ft.Text(t("fiu.empty"), size=13,
                                             color=colors['text_muted']),
                             padding=20))
        else:
            # oldest first: the report that has waited longest needs chasing most
            for rep in sorted(rows, key=_waiting_days, reverse=True):
                body.controls.append(card(rep))
        try:
            page.update()
        except Exception:
            pass

    refresh()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PENDING_ACTIONS, color=colors['warning']),
                        ft.Text(t("fiu.title"), size=18, weight=ft.FontWeight.BOLD,
                                color=colors['text_primary'], expand=True),
                        ft.IconButton(ft.Icons.REFRESH, tooltip=t("common.refresh"),
                                      on_click=lambda e: refresh()),
                    ],
                    spacing=8,
                ),
                ft.Text(t("fiu.subtitle"), size=12, color=colors['text_secondary']),
                ft.Divider(height=1, color=colors['border']),
                body,
            ],
            spacing=12, expand=True,
        ),
        padding=16, expand=True,
    )
