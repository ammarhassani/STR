"""
Toast Notification Component for FIU Report Management System.
Provides non-blocking notification messages.
"""
import flet as ft
from typing import Optional
from enum import Enum


class ToastType(Enum):
    """Toast notification types."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Toast:
    """Toast notification manager."""

    # Type configurations
    CONFIGS = {
        ToastType.SUCCESS: {
            "bgcolor": "#00d084",
            "icon": ft.Icons.CHECK_CIRCLE,
            "duration": 3000,
        },
        ToastType.ERROR: {
            "bgcolor": "#f44336",
            "icon": ft.Icons.ERROR,
            "duration": 5000,
        },
        ToastType.WARNING: {
            "bgcolor": "#ffa726",
            "icon": ft.Icons.WARNING,
            "duration": 4000,
        },
        ToastType.INFO: {
            "bgcolor": "#2196f3",
            "icon": ft.Icons.INFO,
            "duration": 3000,
        },
    }

    def __init__(self, page: ft.Page):
        """
        Initialize toast manager.

        Args:
            page: Flet page object
        """
        self.page = page

    def show(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: Optional[int] = None
    ):
        """
        Show a toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast (success, error, warning, info)
            duration: Duration in milliseconds (optional, uses default if not provided)
        """
        config = self.CONFIGS[toast_type]
        actual_duration = duration or config["duration"]

        snack_bar = ft.SnackBar(
            content=ft.Row(
                controls=[
                    ft.Icon(config["icon"], color=ft.Colors.WHITE, size=20),
                    ft.Text(message, color=ft.Colors.WHITE, size=14),
                ],
                spacing=10,
            ),
            bgcolor=config["bgcolor"],
            duration=actual_duration,
            behavior=ft.SnackBarBehavior.FLOATING,
            width=400,
            margin=ft.margin.only(bottom=20, right=20, left=20),
        )

        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()

    def success(self, message: str, duration: Optional[int] = None):
        """Show success toast."""
        self.show(message, ToastType.SUCCESS, duration)

    def error(self, message: str, duration: Optional[int] = None):
        """Show error toast."""
        self.show(message, ToastType.ERROR, duration)

    def warning(self, message: str, duration: Optional[int] = None):
        """Show warning toast."""
        self.show(message, ToastType.WARNING, duration)

    def info(self, message: str, duration: Optional[int] = None):
        """Show info toast."""
        self.show(message, ToastType.INFO, duration)


def show_toast(
    page: ft.Page,
    message: str,
    toast_type: ToastType = ToastType.INFO,
    duration: Optional[int] = None
):
    """
    Convenience function to show a toast.

    Args:
        page: Flet page object
        message: Message to display
        toast_type: Type of toast
        duration: Duration in milliseconds
    """
    Toast(page).show(message, toast_type, duration)


def show_success(page: ft.Page, message: str, duration: Optional[int] = None):
    """Show success toast."""
    Toast(page).success(message, duration)


def show_error(page: ft.Page, message: str, duration: Optional[int] = None):
    """Show error toast."""
    Toast(page).error(message, duration)


def show_warning(page: ft.Page, message: str, duration: Optional[int] = None):
    """Show warning toast."""
    Toast(page).warning(message, duration)


def show_info(page: ft.Page, message: str, duration: Optional[int] = None):
    """Show info toast."""
    Toast(page).info(message, duration)
