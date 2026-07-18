"""Admin: manage config-driven dashboard widgets (#17/#4). Add/edit/delete the
rows in dashboard_config. Every query is validated + test-run read-only before
it can be saved, so a broken or dangerous widget never reaches the board.
"""
import flet as ft
from typing import Any, Dict, Optional

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error

WIDGET_TYPES = ['kpi_card', 'metric', 'bar_chart', 'line_chart', 'pie_chart', 'table']
ROLE_CHOICES = ['admin', 'supervisor', 'agent', 'reporter']


def build_dashboard_widgets_view(page: ft.Page, app_state: Any) -> ft.Control:
    colors = theme_manager.get_colors()
    dash = app_state.dashboard_service
    body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh():
        body.controls.clear()
        widgets = dash.list_all_widgets()
        if not widgets:
            body.controls.append(ft.Text("No widgets yet. Add one.", color=colors["text_muted"]))
        for w in widgets:
            body.controls.append(_row_card(w))
        try:
            page.update()
        except Exception:
            pass

    def _row_card(w: Dict):
        status = "active" if w.get('is_active') else "hidden"
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=6, height=36, bgcolor=w.get('color') or colors["primary"],
                                 border_radius=3),
                    ft.Column([
                        ft.Text(w['title'], size=13, weight=ft.FontWeight.W_600, color=colors["text_primary"]),
                        ft.Text(f"{w['widget_type']} · {status} · roles: {w.get('visible_to_roles') or '-'}",
                                size=11, color=colors["text_muted"]),
                    ], spacing=1, expand=True),
                    ft.IconButton(ft.Icons.EDIT, icon_size=18, tooltip="Edit",
                                  on_click=lambda e, wid=w: open_editor(wid)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=colors["danger"],
                                  tooltip="Delete", on_click=lambda e, wid=w: confirm_delete(wid)),
                ],
                spacing=10,
            ),
            padding=12, border_radius=8, bgcolor=colors["card_bg"],
            border=ft.border.all(1, colors["card_border"]),
        )

    def confirm_delete(w: Dict):
        def do(e):
            ok, msg = dash.delete_widget(w['widget_id'])
            dlg.open = False
            page.update()
            (show_success if ok else show_error)(page, msg)
            if ok:
                refresh()
        dlg = ft.AlertDialog(
            modal=True, title=ft.Text("Delete widget"),
            content=ft.Text(f"Delete '{w['title']}'? This cannot be undone."),
            actions=[ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                     ft.ElevatedButton("Delete", bgcolor=colors["danger"], color=ft.Colors.WHITE, on_click=do)],
        )
        page.overlay.append(dlg); dlg.open = True; page.update()

    def _close(dlg):
        dlg.open = False; page.update()

    def open_editor(w: Optional[Dict] = None):
        is_edit = w is not None
        type_ref = ft.Ref[ft.Dropdown]()
        title_ref = ft.Ref[ft.TextField]()
        sql_ref = ft.Ref[ft.TextField]()
        color_ref = ft.Ref[ft.TextField]()
        icon_ref = ft.Ref[ft.TextField]()
        order_ref = ft.Ref[ft.TextField]()
        active_ref = ft.Ref[ft.Checkbox]()
        role_boxes = {r: ft.Checkbox(label=r, value=(r in (w.get('visible_to_roles', '') if w else 'admin')))
                      for r in ROLE_CHOICES}
        test_result = ft.Text("", size=11, color=colors["text_muted"], selectable=True)

        def gather() -> Dict[str, Any]:
            roles = ",".join(r for r, cb in role_boxes.items() if cb.value) or "admin"
            return {
                'widget_type': type_ref.current.value,
                'title': title_ref.current.value or '',
                'sql_query': sql_ref.current.value or '',
                'color': color_ref.current.value or '#3b82f6',
                'icon': icon_ref.current.value or None,
                'visible_to_roles': roles,
                'is_active': 1 if active_ref.current.value else 0,
                'display_order': int(order_ref.current.value or 0) if (order_ref.current.value or '0').isdigit() else 0,
            }

        def test_query(e):
            ok, rows, cols, err = dash.run_widget_query(sql_ref.current.value or '')
            if ok:
                test_result.value = f"✓ OK — {len(rows)} row(s), columns: {', '.join(cols) or '(none)'}"
                test_result.color = colors["success"]
            else:
                test_result.value = f"✗ {err}"
                test_result.color = colors["danger"]
            page.update()

        def save(e):
            data = gather()
            if is_edit:
                ok, msg = dash.update_widget(w['widget_id'], data)
            else:
                ok, msg = dash.create_widget(data)
            if ok:
                dlg.open = False; page.update()
                show_success(page, msg); refresh()
            else:
                test_result.value = f"✗ {msg}"; test_result.color = colors["danger"]; page.update()

        form = ft.Column(
            controls=[
                ft.Dropdown(ref=type_ref, label="Widget type", value=(w['widget_type'] if is_edit else 'kpi_card'),
                            options=[ft.dropdown.Option(t) for t in WIDGET_TYPES], text_size=13),
                ft.TextField(ref=title_ref, label="Title", value=(w['title'] if is_edit else ''), text_size=13),
                ft.TextField(ref=sql_ref, label="SQL query (read-only SELECT)",
                             value=(w['sql_query'] if is_edit else 'SELECT COUNT(*) AS value FROM reports WHERE is_deleted = 0'),
                             multiline=True, min_lines=3, max_lines=8, text_size=12),
                ft.Row([ft.TextButton("Test query", icon=ft.Icons.PLAY_ARROW, on_click=test_query)]),
                test_result,
                ft.Row([
                    ft.TextField(ref=color_ref, label="Color (#hex)", value=(w.get('color') if is_edit else '#3b82f6'),
                                 width=140, text_size=13),
                    ft.TextField(ref=icon_ref, label="Icon (kpi only)", value=(w.get('icon') or '' if is_edit else ''),
                                 width=160, text_size=13),
                    ft.TextField(ref=order_ref, label="Order", value=str(w.get('display_order', 0) if is_edit else 0),
                                 width=90, text_size=13, keyboard_type=ft.KeyboardType.NUMBER),
                ], spacing=10, wrap=True),
                ft.Text("Visible to roles:", size=12, color=colors["text_secondary"]),
                ft.Row(list(role_boxes.values()), spacing=8, wrap=True),
                ft.Checkbox(ref=active_ref, label="Active", value=(bool(w.get('is_active', 1)) if is_edit else True)),
            ],
            spacing=10, scroll=ft.ScrollMode.AUTO, tight=True,
        )
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit widget" if is_edit else "Add widget"),
            content=ft.Container(content=form, width=560, height=560),
            actions=[ft.TextButton("Cancel", on_click=lambda e: _close(dlg)),
                     ft.ElevatedButton("Save", bgcolor=colors["primary"], color=ft.Colors.WHITE, on_click=save)],
        )
        page.overlay.append(dlg); dlg.open = True; page.update()

    header = ft.Row(
        controls=[
            ft.Text("Dashboard Widgets", size=18, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
            ft.Container(expand=True),
            ft.ElevatedButton("Add Widget", icon=ft.Icons.ADD, bgcolor=colors["primary"],
                              color=ft.Colors.WHITE, on_click=lambda e: open_editor(None)),
        ],
    )
    refresh()
    return ft.Container(
        content=ft.Column([header, ft.Container(height=8), body], expand=True),
        padding=16, expand=True,
    )
