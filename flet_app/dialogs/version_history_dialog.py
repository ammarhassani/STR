"""
Version History Dialog for FIU Report Management System.
Shows version history with diff comparison, delete options, and activity log.
GitHub-style version management.
"""
import flet as ft
from typing import Optional, Any, Callable, List

from theme.theme_manager import theme_manager


def show_version_history_dialog(
    page: ft.Page,
    app_state: Any,
    report_id: int,
    on_restore: Optional[Callable[[], None]] = None,
    on_change: Optional[Callable[[], None]] = None,
):
    """
    Show the version history dialog with GitHub-style features.

    Args:
        page: Flet page object
        app_state: Application state with services
        report_id: ID of the report to show history for
        on_restore: Callback when a version is restored
        on_change: Callback when versions are modified (delete/restore)
    """
    colors = theme_manager.get_colors()

    version_service = app_state.version_service
    report_service = app_state.report_service
    logging_service = app_state.logging_service
    current_user = app_state.current_user
    is_admin = current_user and current_user.get('role') == 'admin'

    # State
    state = {
        "versions": [],
        "selected_versions": [],  # For comparison (up to 2)
        "show_deleted": False,
        "current_tab": "versions",  # "versions" or "activity"
        "activities": [],
    }

    def load_versions():
        """Load version history."""
        try:
            if version_service:
                state["versions"] = version_service.get_report_versions(
                    report_id,
                    include_deleted=state["show_deleted"]
                )
            else:
                state["versions"] = []
        except Exception as e:
            logging_service.error(f"Error loading versions: {e}")
            state["versions"] = []

        update_version_list()

    def load_activities():
        """Load activities for this report."""
        try:
            if app_state.activity_service:
                state["activities"] = app_state.activity_service.get_report_activities(
                    report_id, limit=50
                )
            else:
                state["activities"] = []
        except Exception as e:
            logging_service.error(f"Error loading activities: {e}")
            state["activities"] = []

        update_activity_list()

    def update_version_list():
        """Update the version list display."""
        version_list.controls.clear()

        if not state["versions"]:
            version_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY, color=colors["text_muted"], size=48),
                            ft.Text(
                                "No version history available",
                                color=colors["text_secondary"],
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=40,
                    alignment=ft.alignment.center,
                )
            )
        else:
            for version in state["versions"]:
                version_item = create_version_item(version)
                version_list.controls.append(version_item)

        # Update compare button state
        compare_btn.disabled = len(state["selected_versions"]) != 2
        compare_btn.text = f"Compare ({len(state['selected_versions'])}/2)"

        page.update()

    def update_activity_list():
        """Update the activity list display."""
        activity_list.controls.clear()

        if not state["activities"]:
            activity_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY, color=colors["text_muted"], size=48),
                            ft.Text(
                                "No activity recorded",
                                color=colors["text_secondary"],
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=40,
                    alignment=ft.alignment.center,
                )
            )
        else:
            from components.activity_timeline import ACTION_ICONS, ACTION_COLORS

            for activity in state["activities"]:
                action_type = activity.get('action_type', 'UPDATE')
                description = activity.get('description', '')
                relative_time = activity.get('relative_time', '')
                created_at = activity.get('created_at', '')

                icon = ACTION_ICONS.get(action_type, ft.Icons.INFO_OUTLINE)
                color = ACTION_COLORS.get(action_type, colors["text_secondary"])

                activity_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(icon, color=color, size=16),
                                    width=32,
                                    height=32,
                                    border_radius=16,
                                    bgcolor=f"{color}20",
                                    alignment=ft.alignment.center,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            description,
                                            size=13,
                                            color=colors["text_primary"],
                                        ),
                                        ft.Text(
                                            relative_time or created_at,
                                            size=11,
                                            color=colors["text_muted"],
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=12,
                        ),
                        padding=8,
                        border=ft.border.only(bottom=ft.BorderSide(1, colors["border"])),
                    )
                )

        page.update()

    def create_version_item(version: dict) -> ft.Container:
        """Create a version list item with selection and actions."""
        version_id = version.get('version_id', version.get('id'))
        version_num = version.get('version_number', '?')
        created_at = version.get('created_at', 'Unknown')
        created_by = version.get('created_by', 'Unknown')
        change_reason = version.get('change_reason', '')
        is_deleted = version.get('is_deleted', 0) == 1
        deleted_by = version.get('deleted_by', '')
        deleted_at = version.get('deleted_at', '')

        is_selected = version_id in state["selected_versions"]

        def toggle_selection(e, vid=version_id):
            """Toggle version selection for comparison."""
            if is_deleted:
                return  # Can't select deleted versions for comparison

            if vid in state["selected_versions"]:
                state["selected_versions"].remove(vid)
            else:
                if len(state["selected_versions"]) >= 2:
                    # Remove oldest selection
                    state["selected_versions"].pop(0)
                state["selected_versions"].append(vid)
            update_version_list()

        def handle_restore_version(e):
            """Restore this specific version (create new version from it)."""
            restore_version_by_id(version_id, version_num)

        def handle_delete_version(e):
            """Delete this version."""
            if is_deleted:
                # Restore deleted version
                restore_deleted_version(version_id, version_num)
            else:
                # Show delete options
                show_version_delete_options(version_id, version_num)

        # Action buttons (admin only for delete)
        action_buttons = [
            ft.IconButton(
                icon=ft.Icons.RESTORE,
                icon_color=colors["primary"],
                tooltip="Restore to this version",
                on_click=handle_restore_version,
                visible=not is_deleted,
            ),
        ]

        if is_admin:
            if is_deleted:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.UNDO,
                        icon_color=colors["success"],
                        tooltip="Undelete version",
                        on_click=handle_delete_version,
                    )
                )
            else:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=colors["danger"],
                        tooltip="Delete version",
                        on_click=handle_delete_version,
                    )
                )

        # Version badge color
        badge_color = colors["danger"] if is_deleted else (
            colors["primary"] if is_selected else colors["text_secondary"]
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    # Selection checkbox (for comparison)
                    ft.Checkbox(
                        value=is_selected,
                        on_change=toggle_selection,
                        disabled=is_deleted,
                        active_color=colors["primary"],
                    ) if not is_deleted else ft.Container(width=48),
                    # Version badge
                    ft.Container(
                        content=ft.Text(
                            f"v{version_num}",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        width=44,
                        height=44,
                        border_radius=22,
                        bgcolor=badge_color,
                        alignment=ft.alignment.center,
                    ),
                    # Version info
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        f"Version {version_num}",
                                        size=14,
                                        weight=ft.FontWeight.W_500,
                                        color=colors["text_muted"] if is_deleted else colors["text_primary"],
                                        style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_deleted else None,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            "DELETED",
                                            size=10,
                                            color=colors["danger"],
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=4,
                                        bgcolor=f"{colors['danger']}20",
                                        visible=is_deleted,
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.Text(
                                f"By {created_by} on {created_at}",
                                size=12,
                                color=colors["text_secondary"],
                            ),
                            ft.Text(
                                change_reason or "No description",
                                size=11,
                                color=colors["text_muted"],
                                italic=True,
                            ) if change_reason else ft.Container(),
                            ft.Text(
                                f"Deleted by {deleted_by} on {deleted_at}",
                                size=11,
                                color=colors["danger"],
                                italic=True,
                            ) if is_deleted and deleted_by else ft.Container(),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    # Action buttons
                    ft.Row(
                        controls=action_buttons,
                        spacing=0,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.all(12),
            border_radius=8,
            bgcolor=f"{colors['danger']}10" if is_deleted else (
                colors["bg_tertiary"] if is_selected else "transparent"
            ),
            border=ft.border.all(
                1,
                colors["danger"] if is_deleted else (
                    colors["primary"] if is_selected else colors["border"]
                )
            ),
            opacity=0.7 if is_deleted else 1.0,
        )

    def show_version_delete_options(version_id: int, version_num: int):
        """Show delete options for a version."""
        from dialogs.delete_confirmation_dialog import show_version_delete_dialog

        # Get report info
        report = report_service.get_report(report_id) if report_service else {}
        report_number = report.get('report_number', str(report_id))

        def on_soft_delete():
            try:
                success, message = version_service.soft_delete_version(
                    version_id,
                    current_user['username'],
                    "User requested deletion"
                )
                if success:
                    show_success(message)
                    load_versions()
                    if on_change:
                        on_change()
                else:
                    show_error(message)
            except Exception as e:
                show_error(f"Failed to delete version: {str(e)}")

        def on_hard_delete():
            try:
                success, message = version_service.hard_delete_version(
                    version_id,
                    current_user['username'],
                    "User requested permanent deletion"
                )
                if success:
                    show_success(message)
                    state["selected_versions"] = [v for v in state["selected_versions"] if v != version_id]
                    load_versions()
                    if on_change:
                        on_change()
                else:
                    show_error(message)
            except Exception as e:
                show_error(f"Failed to permanently delete version: {str(e)}")

        show_version_delete_dialog(
            page=page,
            app_state=app_state,
            version_id=version_id,
            version_number=version_num,
            report_number=report_number,
            on_soft_delete=on_soft_delete,
            on_hard_delete=on_hard_delete,
        )

    def restore_deleted_version(version_id: int, version_num: int):
        """Restore a soft-deleted version."""
        try:
            success, message = version_service.restore_deleted_version(
                version_id,
                current_user['username']
            )
            if success:
                show_success(message)
                load_versions()
                if on_change:
                    on_change()
            else:
                show_error(message)
        except Exception as e:
            show_error(f"Failed to restore version: {str(e)}")

    def restore_version_by_id(version_id: int, version_num: int):
        """Restore the report to a specific version (creates new version)."""
        def confirm_restore(e):
            confirm_dialog.open = False
            page.update()

            try:
                if version_service:
                    success, message = version_service.restore_version(
                        version_id,
                        current_user['username']
                    )

                    if success:
                        show_success(message)
                        load_versions()
                        if on_restore:
                            on_restore()
                        if on_change:
                            on_change()
                    else:
                        show_error(message)
                else:
                    show_error("Version service not available")

            except Exception as ex:
                show_error(f"Failed to restore version: {str(ex)}")

        def cancel_restore(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.RESTORE, color=colors["primary"], size=24),
                    ft.Text("Confirm Restore", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Text(
                f"Are you sure you want to restore to Version {version_num}?\n\n"
                "This will create a new version with the restored data.\n"
                "The current version will be preserved in history."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_restore),
                ft.ElevatedButton(
                    "Restore",
                    icon=ft.Icons.RESTORE,
                    bgcolor=colors["primary"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_restore,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def compare_versions(e):
        """Compare the two selected versions."""
        if len(state["selected_versions"]) != 2:
            show_error("Please select exactly 2 versions to compare")
            return

        from dialogs.diff_view_dialog import show_diff_view_dialog

        # Sort by version_id to show older first
        sorted_ids = sorted(state["selected_versions"])

        show_diff_view_dialog(
            page=page,
            app_state=app_state,
            version_id_1=sorted_ids[0],
            version_id_2=sorted_ids[1],
        )

    def toggle_show_deleted(e):
        """Toggle showing deleted versions."""
        state["show_deleted"] = e.control.value
        state["selected_versions"] = []  # Clear selection
        load_versions()

    def switch_tab(tab: str):
        """Switch between versions and activity tabs."""
        state["current_tab"] = tab
        versions_tab_btn.bgcolor = colors["primary"] if tab == "versions" else colors["bg_tertiary"]
        versions_tab_btn.color = ft.Colors.WHITE if tab == "versions" else colors["text_primary"]
        activity_tab_btn.bgcolor = colors["primary"] if tab == "activity" else colors["bg_tertiary"]
        activity_tab_btn.color = ft.Colors.WHITE if tab == "activity" else colors["text_primary"]

        # Control container visibility (not just list visibility)
        if version_container_ref.current:
            version_container_ref.current.visible = tab == "versions"
        if activity_container_ref.current:
            activity_container_ref.current.visible = tab == "activity"
        version_controls.visible = tab == "versions"

        if tab == "activity" and not state["activities"]:
            load_activities()

        page.update()

    def show_error(message: str):
        """Show error snackbar."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=colors["danger"],
        )
        page.snack_bar.open = True
        page.update()

    def show_success(message: str):
        """Show success snackbar."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=colors["success"],
        )
        page.snack_bar.open = True
        page.update()

    def close_dialog(e):
        """Close the dialog."""
        dialog.open = False
        page.update()

    # Tab buttons
    versions_tab_btn = ft.ElevatedButton(
        "Versions",
        icon=ft.Icons.HISTORY,
        bgcolor=colors["primary"],
        color=ft.Colors.WHITE,
        on_click=lambda e: switch_tab("versions"),
    )

    activity_tab_btn = ft.ElevatedButton(
        "Activity",
        icon=ft.Icons.TIMELINE,
        bgcolor=colors["bg_tertiary"],
        color=colors["text_primary"],
        on_click=lambda e: switch_tab("activity"),
    )

    # Compare button
    compare_btn = ft.ElevatedButton(
        "Compare (0/2)",
        icon=ft.Icons.COMPARE_ARROWS,
        bgcolor=colors["bg_tertiary"],
        color=colors["text_primary"],
        disabled=True,
        on_click=compare_versions,
    )

    # Refs for container visibility control
    version_container_ref = ft.Ref[ft.Container]()
    activity_container_ref = ft.Ref[ft.Container]()

    # Build version list
    version_list = ft.Column(
        controls=[
            ft.Container(
                content=ft.ProgressRing(width=32, height=32),
                alignment=ft.alignment.center,
                padding=20,
            )
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build activity list
    activity_list = ft.Column(
        controls=[],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Version controls (show deleted toggle, compare button)
    version_controls = ft.Row(
        controls=[
            compare_btn,
            ft.Container(expand=True),
            ft.Switch(
                label="Show Deleted",
                value=False,
                on_change=toggle_show_deleted,
                active_color=colors["primary"],
            ) if is_admin else ft.Container(),
        ],
        spacing=8,
    )

    # Create dialog content
    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.Text(
                            "Version History",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=colors["text_secondary"],
                            on_click=close_dialog,
                        ),
                    ],
                ),
                ft.Text(
                    "Compare versions, view changes, or restore previous states",
                    size=13,
                    color=colors["text_secondary"],
                ),
                # Tab buttons
                ft.Row(
                    controls=[versions_tab_btn, activity_tab_btn],
                    spacing=8,
                ),
                ft.Divider(color=colors["border"]),
                # Version controls
                version_controls,
                # Content area - use Column with visibility instead of Stack to avoid click blocking
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                ref=version_container_ref,
                                content=version_list,
                                border=ft.border.all(1, colors["border"]),
                                border_radius=8,
                                expand=True,
                                visible=True,  # Controlled by switch_tab
                            ),
                            ft.Container(
                                ref=activity_container_ref,
                                content=activity_list,
                                border=ft.border.all(1, colors["border"]),
                                border_radius=8,
                                expand=True,
                                visible=False,  # Controlled by switch_tab
                            ),
                        ],
                        expand=True,
                    ),
                    expand=True,
                ),
                # Footer buttons
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Close",
                            on_click=close_dialog,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=12,
        ),
        width=600,
        height=600,
        padding=24,
    )

    # Create dialog
    dialog = ft.AlertDialog(
        modal=True,
        content=dialog_content,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    # Show dialog
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    # Load versions
    load_versions()
