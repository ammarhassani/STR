"""
Form Field Components for FIU Report Management System.
Reusable form input components with validation support.
"""
import flet as ft
from typing import List, Optional, Callable, Any
from datetime import datetime

from theme.theme_manager import theme_manager


def create_text_field(
    label: str,
    value: str = "",
    hint: str = "",
    required: bool = False,
    multiline: bool = False,
    password: bool = False,
    read_only: bool = False,
    width: Optional[int] = None,
    on_change: Optional[Callable] = None,
    error_text: str = None,
    max_length: int = None,
    ref: Optional[ft.Ref] = None,
) -> ft.Column:
    """
    Create a labeled text field.

    Args:
        label: Field label
        value: Initial value
        hint: Placeholder text
        required: Whether field is required
        multiline: Enable multiline input
        password: Enable password mode
        read_only: Make field read-only
        width: Field width
        on_change: Change callback
        error_text: Error message to display
        max_length: Maximum character length
        ref: Optional reference for the TextField

    Returns:
        Column with label and text field
    """
    colors = theme_manager.get_colors()

    label_text = f"{label} *" if required else label

    text_field = ft.TextField(
        ref=ref,
        value=value,
        hint_text=hint,
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=5 if multiline else 1,
        password=password,
        can_reveal_password=password,
        read_only=read_only,
        width=width,
        text_size=13,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=8,
        on_change=on_change,
        error_text=error_text,
        max_length=max_length,
    )

    return ft.Column(
        controls=[
            ft.Text(
                label_text,
                size=12,
                weight=ft.FontWeight.W_500,
                color=colors["text_secondary"],
            ),
            text_field,
        ],
        spacing=4,
    )


def create_dropdown(
    label: str,
    options: List[str],
    value: str = None,
    required: bool = False,
    width: Optional[int] = None,
    on_change: Optional[Callable] = None,
    hint: str = "Select...",
    ref: Optional[ft.Ref] = None,
) -> ft.Column:
    """
    Create a labeled dropdown.

    Args:
        label: Field label
        options: List of option strings
        value: Initial selected value
        required: Whether field is required
        width: Field width
        on_change: Change callback
        hint: Placeholder text
        ref: Optional reference

    Returns:
        Column with label and dropdown
    """
    colors = theme_manager.get_colors()

    label_text = f"{label} *" if required else label

    dropdown = ft.Dropdown(
        ref=ref,
        value=value,
        options=[ft.dropdown.Option(key=opt, text=opt) for opt in options],
        width=width,
        text_size=13,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
        border_radius=8,
        on_change=on_change,
        hint_text=hint,
    )

    return ft.Column(
        controls=[
            ft.Text(
                label_text,
                size=12,
                weight=ft.FontWeight.W_500,
                color=colors["text_secondary"],
            ),
            dropdown,
        ],
        spacing=4,
    )


def create_date_picker(
    label: str,
    value: datetime = None,
    required: bool = False,
    width: Optional[int] = None,
    on_change: Optional[Callable] = None,
    ref: Optional[ft.Ref] = None,
) -> ft.Column:
    """
    Create a labeled date picker.

    Args:
        label: Field label
        value: Initial date value
        required: Whether field is required
        width: Field width
        on_change: Change callback
        ref: Optional reference

    Returns:
        Column with label and date picker
    """
    colors = theme_manager.get_colors()

    label_text = f"{label} *" if required else label

    # Format date for display
    date_str = value.strftime("%d/%m/%Y") if value else ""

    date_field = ft.TextField(
        ref=ref,
        value=date_str,
        hint_text="DD/MM/YYYY",
        width=width,
        text_size=13,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=8,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, size=18, color=colors["text_secondary"]),
        on_change=on_change,
    )

    return ft.Column(
        controls=[
            ft.Text(
                label_text,
                size=12,
                weight=ft.FontWeight.W_500,
                color=colors["text_secondary"],
            ),
            date_field,
        ],
        spacing=4,
    )


def create_checkbox(
    label: str,
    value: bool = False,
    on_change: Optional[Callable] = None,
    ref: Optional[ft.Ref] = None,
) -> ft.Checkbox:
    """
    Create a checkbox.

    Args:
        label: Checkbox label
        value: Initial checked state
        on_change: Change callback
        ref: Optional reference

    Returns:
        Checkbox control
    """
    colors = theme_manager.get_colors()

    return ft.Checkbox(
        ref=ref,
        label=label,
        value=value,
        on_change=on_change,
        label_style=ft.TextStyle(
            size=13,
            color=colors["text_primary"],
        ),
    )


def create_radio_group(
    label: str,
    options: List[str],
    value: str = None,
    required: bool = False,
    on_change: Optional[Callable] = None,
    ref: Optional[ft.Ref] = None,
) -> ft.Column:
    """
    Create a labeled radio button group.

    Args:
        label: Group label
        options: List of option strings
        value: Initial selected value
        required: Whether field is required
        on_change: Change callback
        ref: Optional reference

    Returns:
        Column with label and radio group
    """
    colors = theme_manager.get_colors()

    label_text = f"{label} *" if required else label

    radio_group = ft.RadioGroup(
        ref=ref,
        value=value,
        content=ft.Row(
            controls=[
                ft.Radio(value=opt, label=opt)
                for opt in options
            ],
            spacing=16,
        ),
        on_change=on_change,
    )

    return ft.Column(
        controls=[
            ft.Text(
                label_text,
                size=12,
                weight=ft.FontWeight.W_500,
                color=colors["text_secondary"],
            ),
            radio_group,
        ],
        spacing=4,
    )


def create_form_row(*fields, spacing: int = 16) -> ft.Row:
    """
    Create a row of form fields.

    Args:
        *fields: Form field controls
        spacing: Spacing between fields

    Returns:
        Row containing the fields
    """
    return ft.Row(
        controls=list(fields),
        spacing=spacing,
        wrap=True,
    )


def create_form_section(
    title: str,
    *fields,
    icon: str = None,
    collapsed: bool = False,
) -> ft.Container:
    """
    Create a form section with title and fields.

    Args:
        title: Section title
        *fields: Form field controls
        icon: Optional icon
        collapsed: Start collapsed

    Returns:
        Container with section
    """
    colors = theme_manager.get_colors()

    header = ft.Row(
        controls=[
            ft.Icon(icon, size=18, color=colors["primary"]) if icon else ft.Container(),
            ft.Text(
                title,
                size=14,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
        ],
        spacing=8,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                header,
                ft.Divider(color=colors["border"], height=1),
                ft.Container(height=12),
                *fields,
            ],
            spacing=12,
        ),
        padding=16,
        border_radius=8,
        bgcolor=colors["card_bg"],
        border=ft.border.all(1, colors["card_border"]),
    )


class FormValidator:
    """Form validation helper."""

    @staticmethod
    def required(value: str, field_name: str = "This field") -> Optional[str]:
        """Validate required field."""
        if not value or not value.strip():
            return f"{field_name} is required"
        return None

    @staticmethod
    def min_length(value: str, length: int, field_name: str = "This field") -> Optional[str]:
        """Validate minimum length."""
        if value and len(value) < length:
            return f"{field_name} must be at least {length} characters"
        return None

    @staticmethod
    def max_length(value: str, length: int, field_name: str = "This field") -> Optional[str]:
        """Validate maximum length."""
        if value and len(value) > length:
            return f"{field_name} must be at most {length} characters"
        return None

    @staticmethod
    def numeric(value: str, field_name: str = "This field") -> Optional[str]:
        """Validate numeric value."""
        if value and not value.replace('.', '').replace('-', '').isdigit():
            return f"{field_name} must be a number"
        return None

    @staticmethod
    def date_format(value: str, format: str = "%d/%m/%Y", field_name: str = "This field") -> Optional[str]:
        """Validate date format."""
        if not value:
            return None
        try:
            datetime.strptime(value, format)
            return None
        except ValueError:
            return f"{field_name} must be in format DD/MM/YYYY"

    @staticmethod
    def pattern(value: str, pattern: str, message: str) -> Optional[str]:
        """Validate against regex pattern."""
        import re
        if value and not re.match(pattern, value):
            return message
        return None
