"""
Login View for FIU Report Management System.
Flet-based authentication interface.
"""
import flet as ft
import asyncio
from typing import Callable, Optional, Any

from theme.theme_manager import theme_manager
from theme.colors import Colors
from components.toast import show_error


def build_login_view(
    page: ft.Page,
    app_state: Any,
    on_login_success: Callable[[dict], None]
) -> ft.View:
    """
    Build the login view.

    Args:
        page: Flet page object
        app_state: Application state object
        on_login_success: Callback when login is successful

    Returns:
        ft.View: The login view
    """
    # Get theme colors
    colors = theme_manager.get_colors()

    # State
    is_loading = False
    error_message = ""

    # Create refs for controls we need to update
    username_ref = ft.Ref[ft.TextField]()
    password_ref = ft.Ref[ft.TextField]()
    login_btn_ref = ft.Ref[ft.ElevatedButton]()
    error_text_ref = ft.Ref[ft.Text]()
    error_container_ref = ft.Ref[ft.Container]()

    def set_loading(loading: bool):
        """Set loading state."""
        nonlocal is_loading
        is_loading = loading

        if username_ref.current:
            username_ref.current.disabled = loading
        if password_ref.current:
            password_ref.current.disabled = loading
        if login_btn_ref.current:
            login_btn_ref.current.disabled = loading
            login_btn_ref.current.text = "Logging in..." if loading else "Login"

        page.update()

    def show_login_error(message: str):
        """Show error message."""
        nonlocal error_message
        error_message = message

        if error_text_ref.current:
            error_text_ref.current.value = message
        if error_container_ref.current:
            error_container_ref.current.visible = True

        page.update()

    def hide_login_error():
        """Hide error message."""
        nonlocal error_message
        error_message = ""

        if error_container_ref.current:
            error_container_ref.current.visible = False

        page.update()

    async def do_login():
        """Perform login asynchronously."""
        username = username_ref.current.value.strip() if username_ref.current else ""
        password = password_ref.current.value if password_ref.current else ""

        # Validation
        if not username:
            show_login_error("Please enter your username")
            if username_ref.current:
                username_ref.current.focus()
            return

        if not password:
            show_login_error("Please enter your password")
            if password_ref.current:
                password_ref.current.focus()
            return

        # Set loading state
        set_loading(True)
        hide_login_error()

        try:
            # Run authentication in executor to not block UI
            loop = asyncio.get_event_loop()
            success, user, message = await loop.run_in_executor(
                None,
                app_state.auth_service.authenticate,
                username,
                password
            )

            if success:
                # Login successful
                app_state.login(user)
                on_login_success(user)
            else:
                # Login failed
                show_login_error(message or "Invalid username or password")
                if password_ref.current:
                    password_ref.current.value = ""
                    password_ref.current.focus()
                set_loading(False)

        except Exception as e:
            show_login_error(f"Authentication error: {str(e)}")
            set_loading(False)

    def handle_login(e):
        """Handle login button click."""
        page.run_task(do_login)

    def handle_key_press(e: ft.KeyboardEvent):
        """Handle keyboard events."""
        if e.key == "Enter":
            handle_login(e)

    # Build the UI
    login_card = ft.Container(
        content=ft.Column(
            controls=[
                # Title
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "FIU Report\nManagement System",
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                                color=colors["text_primary"],
                            ),
                            ft.Text(
                                "Financial Intelligence Unit",
                                size=14,
                                color=colors["text_secondary"],
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    margin=ft.margin.only(bottom=30),
                ),

                # Username field
                ft.Text(
                    "Username",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=colors["text_secondary"],
                ),
                ft.TextField(
                    ref=username_ref,
                    hint_text="Enter your username",
                    border_radius=8,
                    height=50,
                    text_size=14,
                    content_padding=ft.padding.symmetric(horizontal=16, vertical=0),
                    on_submit=handle_login,
                    autofocus=True,
                ),

                ft.Container(height=8),

                # Password field
                ft.Text(
                    "Password",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=colors["text_secondary"],
                ),
                ft.TextField(
                    ref=password_ref,
                    hint_text="Enter your password",
                    password=True,
                    can_reveal_password=True,
                    border_radius=8,
                    height=50,
                    text_size=14,
                    content_padding=ft.padding.symmetric(horizontal=16, vertical=0),
                    on_submit=handle_login,
                ),

                # Error message
                ft.Container(
                    ref=error_container_ref,
                    content=ft.Text(
                        ref=error_text_ref,
                        value="",
                        color=colors["danger"],
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    visible=False,
                    margin=ft.margin.only(top=10),
                    alignment=ft.alignment.center,
                ),

                ft.Container(height=16),

                # Login button
                ft.ElevatedButton(
                    ref=login_btn_ref,
                    text="Login",
                    width=float("inf"),
                    height=48,
                    style=ft.ButtonStyle(
                        color=ft.Colors.WHITE,
                        bgcolor=colors["primary"],
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=handle_login,
                ),

                # Spacer
                ft.Container(expand=True),

                # Version
                ft.Text(
                    "Version 2.0.0",
                    size=11,
                    color=colors["text_muted"],
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        width=420,
        height=520,
        padding=40,
        border_radius=12,
        bgcolor=colors["card_bg"],
        border=ft.border.all(1, colors["border"]),
    )

    # Main container with centered login card
    main_content = ft.Container(
        content=login_card,
        expand=True,
        alignment=ft.alignment.center,
        bgcolor=colors["bg_primary"],
    )

    return ft.View(
        route="/login",
        controls=[main_content],
        padding=0,
        spacing=0,
        bgcolor=colors["bg_primary"],
    )


class LoginView:
    """
    Login view class for more complex state management.
    Alternative to the function-based approach.
    """

    def __init__(self, page: ft.Page, app_state: Any, on_login_success: Callable):
        self.page = page
        self.app_state = app_state
        self.on_login_success = on_login_success
        self.is_loading = False

        # Build controls
        self._build()

    def _build(self):
        """Build the view controls."""
        colors = theme_manager.get_colors()

        self.username_field = ft.TextField(
            hint_text="Enter your username",
            border_radius=8,
            height=50,
            text_size=14,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=0),
            on_submit=self._handle_login,
            autofocus=True,
        )

        self.password_field = ft.TextField(
            hint_text="Enter your password",
            password=True,
            can_reveal_password=True,
            border_radius=8,
            height=50,
            text_size=14,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=0),
            on_submit=self._handle_login,
        )

        self.error_text = ft.Text(
            value="",
            color=colors["danger"],
            size=13,
            text_align=ft.TextAlign.CENTER,
        )

        self.error_container = ft.Container(
            content=self.error_text,
            visible=False,
            margin=ft.margin.only(top=10),
            alignment=ft.alignment.center,
        )

        self.login_button = ft.ElevatedButton(
            text="Login",
            width=float("inf"),
            height=48,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=colors["primary"],
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self._handle_login,
        )

        self.login_card = ft.Container(
            content=ft.Column(
                controls=[
                    # Title
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "FIU Report\nManagement System",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER,
                                    color=colors["text_primary"],
                                ),
                                ft.Text(
                                    "Financial Intelligence Unit",
                                    size=14,
                                    color=colors["text_secondary"],
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        margin=ft.margin.only(bottom=30),
                    ),
                    ft.Text("Username", size=13, weight=ft.FontWeight.W_600, color=colors["text_secondary"]),
                    self.username_field,
                    ft.Container(height=8),
                    ft.Text("Password", size=13, weight=ft.FontWeight.W_600, color=colors["text_secondary"]),
                    self.password_field,
                    self.error_container,
                    ft.Container(height=16),
                    self.login_button,
                    ft.Container(expand=True),
                    ft.Text("Version 2.0.0", size=11, color=colors["text_muted"], text_align=ft.TextAlign.CENTER),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=420,
            height=520,
            padding=40,
            border_radius=12,
            bgcolor=colors["card_bg"],
            border=ft.border.all(1, colors["border"]),
        )

    def _set_loading(self, loading: bool):
        """Set loading state."""
        self.is_loading = loading
        self.username_field.disabled = loading
        self.password_field.disabled = loading
        self.login_button.disabled = loading
        self.login_button.text = "Logging in..." if loading else "Login"
        self.page.update()

    def _show_error(self, message: str):
        """Show error message."""
        self.error_text.value = message
        self.error_container.visible = True
        self.page.update()

    def _hide_error(self):
        """Hide error message."""
        self.error_container.visible = False
        self.page.update()

    def _handle_login(self, e):
        """Handle login."""
        self.page.run_task(self._do_login)

    async def _do_login(self):
        """Perform login asynchronously."""
        username = self.username_field.value.strip() if self.username_field.value else ""
        password = self.password_field.value if self.password_field.value else ""

        if not username:
            self._show_error("Please enter your username")
            self.username_field.focus()
            return

        if not password:
            self._show_error("Please enter your password")
            self.password_field.focus()
            return

        self._set_loading(True)
        self._hide_error()

        try:
            loop = asyncio.get_event_loop()
            success, user, message = await loop.run_in_executor(
                None,
                self.app_state.auth_service.authenticate,
                username,
                password
            )

            if success:
                self.app_state.login(user)
                self.on_login_success(user)
            else:
                self._show_error(message or "Invalid username or password")
                self.password_field.value = ""
                self.password_field.focus()
                self._set_loading(False)

        except Exception as ex:
            self._show_error(f"Authentication error: {str(ex)}")
            self._set_loading(False)

    def build(self) -> ft.View:
        """Build and return the view."""
        colors = theme_manager.get_colors()

        return ft.View(
            route="/login",
            controls=[
                ft.Container(
                    content=self.login_card,
                    expand=True,
                    alignment=ft.alignment.center,
                    bgcolor=colors["bg_primary"],
                )
            ],
            padding=0,
            spacing=0,
            bgcolor=colors["bg_primary"],
        )
