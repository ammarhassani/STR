"""
Data Table Component for FIU Report Management System.
Provides a paginated, sortable data table with filtering support.
"""
import flet as ft
from typing import List, Dict, Any, Callable, Optional

from theme.theme_manager import theme_manager


def create_data_table(
    columns: List[Dict[str, Any]],
    data: List[Dict[str, Any]],
    on_row_click: Optional[Callable[[Dict], None]] = None,
    on_row_double_click: Optional[Callable[[Dict], None]] = None,
    show_checkbox: bool = False,
    selected_rows: Optional[List[int]] = None,
    on_selection_change: Optional[Callable[[List[int]], None]] = None,
) -> ft.DataTable:
    """
    Create a data table.

    Args:
        columns: List of column definitions with 'key', 'header', 'width'
        data: List of row data dictionaries
        on_row_click: Callback for row click
        on_row_double_click: Callback for row double-click
        show_checkbox: Show selection checkboxes
        selected_rows: List of selected row indices
        on_selection_change: Callback for selection changes

    Returns:
        DataTable control
    """
    colors = theme_manager.get_colors()

    # Build columns
    data_columns = [
        ft.DataColumn(
            ft.Text(
                col.get('header', col.get('key', '')),
                weight=ft.FontWeight.BOLD,
                size=12,
                color=colors["text_primary"],
            ),
            numeric=col.get('numeric', False),
        )
        for col in columns
    ]

    # Build rows
    data_rows = []
    for row_idx, row in enumerate(data):
        cells = []
        for col in columns:
            key = col.get('key', '')
            value = row.get(key, '')

            # Handle None values
            if value is None:
                value = ''

            # Format value
            cell_text = str(value)

            # Truncate long text
            max_len = col.get('max_length', 50)
            if len(cell_text) > max_len:
                cell_text = cell_text[:max_len] + '...'

            cells.append(
                ft.DataCell(
                    ft.Text(
                        cell_text,
                        size=12,
                        color=colors["text_primary"],
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    on_tap=lambda e, r=row: on_row_click(r) if on_row_click else None,
                    on_double_tap=lambda e, r=row: on_row_double_click(r) if on_row_double_click else None,
                )
            )

        data_rows.append(
            ft.DataRow(
                cells=cells,
                selected=row_idx in (selected_rows or []),
                on_select_changed=lambda e, idx=row_idx: _handle_selection(
                    e, idx, selected_rows, on_selection_change
                ) if show_checkbox else None,
            )
        )

    return ft.DataTable(
        columns=data_columns,
        rows=data_rows,
        column_spacing=20,
        horizontal_lines=ft.BorderSide(1, colors["border"]),
        heading_row_color=colors["bg_tertiary"],
        data_row_color={
            ft.ControlState.HOVERED: colors["hover"],
        },
        border_radius=8,
        show_checkbox_column=show_checkbox,
    )


def _handle_selection(e, idx, selected_rows, callback):
    """Handle row selection."""
    if callback:
        new_selection = list(selected_rows or [])
        if e.data == "true":
            if idx not in new_selection:
                new_selection.append(idx)
        else:
            if idx in new_selection:
                new_selection.remove(idx)
        callback(new_selection)


# Note: UserControl was removed in Flet 0.21+
# Use create_paginated_table function instead


def create_paginated_table(
    columns: List[Dict[str, Any]],
    data: List[Dict[str, Any]],
    total_count: int,
    current_page: int,
    page_size: int,
    on_row_click: Optional[Callable[[Dict], None]] = None,
    on_row_double_click: Optional[Callable[[Dict], None]] = None,
    on_prev_page: Optional[Callable[[], None]] = None,
    on_next_page: Optional[Callable[[], None]] = None,
    is_loading: bool = False,
) -> ft.Column:
    """
    Create a paginated data table.

    Args:
        columns: Column definitions
        data: Current page data
        total_count: Total number of records
        current_page: Current page number (1-based)
        page_size: Items per page
        on_row_click: Row click callback
        on_row_double_click: Row double-click callback
        on_prev_page: Previous page callback
        on_next_page: Next page callback
        is_loading: Whether data is loading

    Returns:
        Column with table and pagination controls
    """
    colors = theme_manager.get_colors()

    # Loading indicator
    if is_loading:
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.ProgressRing(width=32, height=32),
                            ft.Text("Loading...", color=colors["text_secondary"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    expand=True,
                    alignment=ft.alignment.center,
                ),
            ],
            expand=True,
        )

    # Calculate pagination
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    start_item = (current_page - 1) * page_size + 1 if total_count > 0 else 0
    end_item = min(current_page * page_size, total_count)

    # Build table
    table = create_data_table(
        columns,
        data,
        on_row_click=on_row_click,
        on_row_double_click=on_row_double_click,
    )

    # Pagination controls
    pagination = ft.Row(
        controls=[
            ft.Text(
                f"Showing {start_item}-{end_item} of {total_count}" if total_count > 0 else "No records",
                size=12,
                color=colors["text_secondary"],
            ),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT,
                icon_color=colors["text_primary"] if current_page > 1 else colors["disabled"],
                disabled=current_page <= 1,
                on_click=lambda e: on_prev_page() if on_prev_page else None,
            ),
            ft.Text(
                f"Page {current_page} of {total_pages}",
                size=12,
                color=colors["text_primary"],
            ),
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT,
                icon_color=colors["text_primary"] if current_page < total_pages else colors["disabled"],
                disabled=current_page >= total_pages,
                on_click=lambda e: on_next_page() if on_next_page else None,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    return ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[table],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                expand=True,
                border=ft.border.all(1, colors["border"]),
                border_radius=8,
            ),
            ft.Container(
                content=pagination,
                padding=ft.padding.symmetric(vertical=8, horizontal=16),
            ),
        ],
        expand=True,
    )
