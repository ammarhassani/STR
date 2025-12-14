"""
Table Utilities for UI Components
Utility functions for fixing common table UI issues like button overlapping.
"""

from PyQt6.QtWidgets import (QTableWidget, QHeaderView, QWidget, QHBoxLayout,
                              QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt
from ui.utils.responsive_sizing import ResponsiveSize


def fix_table_button_overlap(table_widget, action_column_index, min_action_width=120):
    """
    Fix button overlapping in table action columns.
    
    Args:
        table_widget: QTableWidget instance
        action_column_index: Index of the action column
        min_action_width: Minimum width for action column
    """
    # Set column resize mode
    header = table_widget.horizontalHeader()
    
    # Make sure action column has enough space
    header.setSectionResizeMode(action_column_index, QHeaderView.ResizeMode.ResizeToContents)
    
    # Set minimum widths with DPI scaling
    min_section_size = ResponsiveSize.get_scaled_size(80)
    header.setMinimumSectionSize(min_section_size)

    scaled_min_action_width = ResponsiveSize.get_scaled_size(min_action_width)
    current_width = table_widget.columnWidth(action_column_index)
    if current_width < scaled_min_action_width:
        table_widget.setColumnWidth(action_column_index, scaled_min_action_width)

    # Ensure proper row height with DPI scaling
    row_height = ResponsiveSize.get_row_height('normal')
    min_row_height = ResponsiveSize.get_row_height('compact')
    table_widget.verticalHeader().setDefaultSectionSize(row_height)
    table_widget.verticalHeader().setMinimumSectionSize(min_row_height)

    # Update all action widgets
    for row in range(table_widget.rowCount()):
        widget = table_widget.cellWidget(row, action_column_index)
        if widget:
            # Adjust button sizes in the widget - use minimum size instead of fixed
            for child in widget.findChildren(QPushButton):
                min_width, min_height = ResponsiveSize.get_button_size('table_action')
                child.setMinimumSize(min_width, min_height)
                child.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def create_action_cell_widget(actions, button_width=80, button_height=32):
    """
    Create a properly sized action cell widget with responsive sizing.

    Args:
        actions: List of dictionaries with 'text', 'callback', 'style' keys
        button_width: Base width for action buttons (will be DPI-scaled)
        button_height: Base height for action buttons (will be DPI-scaled)

    Returns:
        QWidget: Container widget with properly sized buttons
    """
    container = QWidget()
    layout = QHBoxLayout(container)

    # Use responsive margins and spacing
    margin = ResponsiveSize.get_margin('tight')
    spacing = ResponsiveSize.get_spacing('tight')
    layout.setContentsMargins(margin, margin // 2, margin, margin // 2)
    layout.setSpacing(spacing)

    for action in actions:
        btn = QPushButton(action['text'])
        btn.setObjectName(action.get('style', 'secondaryButton'))

        # Calculate button width based on text content
        metrics = btn.fontMetrics()
        text_width = metrics.horizontalAdvance(action['text'])
        padding = ResponsiveSize.get_scaled_size(16)
        btn_width = max(ResponsiveSize.get_scaled_size(button_width), text_width + padding * 2)
        btn_height = ResponsiveSize.get_scaled_size(button_height)

        # Use minimum size with expanding policy to allow buttons to grow
        btn.setMinimumSize(btn_width, btn_height)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        if 'callback' in action:
            btn.clicked.connect(action['callback'])

        layout.addWidget(btn)

    # Don't add stretch - let buttons fill space evenly
    return container


def setup_responsive_table_columns(table_widget, column_configs):
    """
    Setup table columns with responsive sizing based on ratios and DPI.

    Args:
        table_widget: QTableWidget instance
        column_configs: List of dictionaries with:
            - 'index': Column index
            - 'ratio': Width ratio (0.0-1.0) of total table width
            - 'min_width': Minimum width in pixels (will be DPI-scaled)
            - 'resize_mode': Optional - 'Interactive', 'ResizeToContents', 'Stretch', or 'Fixed'

    Example:
        configs = [
            {'index': 0, 'ratio': 0.06, 'min_width': 50, 'resize_mode': 'Interactive'},  # ID
            {'index': 1, 'ratio': 0.15, 'min_width': 100, 'resize_mode': 'Interactive'}, # Username
            {'index': 6, 'ratio': 0.20, 'min_width': 200, 'resize_mode': 'ResizeToContents'}, # Actions
        ]
    """
    header = table_widget.horizontalHeader()
    table_width = table_widget.viewport().width()

    # Set global minimum section size with DPI scaling
    header.setMinimumSectionSize(ResponsiveSize.get_scaled_size(60))

    for config in column_configs:
        idx = config['index']
        resize_mode_str = config.get('resize_mode', 'Interactive')

        # Map string to QHeaderView.ResizeMode
        resize_mode_map = {
            'Interactive': QHeaderView.ResizeMode.Interactive,
            'ResizeToContents': QHeaderView.ResizeMode.ResizeToContents,
            'Stretch': QHeaderView.ResizeMode.Stretch,
            'Fixed': QHeaderView.ResizeMode.Fixed,
        }
        resize_mode = resize_mode_map.get(resize_mode_str, QHeaderView.ResizeMode.Interactive)

        if resize_mode == QHeaderView.ResizeMode.ResizeToContents:
            # Let content determine width (for action buttons)
            header.setSectionResizeMode(idx, resize_mode)
            min_width = ResponsiveSize.get_scaled_size(config['min_width'])
            header.setMinimumSectionSize(min_width)
        else:
            # Calculate width from ratio
            ratio = config.get('ratio', 0.1)
            column_width = int(table_width * ratio)
            min_width = ResponsiveSize.get_scaled_size(config['min_width'])
            column_width = max(column_width, min_width)

            table_widget.setColumnWidth(idx, column_width)
            header.setSectionResizeMode(idx, resize_mode)


def configure_table_row_heights(table_widget, default_height=48, min_height=40):
    """
    Configure table row heights to prevent button suppression with DPI scaling.

    Args:
        table_widget: QTableWidget instance
        default_height: Default row height (will be DPI-scaled)
        min_height: Minimum row height (will be DPI-scaled)
    """
    vertical_header = table_widget.verticalHeader()
    scaled_default = ResponsiveSize.get_scaled_size(default_height)
    scaled_min = ResponsiveSize.get_scaled_size(min_height)
    vertical_header.setDefaultSectionSize(scaled_default)
    vertical_header.setMinimumSectionSize(scaled_min)
    vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)