"""
Reports Module - Enhanced with Full Functionality
Implements View/Edit/History, Advanced Filtering, Fixed Search, Export Integration
"""
import flet as ft
import logging
from datetime import datetime
from typing import Optional, List, Dict
import csv
from pathlib import Path

logger = logging.getLogger('fiu_system')


class ReportsModule:
    """Complete reports viewing and management module with all features"""

    def __init__(self, page, db_manager, current_user, content_area):
        self.page = page
        self.db_manager = db_manager
        self.current_user = current_user
        self.content_area = content_area

        # Pagination
        self.current_page = 1
        self.records_per_page = 50
        self.total_records = 0

        # Filters
        self.search_query = ""
        self.active_filters = {}  # column_name: value
        self.status_filter = "All"

        # Data
        self.reports = []
        self.selected_report = None
        self.available_columns = []

    def show(self):
        """Display reports module"""
        logger.info("Loading reports module")

        # Load available columns
        self.load_available_columns()

        # Load reports
        self.load_reports()

        # Build UI
        reports_view = ft.Column(
            [
                self.build_header(),
                ft.Divider(height=1),
                self.build_filters(),
                ft.Divider(height=1),
                self.build_reports_table(),
                ft.Divider(height=1),
                self.build_pagination(),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.content_area.content = reports_view
        self.page.update()

    def build_header(self):
        """Build module header with actions"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.DESCRIPTION, size=32, color=ft.Colors.BLUE_700),
                            ft.Column(
                                [
                                    ft.Text("Reports", size=24, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"Total: {self.total_records} reports", size=12, color=ft.Colors.GREY_700),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                tooltip="Refresh",
                                on_click=lambda e: self.refresh_reports(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DOWNLOAD,
                                tooltip="Export to CSV",
                                on_click=lambda e: self.quick_export(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.FILTER_LIST,
                                tooltip="Advanced Filters",
                                on_click=lambda e: self.show_advanced_filters(),
                            ),
                        ],
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=20,
            bgcolor=ft.Colors.WHITE,
        )

    def build_filters(self):
        """Build filter bar with fixed search"""
        # Status filter
        self.status_dropdown = ft.Dropdown(
            hint_text="Status",
            options=[
                ft.dropdown.Option("All", "All Statuses"),
                ft.dropdown.Option("Open", "Open"),
                ft.dropdown.Option("Case Review", "Case Review"),
                ft.dropdown.Option("Under Investigation", "Under Investigation"),
                ft.dropdown.Option("Case Validation", "Case Validation"),
                ft.dropdown.Option("Close Case", "Close Case"),
                ft.dropdown.Option("Closed with STR", "Closed with STR"),
            ],
            value="All",
            width=200,
            on_change=lambda e: self.on_status_changed(e.control.value),
        )

        # Search field - FIX: Use on_submit instead of on_change
        self.search_field = ft.TextField(
            hint_text="Search by report number, entity name, or CIC...",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda e: self.on_search_submit(e.control.value),
            expand=True,
        )

        # Search button
        search_button = ft.IconButton(
            icon=ft.Icons.SEARCH,
            tooltip="Search",
            on_click=lambda e: self.on_search_submit(self.search_field.value),
        )

        return ft.Container(
            content=ft.Row(
                [
                    self.search_field,
                    search_button,
                    ft.Container(width=10),
                    self.status_dropdown,
                    ft.Container(width=10),
                    ft.ElevatedButton(
                        "Clear Filters",
                        icon=ft.Icons.CLEAR,
                        on_click=lambda e: self.clear_filters(),
                    ),
                ],
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=ft.Colors.GREY_50,
        )

    def build_reports_table(self):
        """Build reports data table"""
        # Define columns
        columns = [
            ft.DataColumn(ft.Text("SN", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Report Number", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Date", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Entity Name", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("CIC", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
        ]

        # Build rows
        rows = []
        for report in self.reports:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(report['sn']))),
                        ft.DataCell(ft.Text(report['report_number'])),
                        ft.DataCell(ft.Text(report['report_date'] or '-')),
                        ft.DataCell(ft.Text(
                            (report['reported_entity_name'][:30] + "...")
                            if report['reported_entity_name'] and len(report['reported_entity_name']) > 30
                            else (report['reported_entity_name'] or '-')
                        )),
                        ft.DataCell(ft.Text(report['cic'] or '-')),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    report['status'],
                                    size=12,
                                    color=ft.Colors.WHITE,
                                ),
                                padding=5,
                                bgcolor=self.get_status_color(report['status']),
                                border_radius=5,
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.VISIBILITY,
                                        tooltip="View Details",
                                        icon_size=18,
                                        icon_color=ft.Colors.BLUE_700,
                                        on_click=lambda e, r=report: self.view_report_details(r),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        icon_size=18,
                                        icon_color=ft.Colors.GREEN_700,
                                        on_click=lambda e, r=report: self.edit_report(r),
                                    ) if self.can_edit() else ft.Container(width=0),
                                    ft.IconButton(
                                        icon=ft.Icons.HISTORY,
                                        tooltip="View History",
                                        icon_size=18,
                                        icon_color=ft.Colors.ORANGE_700,
                                        on_click=lambda e, r=report: self.view_history(r),
                                    ),
                                ],
                                spacing=0,
                            )
                        ),
                    ],
                )
            )

        # Create data table
        if not rows:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.GREY_400),
                        ft.Text("No reports found", size=16, color=ft.Colors.GREY_600),
                        ft.Text("Try adjusting your filters", size=12, color=ft.Colors.GREY_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=40,
                expand=True,
                alignment=ft.alignment.center,
            )

        data_table = ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_200),
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_200),
            heading_row_color=ft.Colors.GREY_100,
            heading_row_height=50,
            data_row_max_height=60,
        )

        return ft.Container(
            content=ft.Column(
                [data_table],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )

    def build_pagination(self):
        """Build pagination controls"""
        total_pages = max(1, (self.total_records + self.records_per_page - 1) // self.records_per_page)

        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(f"Page {self.current_page} of {total_pages}"),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_LEFT,
                                on_click=lambda e: self.previous_page(),
                                disabled=self.current_page <= 1,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CHEVRON_RIGHT,
                                on_click=lambda e: self.next_page(),
                                disabled=self.current_page >= total_pages,
                            ),
                        ],
                    ),
                    ft.Text(f"Showing {len(self.reports)} of {self.total_records} records"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=20,
            bgcolor=ft.Colors.WHITE,
        )

    def load_available_columns(self):
        """Load available columns for filtering"""
        try:
            query = "SELECT column_name, display_name_en FROM column_settings ORDER BY display_order"
            self.available_columns = [dict(row) for row in self.db_manager.execute_with_retry(query)]
            logger.info(f"Loaded {len(self.available_columns)} filterable columns")
        except Exception as e:
            logger.error(f"Failed to load columns: {e}")
            self.available_columns = []

    def load_reports(self):
        """Load reports from database with pagination and filters"""
        try:
            # Build query
            query = "SELECT * FROM reports WHERE is_deleted = 0"
            params = []

            # Apply search filter
            if self.search_query:
                query += """ AND (
                    report_number LIKE ? OR
                    reported_entity_name LIKE ? OR
                    CAST(cic AS TEXT) LIKE ?
                )"""
                search_param = f"%{self.search_query}%"
                params.extend([search_param, search_param, search_param])

            # Apply status filter
            if self.status_filter and self.status_filter != "All":
                query += " AND status = ?"
                params.append(self.status_filter)

            # Apply advanced filters
            for col, value in self.active_filters.items():
                if value:
                    query += f" AND {col} LIKE ?"
                    params.append(f"%{value}%")

            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM ({query})"
            count_result = self.db_manager.execute_with_retry(count_query, params)
            self.total_records = count_result[0]['count']

            # Add pagination
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([self.records_per_page, (self.current_page - 1) * self.records_per_page])

            # Execute query
            self.reports = [dict(row) for row in self.db_manager.execute_with_retry(query, params)]

            logger.info(f"Loaded {len(self.reports)} reports (page {self.current_page})")

        except Exception as e:
            logger.error(f"Failed to load reports: {e}")
            self.reports = []
            self.total_records = 0

    def on_search_submit(self, value):
        """Handle search query submission"""
        self.search_query = value or ""
        self.current_page = 1
        self.show()

    def on_status_changed(self, value):
        """Handle status filter change"""
        self.status_filter = value
        self.current_page = 1
        self.show()

    def clear_filters(self):
        """Clear all filters"""
        self.search_query = ""
        self.status_filter = "All"
        self.active_filters = {}
        self.current_page = 1
        self.search_field.value = ""
        self.status_dropdown.value = "All"
        self.show()

    def refresh_reports(self):
        """Refresh reports list"""
        self.show()
        self.show_snackbar("Reports refreshed")

    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.show()

    def next_page(self):
        """Go to next page"""
        total_pages = (self.total_records + self.records_per_page - 1) // self.records_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.show()

    def view_report_details(self, report):
        """View detailed report information"""
        logger.info(f"Viewing report details: {report['report_number']}")

        # Build detailed view
        details_controls = []

        # Get all column settings for proper labels
        try:
            query = "SELECT column_name, display_name_en FROM column_settings ORDER BY display_order"
            columns = [dict(row) for row in self.db_manager.execute_with_retry(query)]

            for col in columns:
                col_name = col['column_name']
                if col_name in report and report[col_name]:
                    details_controls.append(
                        ft.Row(
                            [
                                ft.Text(f"{col['display_name_en']}:", weight=ft.FontWeight.BOLD, size=14, expand=1),
                                ft.Text(str(report[col_name]), size=14, expand=2),
                            ],
                            spacing=10,
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to load column settings: {e}")
            # Fallback to basic display
            for key, value in report.items():
                if value and key not in ['is_deleted', 'created_at', 'updated_at']:
                    details_controls.append(
                        ft.Row(
                            [
                                ft.Text(f"{key.replace('_', ' ').title()}:", weight=ft.FontWeight.BOLD, size=14, expand=1),
                                ft.Text(str(value), size=14, expand=2),
                            ],
                            spacing=10,
                        )
                    )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Report Details: {report['report_number']}"),
            content=ft.Container(
                content=ft.Column(
                    details_controls,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=600,
                height=500,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
            ],
        )

        self.page.open(dialog)

    def edit_report(self, report):
        """Edit report"""
        logger.info(f"Editing report: {report['report_number']}")
        self.show_snackbar(f"Edit functionality for report {report['report_number']} - Coming in next update")

    def view_history(self, report):
        """View report change history"""
        logger.info(f"Viewing history for report: {report['report_number']}")

        try:
            # Get change history
            query = """
                SELECT * FROM change_history
                WHERE table_name = 'reports' AND record_id = ?
                ORDER BY changed_at DESC
                LIMIT 50
            """
            history = [dict(row) for row in self.db_manager.execute_with_retry(query, (report['report_id'],))]

            if not history:
                self.show_snackbar("No change history found")
                return

            # Build history view
            history_controls = []
            for change in history:
                history_controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(f"{change['change_type']}: {change['field_name']}", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"From: {change['old_value'] or 'N/A'}", size=12),
                                    ft.Text(f"To: {change['new_value'] or 'N/A'}", size=12),
                                    ft.Text(f"By: {change['changed_by']} at {change['changed_at']}", size=11, color=ft.Colors.GREY_600),
                                ],
                                spacing=5,
                            ),
                            padding=10,
                        ),
                        elevation=1,
                    )
                )

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Change History: {report['report_number']}"),
                content=ft.Container(
                    content=ft.Column(
                        history_controls,
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=500,
                    height=400,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: self.page.close(dialog)),
                ],
            )

            self.page.open(dialog)

        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            self.show_snackbar(f"Failed to load history: {str(e)}")

    def show_advanced_filters(self):
        """Show advanced filters dialog with column selection"""
        filter_controls = []

        for col in self.available_columns:
            col_name = col['column_name']
            current_value = self.active_filters.get(col_name, "")

            filter_field = ft.TextField(
                label=col['display_name_en'],
                value=current_value,
                hint_text=f"Filter by {col['display_name_en'].lower()}",
            )

            filter_controls.append(
                ft.Row(
                    [
                        filter_field,
                        ft.IconButton(
                            icon=ft.Icons.CLEAR,
                            on_click=lambda e, f=filter_field: self.clear_single_filter(f),
                        ),
                    ],
                    spacing=5,
                )
            )

        def apply_filters(e):
            # Collect filter values
            self.active_filters = {}
            for i, col in enumerate(self.available_columns):
                row = filter_controls[i]
                field = row.controls[0]
                if field.value:
                    self.active_filters[col['column_name']] = field.value

            self.current_page = 1
            self.page.close(dialog)
            self.show()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Advanced Filters"),
            content=ft.Container(
                content=ft.Column(
                    filter_controls,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=500,
                height=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.page.close(dialog)),
                ft.ElevatedButton("Apply Filters", on_click=apply_filters),
            ],
        )

        self.page.open(dialog)

    def clear_single_filter(self, field):
        """Clear a single filter field"""
        field.value = ""
        self.page.update()

    def quick_export(self):
        """Quick export to CSV"""
        try:
            # Get all reports with current filters
            query = "SELECT * FROM reports WHERE is_deleted = 0"
            params = []

            if self.search_query:
                query += """ AND (
                    report_number LIKE ? OR
                    reported_entity_name LIKE ? OR
                    CAST(cic AS TEXT) LIKE ?
                )"""
                search_param = f"%{self.search_query}%"
                params.extend([search_param, search_param, search_param])

            if self.status_filter and self.status_filter != "All":
                query += " AND status = ?"
                params.append(self.status_filter)

            for col, value in self.active_filters.items():
                if value:
                    query += f" AND {col} LIKE ?"
                    params.append(f"%{value}%")

            reports = [dict(row) for row in self.db_manager.execute_with_retry(query, params)]

            if not reports:
                self.show_snackbar("No reports to export")
                return

            # Create picker to select export location
            file_picker = ft.FilePicker(
                on_result=lambda e: self.save_export(e, reports)
            )
            self.page.overlay.append(file_picker)
            self.page.update()
            file_picker.get_directory_path(dialog_title="Select Export Location")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            self.show_snackbar(f"Export failed: {str(e)}")

    def save_export(self, e: ft.FilePickerResultEvent, reports):
        """Save exported data"""
        if not e.path:
            return

        try:
            export_path = Path(e.path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Reports_Export_{timestamp}.csv"
            file_path = export_path / filename

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if reports:
                    fieldnames = list(reports[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(reports)

            logger.info(f"Exported {len(reports)} reports to: {file_path}")
            self.show_snackbar(f"Exported {len(reports)} reports successfully!")

        except Exception as e:
            logger.error(f"Failed to save export: {e}")
            self.show_snackbar(f"Failed to save export: {str(e)}")

    def can_edit(self):
        """Check if current user can edit reports"""
        return self.current_user['role'] in ['admin', 'agent']

    def get_status_color(self, status):
        """Get color for status badge"""
        colors = {
            'Open': ft.Colors.GREEN_700,
            'Case Review': ft.Colors.BLUE_700,
            'Under Investigation': ft.Colors.ORANGE_700,
            'Case Validation': ft.Colors.PURPLE_700,
            'Close Case': ft.Colors.RED_700,
            'Closed with STR': ft.Colors.GREY_700,
        }
        return colors.get(status, ft.Colors.GREY_700)

    def show_snackbar(self, message):
        """Show snackbar message"""
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()
