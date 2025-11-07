"""
Chart Widget
Base widget for displaying matplotlib charts with PyQt6.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class ChartWidget(QWidget):
    """
    Base chart widget using matplotlib.

    Features:
    - Embeds matplotlib canvas in PyQt6
    - Theme-aware styling
    - Responsive resizing
    - Interactive features
    """

    def __init__(self, parent=None, theme='dark'):
        """
        Initialize chart widget.

        Args:
            parent: Parent widget
            theme: Theme name ('dark' or 'light')
        """
        super().__init__(parent)
        self.theme = theme

        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        # Setup layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        # Configure canvas
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Apply theme
        self.apply_theme()

    def apply_theme(self):
        """Apply theme styling to the chart."""
        if self.theme == 'dark':
            # Dark theme colors
            self.bg_color = '#1a1f26'
            self.text_color = '#e0e6ed'
            self.grid_color = '#2c3e50'
            self.accent_color = '#0d7377'
        else:
            # Light theme colors
            self.bg_color = '#ffffff'
            self.text_color = '#2c3e50'
            self.grid_color = '#e0e0e0'
            self.accent_color = '#0d7377'

        # Set figure background
        self.figure.patch.set_facecolor(self.bg_color)
        self.canvas.setStyleSheet(f"background-color: {self.bg_color};")

    def clear(self):
        """Clear the chart."""
        self.figure.clear()
        self.canvas.draw()

    def get_color_palette(self):
        """
        Get color palette for charts.

        Returns:
            List of colors
        """
        if self.theme == 'dark':
            return [
                '#0d7377',  # Teal
                '#14ffec',  # Cyan
                '#f39c12',  # Orange
                '#e74c3c',  # Red
                '#27ae60',  # Green
                '#3498db',  # Blue
                '#9b59b6',  # Purple
                '#e67e22',  # Dark Orange
            ]
        else:
            return [
                '#0d7377',  # Teal
                '#3498db',  # Blue
                '#f39c12',  # Orange
                '#e74c3c',  # Red
                '#27ae60',  # Green
                '#9b59b6',  # Purple
                '#1abc9c',  # Turquoise
                '#e67e22',  # Dark Orange
            ]


class PieChartWidget(ChartWidget):
    """
    Pie chart widget for displaying proportional data.
    """

    def __init__(self, parent=None, theme='dark'):
        """
        Initialize pie chart widget.

        Args:
            parent: Parent widget
            theme: Theme name
        """
        super().__init__(parent, theme)

    def plot_data(self, data, labels, title="Pie Chart"):
        """
        Plot pie chart data.

        Args:
            data: List of values
            labels: List of labels
            title: Chart title
        """
        self.clear()

        if not data or sum(data) == 0:
            # Show "No data" message
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available',
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=14,
                   color=self.text_color)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.patch.set_facecolor(self.bg_color)
            self.canvas.draw()
            return

        ax = self.figure.add_subplot(111)
        ax.patch.set_facecolor(self.bg_color)

        # Get colors
        colors = self.get_color_palette()[:len(data)]

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            data,
            labels=labels,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            textprops={'color': self.text_color, 'fontsize': 10}
        )

        # Style percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)

        # Add title
        ax.set_title(title, color=self.text_color, fontsize=12, fontweight='bold', pad=20)

        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')

        self.figure.tight_layout()
        self.canvas.draw()


class BarChartWidget(ChartWidget):
    """
    Bar chart widget for displaying comparative data.
    """

    def __init__(self, parent=None, theme='dark'):
        """
        Initialize bar chart widget.

        Args:
            parent: Parent widget
            theme: Theme name
        """
        super().__init__(parent, theme)

    def plot_data(self, categories, values, title="Bar Chart", xlabel="", ylabel="Count"):
        """
        Plot bar chart data.

        Args:
            categories: List of category names
            values: List of values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
        """
        self.clear()

        if not values or sum(values) == 0:
            # Show "No data" message
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available',
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=14,
                   color=self.text_color)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.patch.set_facecolor(self.bg_color)
            self.canvas.draw()
            return

        ax = self.figure.add_subplot(111)
        ax.patch.set_facecolor(self.bg_color)

        # Get colors
        colors = self.get_color_palette()[:len(values)]

        # Create bar chart
        bars = ax.bar(categories, values, color=colors, edgecolor=self.text_color, linewidth=0.5)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom',
                   color=self.text_color,
                   fontsize=9,
                   fontweight='bold')

        # Styling
        ax.set_title(title, color=self.text_color, fontsize=12, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, color=self.text_color, fontsize=10)
        ax.set_ylabel(ylabel, color=self.text_color, fontsize=10)

        # Style axes
        ax.tick_params(axis='x', colors=self.text_color, labelsize=9)
        ax.tick_params(axis='y', colors=self.text_color, labelsize=9)
        ax.spines['bottom'].set_color(self.text_color)
        ax.spines['left'].set_color(self.text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add grid
        ax.grid(True, alpha=0.3, color=self.grid_color, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)

        # Rotate x-axis labels if needed
        if len(categories) > 5:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        self.figure.tight_layout()
        self.canvas.draw()


class LineChartWidget(ChartWidget):
    """
    Line chart widget for displaying trends over time.
    """

    def __init__(self, parent=None, theme='dark'):
        """
        Initialize line chart widget.

        Args:
            parent: Parent widget
            theme: Theme name
        """
        super().__init__(parent, theme)

    def plot_data(self, x_data, y_data_dict, title="Line Chart", xlabel="", ylabel="Value"):
        """
        Plot line chart data.

        Args:
            x_data: List of x-axis values (e.g., dates, months)
            y_data_dict: Dictionary of {label: [values]} for multiple lines
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
        """
        self.clear()

        if not y_data_dict or not x_data:
            # Show "No data" message
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available',
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=14,
                   color=self.text_color)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.patch.set_facecolor(self.bg_color)
            self.canvas.draw()
            return

        ax = self.figure.add_subplot(111)
        ax.patch.set_facecolor(self.bg_color)

        # Get colors
        colors = self.get_color_palette()

        # Plot each line
        for idx, (label, y_data) in enumerate(y_data_dict.items()):
            color = colors[idx % len(colors)]
            ax.plot(x_data, y_data, marker='o', linewidth=2,
                   markersize=6, label=label, color=color)

        # Styling
        ax.set_title(title, color=self.text_color, fontsize=12, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, color=self.text_color, fontsize=10)
        ax.set_ylabel(ylabel, color=self.text_color, fontsize=10)

        # Style axes
        ax.tick_params(axis='x', colors=self.text_color, labelsize=9)
        ax.tick_params(axis='y', colors=self.text_color, labelsize=9)
        ax.spines['bottom'].set_color(self.text_color)
        ax.spines['left'].set_color(self.text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add grid
        ax.grid(True, alpha=0.3, color=self.grid_color, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)

        # Add legend if multiple lines
        if len(y_data_dict) > 1:
            legend = ax.legend(loc='best', framealpha=0.9)
            legend.get_frame().set_facecolor(self.bg_color)
            legend.get_frame().set_edgecolor(self.text_color)
            for text in legend.get_texts():
                text.set_color(self.text_color)

        # Rotate x-axis labels if needed
        if len(x_data) > 10:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        self.figure.tight_layout()
        self.canvas.draw()


class HorizontalBarChartWidget(ChartWidget):
    """
    Horizontal bar chart widget for displaying ranked data.
    """

    def __init__(self, parent=None, theme='dark'):
        """
        Initialize horizontal bar chart widget.

        Args:
            parent: Parent widget
            theme: Theme name
        """
        super().__init__(parent, theme)

    def plot_data(self, categories, values, title="Horizontal Bar Chart", xlabel="Count", ylabel=""):
        """
        Plot horizontal bar chart data.

        Args:
            categories: List of category names
            values: List of values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
        """
        self.clear()

        if not values or sum(values) == 0:
            # Show "No data" message
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available',
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=14,
                   color=self.text_color)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.patch.set_facecolor(self.bg_color)
            self.canvas.draw()
            return

        ax = self.figure.add_subplot(111)
        ax.patch.set_facecolor(self.bg_color)

        # Get colors
        colors = self.get_color_palette()[:len(values)]

        # Create horizontal bar chart
        y_pos = range(len(categories))
        bars = ax.barh(y_pos, values, color=colors, edgecolor=self.text_color, linewidth=0.5)

        # Add value labels on bars
        for idx, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f' {int(width)}',
                   ha='left', va='center',
                   color=self.text_color,
                   fontsize=9,
                   fontweight='bold')

        # Styling
        ax.set_title(title, color=self.text_color, fontsize=12, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, color=self.text_color, fontsize=10)
        ax.set_ylabel(ylabel, color=self.text_color, fontsize=10)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories)

        # Style axes
        ax.tick_params(axis='x', colors=self.text_color, labelsize=9)
        ax.tick_params(axis='y', colors=self.text_color, labelsize=9)
        ax.spines['bottom'].set_color(self.text_color)
        ax.spines['left'].set_color(self.text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add grid
        ax.grid(True, alpha=0.3, color=self.grid_color, linestyle='--', linewidth=0.5, axis='x')
        ax.set_axisbelow(True)

        self.figure.tight_layout()
        self.canvas.draw()
