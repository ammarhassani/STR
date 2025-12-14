"""
Help Dialog for FIU Report Management System.
Comprehensive help system with documentation and shortcuts.
"""
import flet as ft
from typing import Any

from theme.theme_manager import theme_manager


def show_help_dialog(page: ft.Page, app_state: Any = None):
    """
    Show the help dialog.

    Args:
        page: Flet page object
        app_state: Application state (optional)
    """
    colors = theme_manager.get_colors()

    # Getting Started content
    getting_started_content = """
## Welcome to FIU Report Management System

This system helps you manage and track FIU (Financial Intelligence Unit) reports efficiently.

### Quick Start Guide

1. **Dashboard** - View your daily summary, KPIs, and charts
2. **Reports** - Create, edit, and manage reports
3. **Export** - Export reports to CSV format
4. **Settings** - Configure system settings (Admin only)

### Creating a Report

1. Click "New Report" in the toolbar
2. Fill in the required fields (marked with *)
3. Click "Save" to save as draft or "Submit for Approval"

### Need Help?

Contact your system administrator for assistance.
    """

    # Keyboard Shortcuts content
    shortcuts_content = """
## Keyboard Shortcuts

### General Actions
| Shortcut | Action |
|----------|--------|
| F1 | Open Help |
| F5 | Refresh Current View |
| Ctrl+N | New Report (if permitted) |
| Ctrl+P | My Profile |
| Escape | Close Open Dialog |

### Admin Only Shortcuts
| Shortcut | Action |
|----------|--------|
| Ctrl+B | Backup & Restore |
| Ctrl+R | Reservation Management |

### Navigation
Use the sidebar to navigate between different sections of the application.

### Tips
- Use the toolbar buttons for quick actions
- Click the theme toggle to switch between light/dark modes
- Hover over buttons to see tooltips
    """

    # FAQ content
    faq_content = """
## Frequently Asked Questions

### Q: How do I create a new report?
Click the "New Report" button in the toolbar or press Ctrl+N.

### Q: How do I export reports?
Go to the Export section from the sidebar and select your filters.

### Q: What are report statuses?
- **Open**: Report is being drafted
- **Case Review**: Awaiting initial review
- **Under Investigation**: Being investigated
- **Case Validation**: Final validation stage
- **Close Case**: Case closed without STR
- **Closed with STR**: Case closed with STR filed

### Q: How do I change my password?
Click on your profile icon > My Profile > Security tab > Change Password

### Q: Who can approve reports?
Only users with Admin role can approve reports.
    """

    # About content
    about_content = ft.Column(
        controls=[
            ft.Icon(ft.Icons.SECURITY, size=64, color=colors["primary"]),
            ft.Container(height=16),
            ft.Text(
                "FIU Report Management System",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=8),
            ft.Text(
                "Version 2.0.0 (Flet Edition)",
                size=14,
                color=colors["text_secondary"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=24),
            ft.Text(
                "A comprehensive system for managing Financial Intelligence Unit reports.\n"
                "Built with Python and Flet for cross-platform desktop applications.",
                size=12,
                color=colors["text_secondary"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=24),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Technology Stack", weight=ft.FontWeight.BOLD, size=12),
                        ft.Text("Python 3.9+", size=11, color=colors["text_muted"]),
                        ft.Text("Flet 0.21+", size=11, color=colors["text_muted"]),
                        ft.Text("SQLite3", size=11, color=colors["text_muted"]),
                        ft.Text("Plotly Charts", size=11, color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=16,
                bgcolor=colors["bg_tertiary"],
                border_radius=8,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # Tabs
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[
            ft.Tab(
                text="Getting Started",
                icon=ft.Icons.ROCKET_LAUNCH,
                content=ft.Container(
                    content=ft.Markdown(
                        getting_started_content,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
                    padding=20,
                ),
            ),
            ft.Tab(
                text="Shortcuts",
                icon=ft.Icons.KEYBOARD,
                content=ft.Container(
                    content=ft.Markdown(
                        shortcuts_content,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
                    padding=20,
                ),
            ),
            ft.Tab(
                text="FAQ",
                icon=ft.Icons.HELP_OUTLINE,
                content=ft.Container(
                    content=ft.Markdown(
                        faq_content,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
                    padding=20,
                ),
            ),
            ft.Tab(
                text="About",
                icon=ft.Icons.INFO_OUTLINE,
                content=ft.Container(
                    content=about_content,
                    padding=20,
                    alignment=ft.alignment.center,
                ),
            ),
        ],
    )

    def close_dialog(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.HELP, color=colors["primary"]),
                ft.Container(width=8),
                ft.Text("Help & Documentation"),
                ft.Container(expand=True),
                ft.Text("v2.0.0", size=11, color=colors["text_muted"]),
            ],
        ),
        content=ft.Container(
            content=tabs,
            width=600,
            height=450,
        ),
        actions=[
            ft.TextButton("Close", on_click=close_dialog),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()
