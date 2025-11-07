"""
Keyboard Shortcuts Service
Manages application-wide keyboard shortcuts and provides a centralized registry.
"""

from PyQt6.QtGui import QKeySequence, QShortcut, QAction
from PyQt6.QtCore import Qt, QObject
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass


@dataclass
class ShortcutInfo:
    """Information about a keyboard shortcut."""
    key_sequence: str
    description: str
    category: str
    action: Optional[Callable] = None


class KeyboardShortcutsService(QObject):
    """
    Service for managing keyboard shortcuts across the application.

    Features:
    - Centralized shortcut registration
    - Category-based organization
    - Context-aware shortcuts
    - Customizable key bindings
    - Help documentation generation
    """

    def __init__(self):
        """Initialize keyboard shortcuts service."""
        super().__init__()
        self.shortcuts: Dict[str, ShortcutInfo] = {}
        self.registered_shortcuts: Dict[str, QShortcut] = {}
        self.registered_actions: Dict[str, QAction] = {}

        # Define default shortcuts
        self._define_default_shortcuts()

    def _define_default_shortcuts(self):
        """Define default application shortcuts."""

        # Navigation shortcuts
        self.register_shortcut_info(
            "dashboard",
            "Ctrl+D",
            "Go to Dashboard",
            "Navigation"
        )

        self.register_shortcut_info(
            "reports",
            "Ctrl+R",
            "Go to Reports",
            "Navigation"
        )

        self.register_shortcut_info(
            "export",
            "Ctrl+E",
            "Go to Export",
            "Navigation"
        )

        self.register_shortcut_info(
            "settings",
            "Ctrl+,",
            "Open Settings",
            "Navigation"
        )

        # Actions
        self.register_shortcut_info(
            "new_report",
            "Ctrl+N",
            "Create New Report",
            "Actions"
        )

        self.register_shortcut_info(
            "save",
            "Ctrl+S",
            "Save Current Item",
            "Actions"
        )

        self.register_shortcut_info(
            "refresh",
            "F5",
            "Refresh Current View",
            "Actions"
        )

        self.register_shortcut_info(
            "search",
            "Ctrl+F",
            "Focus Search Box",
            "Actions"
        )

        self.register_shortcut_info(
            "clear_filters",
            "Ctrl+Shift+C",
            "Clear All Filters",
            "Actions"
        )

        self.register_shortcut_info(
            "export_excel",
            "Ctrl+Shift+E",
            "Export to Excel",
            "Actions"
        )

        # System
        self.register_shortcut_info(
            "help",
            "F1",
            "Open Help",
            "System"
        )

        self.register_shortcut_info(
            "quit",
            "Ctrl+Q",
            "Quit Application",
            "System"
        )

        self.register_shortcut_info(
            "toggle_theme",
            "Ctrl+T",
            "Toggle Dark/Light Theme",
            "System"
        )

        self.register_shortcut_info(
            "profile",
            "Ctrl+P",
            "Open User Profile",
            "System"
        )

        # Window management
        self.register_shortcut_info(
            "close_dialog",
            "Esc",
            "Close Current Dialog",
            "Window"
        )

        self.register_shortcut_info(
            "next_tab",
            "Ctrl+Tab",
            "Next Tab",
            "Window"
        )

        self.register_shortcut_info(
            "prev_tab",
            "Ctrl+Shift+Tab",
            "Previous Tab",
            "Window"
        )

        # Table navigation
        self.register_shortcut_info(
            "select_all",
            "Ctrl+A",
            "Select All",
            "Table"
        )

        self.register_shortcut_info(
            "delete",
            "Delete",
            "Delete Selected Item",
            "Table"
        )

        self.register_shortcut_info(
            "edit",
            "Enter",
            "Edit Selected Item",
            "Table"
        )

    def register_shortcut_info(
        self,
        shortcut_id: str,
        key_sequence: str,
        description: str,
        category: str
    ):
        """
        Register shortcut information.

        Args:
            shortcut_id: Unique identifier for the shortcut
            key_sequence: Key sequence (e.g., "Ctrl+N")
            description: Human-readable description
            category: Category for organization
        """
        self.shortcuts[shortcut_id] = ShortcutInfo(
            key_sequence=key_sequence,
            description=description,
            category=category
        )

    def create_shortcut(
        self,
        widget,
        shortcut_id: str,
        callback: Callable,
        context: Qt.ShortcutContext = Qt.ShortcutContext.WindowShortcut
    ) -> Optional[QShortcut]:
        """
        Create and register a keyboard shortcut.

        Args:
            widget: Parent widget for the shortcut
            shortcut_id: Registered shortcut identifier
            callback: Function to call when shortcut is triggered
            context: Shortcut context (Window, Application, etc.)

        Returns:
            QShortcut instance or None if shortcut_id not found
        """
        if shortcut_id not in self.shortcuts:
            return None

        shortcut_info = self.shortcuts[shortcut_id]

        # Create shortcut
        shortcut = QShortcut(QKeySequence(shortcut_info.key_sequence), widget)
        shortcut.setContext(context)
        shortcut.activated.connect(callback)

        # Store reference
        key = f"{shortcut_id}_{id(widget)}"
        self.registered_shortcuts[key] = shortcut

        return shortcut

    def create_action(
        self,
        shortcut_id: str,
        callback: Callable,
        parent=None
    ) -> Optional[QAction]:
        """
        Create a QAction with the registered shortcut.

        Args:
            shortcut_id: Registered shortcut identifier
            callback: Function to call when action is triggered
            parent: Parent object for the action

        Returns:
            QAction instance or None if shortcut_id not found
        """
        if shortcut_id not in self.shortcuts:
            return None

        shortcut_info = self.shortcuts[shortcut_id]

        action = QAction(shortcut_info.description, parent)
        action.setShortcut(QKeySequence(shortcut_info.key_sequence))
        action.triggered.connect(callback)

        # Store reference
        key = f"{shortcut_id}_{id(parent)}"
        self.registered_actions[key] = action

        return action

    def get_shortcut_key(self, shortcut_id: str) -> Optional[str]:
        """
        Get the key sequence for a shortcut.

        Args:
            shortcut_id: Shortcut identifier

        Returns:
            Key sequence string or None
        """
        if shortcut_id in self.shortcuts:
            return self.shortcuts[shortcut_id].key_sequence
        return None

    def get_shortcut_description(self, shortcut_id: str) -> Optional[str]:
        """
        Get the description for a shortcut.

        Args:
            shortcut_id: Shortcut identifier

        Returns:
            Description string or None
        """
        if shortcut_id in self.shortcuts:
            return self.shortcuts[shortcut_id].description
        return None

    def get_shortcuts_by_category(self, category: str) -> Dict[str, ShortcutInfo]:
        """
        Get all shortcuts in a category.

        Args:
            category: Category name

        Returns:
            Dictionary of shortcut_id to ShortcutInfo
        """
        return {
            sid: info for sid, info in self.shortcuts.items()
            if info.category == category
        }

    def get_all_categories(self) -> List[str]:
        """
        Get list of all shortcut categories.

        Returns:
            List of category names
        """
        categories = set(info.category for info in self.shortcuts.values())
        return sorted(categories)

    def get_all_shortcuts(self) -> Dict[str, ShortcutInfo]:
        """
        Get all registered shortcuts.

        Returns:
            Dictionary of all shortcuts
        """
        return self.shortcuts.copy()

    def generate_help_html(self) -> str:
        """
        Generate HTML documentation for all shortcuts.

        Returns:
            HTML string with formatted shortcut documentation
        """
        html = """
        <html>
        <head>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 20px;
                }
                h2 {
                    color: #0d7377;
                    border-bottom: 2px solid #0d7377;
                    padding-bottom: 8px;
                    margin-top: 24px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 24px;
                }
                th {
                    background-color: #0d7377;
                    color: white;
                    padding: 10px;
                    text-align: left;
                    font-weight: 600;
                }
                td {
                    padding: 8px 10px;
                    border-bottom: 1px solid #e0e0e0;
                }
                .key {
                    background-color: #f5f5f5;
                    border: 1px solid #d0d0d0;
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-family: 'Courier New', monospace;
                    font-weight: 600;
                    color: #333;
                }
            </style>
        </head>
        <body>
            <h1>Keyboard Shortcuts Reference</h1>
        """

        # Group by category
        for category in self.get_all_categories():
            html += f"<h2>{category}</h2>\n<table>\n"
            html += "<tr><th>Shortcut</th><th>Description</th></tr>\n"

            shortcuts = self.get_shortcuts_by_category(category)
            for shortcut_id, info in shortcuts.items():
                html += f"<tr>\n"
                html += f'  <td><span class="key">{info.key_sequence}</span></td>\n'
                html += f"  <td>{info.description}</td>\n"
                html += f"</tr>\n"

            html += "</table>\n"

        html += """
        </body>
        </html>
        """

        return html
