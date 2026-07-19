"""Import the unit's pre-STR history from a filled Excel template.

Two buttons and a results panel. The interesting part is the refusal: with
60,000 rows a flat list of errors is unreadable, so problems arrive grouped by
type with a count and example row numbers, which is what lets an analyst fix a
whole class of problem in one pass through the spreadsheet.
"""
import os
import threading
import flet as ft
from components.overlay import (mount as _overlay_mount,
                                dismiss as _overlay_dismiss)
from typing import Any

from theme.theme_manager import theme_manager
from components.app_button import app_button
from components.toast import show_error, show_success
from utils.file_dialog import choose_file, choose_save_file
from i18n import t


def show_retrospective_import_dialog(page: ft.Page, app_state: Any):
    colors = theme_manager.get_colors()
    service = getattr(app_state, "retrospective_import_service", None)
    if service is None:
        show_error(page, t("retro.err.unavailable"))
        return

    body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    busy = ft.ProgressBar(visible=False)

    def set_busy(on: bool):
        busy.visible = on
        try:
            page.update()
        except Exception:
            pass

    def line(text, color=None, size=12, bold=False):
        return ft.Text(text, size=size, color=color or colors["text_secondary"],
                       weight=ft.FontWeight.BOLD if bold else None, selectable=True)

    def show_problems(result):
        """A refusal, grouped by problem type rather than listed row by row."""
        body.controls.clear()
        body.controls.append(line(result.get("error", t("retro.refused")),
                                  colors["danger"], size=13, bold=True))
        problems = result.get("problems") or {}
        if problems:
            body.controls.append(line(t("retro.problems_heading"), size=12, bold=True))
        for kind, info in sorted(problems.items(),
                                 key=lambda kv: -kv[1].get("count", 0)):
            rows = ", ".join(str(r) for r in info.get("rows", []))
            more = "" if info.get("count", 0) <= len(info.get("rows", [])) else " ..."
            body.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            line(f"{kind}  —  {info.get('count')} row(s)",
                                 colors["danger"], size=12, bold=True),
                            line(t("retro.example_rows", rows=rows + more), size=11),
                        ],
                        spacing=2,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.06, colors["danger"]),
                    border_radius=4,
                    padding=ft.padding.symmetric(6, 10),
                )
            )
        page.update()

    def do_template(e):
        path = choose_save_file(prompt=t("retro.save_template"),
                                default_name="str_history_template.xlsx")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        ok, msg = service.write_template(path)
        (show_success if ok else show_error)(page, msg)
        if ok:
            body.controls.clear()
            body.controls.append(line(t("retro.template_written", path=path),
                                      colors["success"], size=13))
            page.update()

    def do_import(e):
        path = choose_file(prompt=t("retro.choose_file"))
        if not path:
            return
        body.controls.clear()
        body.controls.append(line(t("retro.working", name=os.path.basename(path))))
        set_busy(True)

        def run():
            ok, result = service.import_file(path)
            set_busy(False)
            if ok:
                body.controls.clear()
                body.controls.append(
                    line(t("retro.imported", n=result.get("imported"),
                           name=result.get("source_file")),
                         colors["success"], size=13, bold=True))
                body.controls.append(line(t("retro.batch", id=result.get("batch_id"))))
                show_success(page, t("retro.imported_short", n=result.get("imported")))
                page.update()
            else:
                show_problems(result)
                show_error(page, result.get("error", t("retro.refused")))

        # a 60k-row file takes a few seconds; keep the UI responsive
        threading.Thread(target=run, daemon=True).start()

    def close(e):
        _overlay_dismiss(page, dialog)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.HISTORY_EDU, color=colors["primary"]),
                ft.Text(t("retro.title"), weight=ft.FontWeight.BOLD),
            ],
            spacing=10,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(t("retro.subtitle"), size=12,
                            color=colors["text_secondary"]),
                    ft.Row(
                        controls=[
                            app_button(t("retro.get_template"), icon=ft.Icons.DOWNLOAD,
                                       on_click=do_template, variant="secondary"),
                            app_button(t("retro.upload"), icon=ft.Icons.UPLOAD_FILE,
                                       on_click=do_import, variant="primary"),
                        ],
                        spacing=12,
                    ),
                    busy,
                    ft.Divider(height=1, color=colors["border"]),
                    body,
                ],
                spacing=12, tight=True,
            ),
            width=620, height=420, padding=8,
        ),
        actions=[ft.TextButton(t("common.close"), on_click=close)],
    )
    _overlay_mount(page, dialog, update=False)
    page.update()
