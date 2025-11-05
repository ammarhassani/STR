"""
Reports Module - Production-Grade Reports Viewing and Management
Implements comprehensive report listing, filtering, search, and management
"""
import flet as ft
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger('fiu_system')


class ReportsModule:
    """Complete reports viewing and management module"""

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
        self.status_filter = "All"
        self.date_from = None
        self.date_to = None

        # Data
        self.reports = []
        self.selected_report = None

    def show(self):
        """Display reports module"""
        logger.info("Loading reports module")

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
                                tooltip="Export",
                                on_click=lambda e: self.show_export_dialog(),
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
        """Build filter bar"""
        # Search field
        self.search_field = ft.TextField(
            hint_text="Search by report number, entity name, or CIC...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: self.on_search_changed(e.control.value),
            expand=True,
        )

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

        return ft.Container(
            content=ft.Row(
                [
                    self.search_field,
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
                        ft.DataCell(ft.Text(report['report_date'])),
                        ft.DataCell(ft.Text(report['reported_entity_name'][:30] + "..." if len(report['reported_entity_name']) > 30 else report['reported_entity_name'])),
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
                                        on_click=lambda e, r=report: self.view_report_details(r),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        icon_size=18,
                                        on_click=lambda e, r=report: self.edit_report(r),
                                    ) if self.can_edit() else ft.Container(),
                                    ft.IconButton(
                                        icon=ft.Icons.HISTORY,
                                        tooltip="View History",
                                        icon_size=18,
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
        total_pages = (self.total_records + self.records_per_page - 1) // self.records_per_page

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

    def load_reports(self):
        """Load reports from database with pagination and filters"""
        try:
            # Build query
            query = """
                SELECT * FROM reports
                WHERE is_deleted = 0
            """
            params = []

            # Apply search filter
            if self.search_query:
                query += """ AND (
                    report_number LIKE ? OR
                    reported_entity_name LIKE ? OR
                    cic LIKE ?
                )"""
                search_param = f"%{self.search_query}%"
                params.extend([search_param, search_param, search_param])

            # Apply status filter
            if self.status_filter and self.status_filter != "All":
                query += " AND status = ?"
                params.append(self.status_filter)

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

    def on_search_changed(self, value):
        """Handle search query change"""
        self.search_query = value
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
        self.current_page = 1
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
        # TODO: Implement detailed view dialog
        self.show_snackbar(f"Viewing report {report['report_number']}")

    def edit_report(self, report):
        """Edit report"""
        logger.info(f"Editing report: {report['report_number']}")
        # TODO: Implement edit functionality
        self.show_snackbar(f"Editing report {report['report_number']}")

    def view_history(self, report):
        """View report change history"""
        logger.info(f"Viewing history for report: {report['report_number']}")
        # TODO: Implement history view
        self.show_snackbar(f"Viewing history for {report['report_number']}")

    def show_export_dialog(self):
        """Show export options dialog"""
        # TODO: Implement export dialog
        self.show_snackbar("Export functionality - Coming in next update")

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
