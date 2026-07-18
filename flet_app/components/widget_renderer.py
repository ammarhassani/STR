"""Render a config-driven dashboard widget (from dashboard_config) into a Flet
control. The widget's query result is already normalized to a list of dicts by
DashboardService; here we only shape it per widget_type. Never trusts the query
to have succeeded — a widget carrying an `error` renders an error card.
"""
import flet as ft
from typing import Any, Dict, List

from theme.theme_manager import theme_manager
from components.charts import create_pie_chart, create_bar_chart, create_line_chart


def _label_value(data: List[Dict], columns: List[str]) -> List[Dict[str, Any]]:
    """Coerce arbitrary query rows into [{label, value}]: prefer columns named
    label/value, else use the first two columns."""
    out = []
    for row in data:
        if 'label' in row and 'value' in row:
            label, value = row['label'], row['value']
        else:
            keys = list(row.keys())
            label = row[keys[0]] if keys else ''
            value = row[keys[1]] if len(keys) > 1 else (row[keys[0]] if keys else 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0
        out.append({'label': str(label), 'value': value})
    return out


def _single_value(data: List[Dict]) -> str:
    if not data:
        return "0"
    row = data[0]
    if 'value' in row:
        v = row['value']
    else:
        keys = list(row.keys())
        v = row[keys[0]] if keys else 0
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def _card(colors, content, min_width=280, expand=True):
    return ft.Container(
        content=content, padding=16, border_radius=12,
        bgcolor=colors["card_bg"], border=ft.border.all(1, colors["card_border"]),
        expand=expand, width=None if expand else min_width,
    )


def _kpi_card(colors, widget):
    color = widget.get('color') or colors["primary"]
    icon_name = (widget.get('icon') or '').replace('-', '_').upper()
    icon = getattr(ft.Icons, icon_name, ft.Icons.INSIGHTS)
    return _card(colors, ft.Column(
        controls=[
            ft.Container(content=ft.Icon(icon, color=color, size=24),
                         width=44, height=44, border_radius=8,
                         bgcolor=ft.Colors.with_opacity(0.12, color), alignment=ft.alignment.center),
            ft.Container(height=10),
            ft.Text(_single_value(widget['data']), size=30, weight=ft.FontWeight.BOLD,
                    color=colors["text_primary"]),
            ft.Text(widget['title'], size=13, color=colors["text_secondary"], weight=ft.FontWeight.W_500),
        ], spacing=2, tight=True))


def _table_widget(colors, widget):
    cols = widget.get('columns') or (list(widget['data'][0].keys()) if widget['data'] else [])
    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(c, weight=ft.FontWeight.BOLD, size=12,
                                       color=colors["text_primary"])) for c in cols],
        rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(str(r.get(c, '')), size=12,
                                                    color=colors["text_secondary"])) for c in cols])
              for r in widget['data'][:50]],
        heading_row_color=colors["bg_tertiary"], border_radius=4,
    )
    return _card(colors, ft.Column([
        ft.Text(widget['title'], size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
        ft.Container(height=8),
        ft.Container(content=table, ),
    ], scroll=ft.ScrollMode.AUTO, tight=True))


def _error_card(colors, widget):
    return _card(colors, ft.Column([
        ft.Row([ft.Icon(ft.Icons.WARNING_AMBER, color=colors["warning"], size=18),
                ft.Text(widget['title'], size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"])],
               spacing=6),
        ft.Text(widget.get('error') or "Widget failed to load.", size=12, color=colors["text_muted"],
                selectable=True),
    ], spacing=6, tight=True))


def render_widget(widget: Dict[str, Any]) -> ft.Control:
    colors = theme_manager.get_colors()
    if widget.get('error'):
        return _error_card(colors, widget)
    wtype = widget.get('widget_type')
    data = widget.get('data') or []
    columns = widget.get('columns') or []
    title = widget.get('title', '')

    if wtype in ('kpi_card', 'metric'):
        return _kpi_card(colors, widget)
    if wtype == 'table':
        return _table_widget(colors, widget)
    if wtype == 'pie_chart':
        return _card(colors, create_pie_chart(_label_value(data, columns), title=title, height=250).content
                     if data else ft.Text(f"{title}: no data", color=colors["text_muted"]))
    if wtype == 'bar_chart':
        return _card(colors, create_bar_chart(_label_value(data, columns), title=title, height=250).content
                     if data else ft.Text(f"{title}: no data", color=colors["text_muted"]))
    if wtype == 'line_chart':
        return _card(colors, create_line_chart(_label_value(data, columns), title=title, height=250,
                                               x_key='label', y_key='value').content
                     if data else ft.Text(f"{title}: no data", color=colors["text_muted"]))
    return _error_card(colors, {'title': title, 'error': f"Unknown widget type: {wtype}"})


def render_widget_grid(widgets: List[Dict[str, Any]]) -> ft.Control:
    """Lay widgets out in a responsive wrap. KPI/metric cards are narrow; charts
    and tables take a wider column."""
    if not widgets:
        colors = theme_manager.get_colors()
        return ft.Text("No dashboard widgets configured.", color=theme_manager.get_colors()["text_muted"])
    row = ft.ResponsiveRow(columns=12, spacing=16, run_spacing=16)
    for w in widgets:
        control = render_widget(w)
        # KPIs are compact (3/12), charts + tables wide (6/12), stacked on small screens
        span = 3 if w.get('widget_type') in ('kpi_card', 'metric') else 6
        control.col = {"xs": 12, "md": span}
        row.controls.append(control)
    return row
