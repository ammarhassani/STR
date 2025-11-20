"""
UI Widgets Package
Exports both individual widget components and view widgets.
"""

# The widgets.py file is at ui/widgets.py (sibling to this package)
# We need to import from parent level with a different name to avoid conflict

# Solution: Import specific classes from the parent's widgets module
# This avoids the naming conflict between ui.widgets (package) and ui/widgets.py (module)

try:
    # Try to import from the widgets.py file at the parent ui level
    # We do this by going up one level (..) and importing from widgets
    import importlib.util
    import sys
    from pathlib import Path

    # Get the path to ui/widgets.py
    widgets_file_path = Path(__file__).parent.parent / "widgets.py"

    if widgets_file_path.exists():
        # Load the module from file
        spec = importlib.util.spec_from_file_location("ui_widgets_module", widgets_file_path)
        widgets_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(widgets_module)

        # Export the classes
        StatCard = widgets_module.StatCard
        ModernButton = widgets_module.ModernButton
        SearchBar = widgets_module.SearchBar
        StatusBadge = widgets_module.StatusBadge
    else:
        raise ImportError("widgets.py file not found")

except Exception as e:
    # Fallback: define placeholder classes if import fails
    from PyQt6.QtWidgets import QFrame, QPushButton, QLineEdit, QLabel

    print(f"Warning: Could not import from widgets.py: {e}")

    class StatCard(QFrame):
        def __init__(self, title="", value=0, icon="", color="#000", parent=None):
            super().__init__(parent)

    class ModernButton(QPushButton):
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)

    class SearchBar(QLineEdit):
        def __init__(self, parent=None):
            super().__init__(parent)

    class StatusBadge(QLabel):
        def __init__(self, text="", status="info", parent=None):
            super().__init__(text, parent)

# Import view widgets from this package
from .dashboard_view import DashboardView
from .reports_view import ReportsView
from .admin_panel import AdminPanel
from .approval_panel import ApprovalPanel
from .export_view import ExportView
from .settings_view import SettingsView
from .log_management_view import LogManagementView

__all__ = [
    'StatCard',
    'ModernButton',
    'SearchBar',
    'StatusBadge',
    'DashboardView',
    'ReportsView',
    'AdminPanel',
    'ApprovalPanel',
    'ExportView',
    'SettingsView',
    'LogManagementView',
]
