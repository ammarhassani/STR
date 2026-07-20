"""
Login View for FIU Report Management System.
Flet-based authentication interface.
"""
import flet as ft
from components.overlay import (mount as _overlay_mount,
                                dismiss as _overlay_dismiss)
import asyncio
from typing import Callable, Optional, Any

from theme.theme_manager import theme_manager
from theme.colors import Colors
from components.toast import show_error
from components.app_button import app_button
from components.branding import logo_image
from i18n import t


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
            border_radius=4,
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
            border_radius=4,
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
            text=t("login.button"),
            width=float("inf"),
            height=48,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=colors["primary"],
                shape=ft.RoundedRectangleBorder(radius=4),
                elevation=0,
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
                                logo_image(72),
                                ft.Container(height=12),
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
                    ft.Text(t("login.user_id"), size=13, weight=ft.FontWeight.W_600, color=colors["text_secondary"]),
                    self.username_field,
                    ft.Container(height=8),
                    ft.Text(t("login.password"), size=13, weight=ft.FontWeight.W_600, color=colors["text_secondary"]),
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
        self.login_button.text = "Logging in..." if loading else t("login.button")
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
            self._show_error(t("login.err.enter_user_id"))
            self.username_field.focus()
            return

        # Two-way handshake (#1): route a not-yet-registered ID to self-registration.
        self._set_loading(True)
        self._hide_error()
        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, self.app_state.get_onboarding_status, username)
        except Exception:
            status = "active"
        if status == "pending":
            self._set_loading(False)
            self._show_registration_dialog(username)
            return

        if not password:
            self._set_loading(False)
            self._show_error(t("login.err.enter_password"))
            self.password_field.focus()
            return

        try:
            loop = asyncio.get_event_loop()
            success, user, message = await loop.run_in_executor(
                None,
                self.app_state.authenticate,
                username,
                password
            )

            if success:
                self.app_state.login(user)
                self.on_login_success(user)
            else:
                self._show_error(message if message and message != "ONBOARDING_REQUIRED"
                                 else t("login.err.invalid"))
                self.password_field.value = ""
                self.password_field.focus()
                self._set_loading(False)

        except Exception as ex:
            self._show_error(f"Authentication error: {str(ex)}")
            self._set_loading(False)

    def _show_registration_dialog(self, username: str):
        """Two-way handshake (#1): the user sets their OWN name + password. The
        admin never learns it."""
        colors = theme_manager.get_colors()
        danger = colors.get("danger", "#d32f2f")
        fullname = ft.TextField(label=t("onboard.full_name"), text_size=13)
        pw = ft.TextField(label=t("onboard.new_password"), password=True, can_reveal_password=True, text_size=13)
        confirm = ft.TextField(label=t("onboard.confirm_password"), password=True, can_reveal_password=True, text_size=13)
        err = ft.Text("", color=danger, size=12, visible=False)

        def _err(msg):
            err.value = msg; err.visible = True; self.page.update()

        async def _register():
            name = (fullname.value or "").strip()
            p1 = pw.value or ""
            p2 = confirm.value or ""
            if not name:
                _err(t("onboard.err.name")); return
            if len(p1) < 8:
                _err(t("onboard.err.pw_len")); return
            if p1 != p2:
                _err(t("onboard.err.mismatch")); return
            loop = asyncio.get_event_loop()
            ok, msg = await loop.run_in_executor(None, self.app_state.complete_onboarding, username, name, p1)
            if not ok:
                _err(msg or "Could not complete registration."); return
            dlg.open = False
            _overlay_dismiss(self.page, dlg)
            self.page.update()
            success, user, m = await loop.run_in_executor(None, self.app_state.authenticate, username, p1)
            if success:
                self.app_state.login(user)
                self.on_login_success(user)
            else:
                self._show_error(m or "Registration complete — please log in.")

        def submit(e):
            self.page.run_task(_register)

        def cancel(e):
            # page.update() alone leaves the barrier up -- see components/overlay.
            dlg.open = False
            _overlay_dismiss(self.page, dlg)
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("onboard.title")),
            content=ft.Container(width=380, content=ft.Column(controls=[
                ft.Text(t("onboard.user_id", username=username), size=12,
                        weight=ft.FontWeight.W_600, color=colors.get("text_primary")),
                ft.Text(t("onboard.instruction"), size=12, color=colors.get("text_secondary")),
                fullname, pw, confirm,
                err,
            ], tight=True, spacing=10)),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=cancel),
                ft.ElevatedButton(t("onboard.submit"), on_click=submit,
                                  bgcolor=colors.get("primary"), color=ft.Colors.WHITE),
            ],
        )
        confirm.on_submit = submit
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _open_control_panel(self, e):
        """Open the operator Control Panel in a second window.

        It lives on the LOGIN screen deliberately. The panel answers "why isn't
        this working?", and the moments that matters most -- the share is
        unreachable, no host is running, this PC was never set up -- are exactly
        the moments nobody can get past this screen. Reaching it must not
        require logging in, and must not require a shortcut or a typed flag.
        """
        import os as _os
        import subprocess
        import sys as _sys
        env = None
        try:
            if getattr(_sys, "frozen", False):
                cmd = [_sys.executable, "--panel"]
                # This is the one genuine self-spawn in the app, and the panel
                # is designed to OUTLIVE it. Without the reset, the child
                # inherits the bootloader's handoff variables, runs out of the
                # parent's _MEIxxxxx directory, and the parent deletes that
                # directory on exit -- the surviving panel then dies on its next
                # lazy import with a missing base_library.zip. PyInstaller
                # documents this exact case (independent subprocess).
                env = {**_os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
            else:
                main_py = _os.path.join(_os.path.dirname(_os.path.dirname(
                    _os.path.abspath(__file__))), "main.py")
                cmd = [_sys.executable, main_py, "--panel"]
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception as ex:
            from components.toast import show_error
            show_error(self.page, f"Could not open the Control Panel: {ex}")

    def build(self) -> ft.View:
        """Build and return the view."""
        colors = theme_manager.get_colors()

        return ft.View(
            route="/login",
            controls=[
                # A Stack, not two siblings in a column: the login card is
                # expand=True and would push anything after it off-screen.
                ft.Stack(
                    expand=True,
                    controls=[
                        ft.Container(
                            content=self.login_card,
                            expand=True,
                            alignment=ft.alignment.center,
                            bgcolor=colors["bg_primary"],
                        ),
                        ft.Container(
                            content=ft.TextButton(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.BUILD_CIRCLE, size=15,
                                            color=colors["text_muted"]),
                                    ft.Text("Control Panel", size=12,
                                            color=colors["text_muted"]),
                                ], spacing=6, tight=True),
                                on_click=self._open_control_panel,
                                tooltip="Check whether STR is working on this PC",
                            ),
                            alignment=ft.alignment.bottom_right,
                            padding=ft.padding.only(right=14, bottom=10),
                        ),
                    ],
                ),
            ],
            padding=0,
            spacing=0,
            bgcolor=colors["bg_primary"],
        )
