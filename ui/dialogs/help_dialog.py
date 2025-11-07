"""
Help & Documentation Dialog
Comprehensive help system with searchable documentation.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QTextBrowser, QTabWidget,
                             QWidget, QListWidget, QListWidgetItem, QSplitter,
                             QFrame)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices
from services.icon_service import get_icon


class HelpDialog(QDialog):
    """
    Help and documentation dialog.

    Features:
    - Getting Started guide
    - User Guide with searchable topics
    - Keyboard Shortcuts reference
    - FAQ section
    - About & Version information
    """

    def __init__(self, parent=None, shortcuts_service=None):
        """
        Initialize help dialog.

        Args:
            parent: Parent widget
            shortcuts_service: KeyboardShortcutsService instance (optional)
        """
        super().__init__(parent)
        self.shortcuts_service = shortcuts_service
        self.setup_ui()
        self.load_getting_started()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Help & Documentation")
        self.setMinimumSize(900, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        header = QLabel("Help & Documentation")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        header_layout.addWidget(header)

        header_layout.addStretch()

        # Version label
        version_label = QLabel("Version 2.0.0")
        version_label.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        header_layout.addWidget(version_label)

        layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_getting_started_tab(), "Getting Started")
        self.tabs.addTab(self.create_user_guide_tab(), "User Guide")
        self.tabs.addTab(self.create_shortcuts_tab(), "Keyboard Shortcuts")
        self.tabs.addTab(self.create_faq_tab(), "FAQ")
        self.tabs.addTab(self.create_about_tab(), "About")
        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        online_help_btn = QPushButton("Online Documentation")
        online_help_btn.setIcon(get_icon('book'))
        online_help_btn.clicked.connect(self.open_online_help)
        button_layout.addWidget(online_help_btn)

        close_btn = QPushButton("Close")
        close_btn.setIcon(get_icon('times'))
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_getting_started_tab(self):
        """Create getting started tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        self.getting_started_browser = QTextBrowser()
        self.getting_started_browser.setOpenExternalLinks(True)
        layout.addWidget(self.getting_started_browser)

        return tab

    def create_user_guide_tab(self):
        """Create user guide tab with searchable topics."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        search_frame = QFrame()
        search_frame.setObjectName("card")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(16, 12, 16, 12)

        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search help topics...")
        self.search_input.textChanged.connect(self.filter_topics)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_frame)

        # Splitter with topics and content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Topics list
        self.topics_list = QListWidget()
        self.topics_list.setMaximumWidth(250)
        self.topics_list.currentItemChanged.connect(self.on_topic_selected)
        splitter.addWidget(self.topics_list)

        # Content browser
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        splitter.addWidget(self.content_browser)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Load topics
        self.load_help_topics()

        return tab

    def create_shortcuts_tab(self):
        """Create keyboard shortcuts tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        shortcuts_browser = QTextBrowser()
        shortcuts_browser.setOpenExternalLinks(False)
        shortcuts_browser.setHtml(self.get_shortcuts_html())
        layout.addWidget(shortcuts_browser)

        return tab

    def create_faq_tab(self):
        """Create FAQ tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        faq_browser = QTextBrowser()
        faq_browser.setOpenExternalLinks(True)
        faq_browser.setHtml(self.get_faq_html())
        layout.addWidget(faq_browser)

        return tab

    def create_about_tab(self):
        """Create about tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Logo/Title
        title = QLabel("FIU Report Management System")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Version
        version = QLabel("Version 2.0.0")
        version.setStyleSheet("font-size: 14pt; color: #7f8c8d;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(20)

        # Description
        desc = QLabel(
            "Financial Intelligence Unit Report Management System\n\n"
            "A comprehensive solution for managing financial crime reports "
            "with modern architecture and user-friendly interface."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(desc)

        layout.addSpacing(20)

        # Technology stack
        tech_label = QLabel("Built with:")
        tech_label.setStyleSheet("font-weight: 600; font-size: 11pt;")
        tech_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tech_label)

        tech_stack = QLabel(
            "Python 3.9+ • PyQt6 • SQLite3 • QtAwesome\n"
            "Matplotlib • OpenPyXL • Bcrypt"
        )
        tech_stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tech_stack.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(tech_stack)

        layout.addSpacing(20)

        # Copyright
        copyright_label = QLabel(
            "© 2025 Financial Intelligence Unit\n"
            "All rights reserved."
        )
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        layout.addWidget(copyright_label)

        layout.addStretch()

        return tab

    def load_getting_started(self):
        """Load getting started content."""
        html = """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; }
                h1 { color: #0d7377; border-bottom: 2px solid #0d7377; padding-bottom: 10px; }
                h2 { color: #2c3e50; margin-top: 25px; }
                h3 { color: #34495e; margin-top: 20px; }
                .step { background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #0d7377; }
                .tip { background-color: #d1f2eb; padding: 12px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #27ae60; }
                .warning { background-color: #fef5e7; padding: 12px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #f39c12; }
                ul { padding-left: 25px; }
                li { margin: 8px 0; }
                code { background-color: #ecf0f1; padding: 2px 6px; border-radius: 3px; font-family: 'Consolas', monospace; }
            </style>
        </head>
        <body>
            <h1>🚀 Getting Started with FIU System</h1>

            <h2>Welcome!</h2>
            <p>Thank you for using the FIU Report Management System. This guide will help you get started quickly.</p>

            <h2>1. First Login</h2>
            <div class="step">
                <h3>Default Administrator Account</h3>
                <ul>
                    <li><strong>Username:</strong> admin</li>
                    <li><strong>Password:</strong> admin123</li>
                </ul>
                <div class="warning">
                    <strong>⚠️ Important:</strong> Please change the default password immediately after first login for security.
                </div>
            </div>

            <h2>2. Navigation</h2>
            <div class="step">
                <p>Use the left sidebar to navigate between different sections:</p>
                <ul>
                    <li><strong>Dashboard:</strong> View summary statistics and key metrics</li>
                    <li><strong>Reports:</strong> Browse, search, and manage financial crime reports</li>
                    <li><strong>Add Report:</strong> Create new reports (for authorized users)</li>
                    <li><strong>Export:</strong> Export reports to CSV format</li>
                    <li><strong>Users:</strong> Manage user accounts (admin only)</li>
                    <li><strong>System Logs:</strong> View audit trail (admin only)</li>
                    <li><strong>Settings:</strong> Configure application preferences (admin only)</li>
                </ul>
            </div>

            <h2>3. Creating Your First Report</h2>
            <div class="step">
                <ol>
                    <li>Click on <strong>Reports</strong> in the sidebar</li>
                    <li>Click the <strong>Add New Report</strong> button</li>
                    <li>Fill in the required information across 5 tabs:
                        <ul>
                            <li>Basic Information (Report ID, Date, Institution details)</li>
                            <li>Entity Details (Suspect information, ID details)</li>
                            <li>Suspicion Details (Activity description, amounts)</li>
                            <li>Classification & Source (Report type, classification)</li>
                            <li>FIU Details (Submission info, attachments)</li>
                        </ul>
                    </li>
                    <li>Click <strong>Save Report</strong> when complete</li>
                </ol>
                <div class="tip">
                    <strong>💡 Tip:</strong> All fields marked with an asterisk (*) are required.
                </div>
            </div>

            <h2>4. Managing Reports</h2>
            <div class="step">
                <h3>View Reports</h3>
                <ul>
                    <li>Browse all reports in the Reports view</li>
                    <li>Use search and filters to find specific reports</li>
                    <li>Click on any report to view full details</li>
                </ul>

                <h3>Edit Reports</h3>
                <ul>
                    <li>Select a report and click the <strong>Edit</strong> button</li>
                    <li>Make changes and save</li>
                    <li>Changes are logged in the audit trail</li>
                </ul>

                <h3>Delete Reports</h3>
                <ul>
                    <li>Select a report and click the <strong>Delete</strong> button</li>
                    <li>Confirm the deletion</li>
                    <li>Note: Deletions are soft deletes and can be recovered by administrators</li>
                </ul>
            </div>

            <h2>5. User Management (Admin Only)</h2>
            <div class="step">
                <h3>Adding Users</h3>
                <ol>
                    <li>Navigate to <strong>Users</strong> in the sidebar</li>
                    <li>Click <strong>Add User</strong></li>
                    <li>Fill in user details and assign a role:
                        <ul>
                            <li><strong>Admin:</strong> Full system access</li>
                            <li><strong>Agent:</strong> Can view and create reports</li>
                            <li><strong>Reporter:</strong> Can only create reports</li>
                        </ul>
                    </li>
                    <li>Click <strong>Save</strong></li>
                </ol>

                <div class="tip">
                    <strong>💡 Tip:</strong> Assign the least privilege necessary for each user's role.
                </div>
            </div>

            <h2>6. Data Backup</h2>
            <div class="step">
                <p>Regular backups are essential for data protection:</p>
                <ol>
                    <li>Go to <strong>Settings</strong></li>
                    <li>Navigate to the <strong>Advanced</strong> tab</li>
                    <li>Click <strong>Backup & Restore</strong></li>
                    <li>Click <strong>Create Backup Now</strong></li>
                </ol>

                <div class="warning">
                    <strong>⚠️ Best Practice:</strong> Create backups before major changes and store them in a secure location.
                </div>
            </div>

            <h2>7. Customization</h2>
            <div class="step">
                <p>Personalize your experience in <strong>Settings</strong>:</p>
                <ul>
                    <li><strong>Theme:</strong> Switch between light and dark themes</li>
                    <li><strong>Notifications:</strong> Configure toast notification preferences</li>
                    <li><strong>Display:</strong> Adjust font sizes and table settings</li>
                    <li><strong>Language:</strong> Set date/time formats (more languages coming soon)</li>
                </ul>
            </div>

            <h2>8. Need More Help?</h2>
            <div class="step">
                <ul>
                    <li>Check the <strong>User Guide</strong> tab for detailed documentation</li>
                    <li>Review <strong>Keyboard Shortcuts</strong> for efficiency tips</li>
                    <li>Browse the <strong>FAQ</strong> for common questions</li>
                    <li>Contact your system administrator for technical support</li>
                </ul>
            </div>

            <div class="tip">
                <h3>🎯 Quick Tips for Success</h3>
                <ul>
                    <li>Use the search bar to quickly find reports</li>
                    <li>Enable auto-refresh on dashboard for real-time updates</li>
                    <li>Export reports regularly for external analysis</li>
                    <li>Review system logs periodically for security monitoring</li>
                    <li>Keep your password secure and change it regularly</li>
                </ul>
            </div>
        </body>
        </html>
        """
        self.getting_started_browser.setHtml(html)

    def load_help_topics(self):
        """Load help topics into the list."""
        topics = [
            ("Dashboard Overview", "dashboard"),
            ("Creating Reports", "reports_create"),
            ("Editing Reports", "reports_edit"),
            ("Searching Reports", "reports_search"),
            ("Exporting Data", "export"),
            ("User Management", "users"),
            ("Role Permissions", "permissions"),
            ("System Settings", "settings"),
            ("Backup & Restore", "backup"),
            ("Security Best Practices", "security"),
            ("Audit Trail", "audit"),
            ("Troubleshooting", "troubleshooting"),
        ]

        for title, topic_id in topics:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, topic_id)
            self.topics_list.addItem(item)

        # Select first topic
        if self.topics_list.count() > 0:
            self.topics_list.setCurrentRow(0)

    def on_topic_selected(self, current, previous):
        """
        Handle topic selection.

        Args:
            current: Current item
            previous: Previous item
        """
        if not current:
            return

        topic_id = current.data(Qt.ItemDataRole.UserRole)
        content = self.get_topic_content(topic_id)
        self.content_browser.setHtml(content)

    def filter_topics(self, text):
        """
        Filter topics based on search text.

        Args:
            text: Search text
        """
        search_text = text.lower()
        for i in range(self.topics_list.count()):
            item = self.topics_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    def get_topic_content(self, topic_id):
        """
        Get content for a specific topic.

        Args:
            topic_id: Topic identifier

        Returns:
            HTML content string
        """
        # This would ideally load from external documentation files
        # For now, return placeholder content based on topic

        base_style = """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; padding: 20px; }
                h1 { color: #0d7377; border-bottom: 2px solid #0d7377; padding-bottom: 10px; }
                h2 { color: #2c3e50; margin-top: 20px; }
                p { margin: 10px 0; }
                ul, ol { padding-left: 25px; }
                li { margin: 8px 0; }
                .note { background-color: #d1f2eb; padding: 12px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #27ae60; }
                .warning { background-color: #fef5e7; padding: 12px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #f39c12; }
                code { background-color: #ecf0f1; padding: 2px 6px; border-radius: 3px; font-family: 'Consolas', monospace; }
            </style>
        </head>
        <body>
        """

        content_map = {
            "dashboard": """
                <h1>Dashboard Overview</h1>
                <p>The dashboard provides a comprehensive view of your system's key metrics and statistics.</p>

                <h2>Key Performance Indicators (KPIs)</h2>
                <ul>
                    <li><strong>Total Reports:</strong> Shows the total number of reports in the system</li>
                    <li><strong>Open Reports:</strong> Reports that are currently active</li>
                    <li><strong>Under Investigation:</strong> Reports being actively investigated</li>
                    <li><strong>Closed Cases:</strong> Completed and archived reports</li>
                </ul>

                <h2>Auto-Refresh</h2>
                <p>Enable auto-refresh in Settings → General to automatically update dashboard data at regular intervals.</p>

                <div class="note">
                    <strong>Tip:</strong> Click the Refresh button in the toolbar to manually update dashboard data.
                </div>
            """,
            "reports_create": """
                <h1>Creating Reports</h1>
                <p>Follow these steps to create a new financial crime report.</p>

                <h2>Access Requirements</h2>
                <p>Users must have 'Reporter', 'Agent', or 'Admin' role to create reports.</p>

                <h2>Report Form Structure</h2>
                <p>The report form is organized into 5 tabs for easy navigation:</p>

                <h3>1. Basic Information</h3>
                <ul>
                    <li>Report ID (auto-generated)</li>
                    <li>Report date and time</li>
                    <li>Reporting institution details</li>
                    <li>Contact information</li>
                </ul>

                <h3>2. Entity Details</h3>
                <ul>
                    <li>Suspect name and type</li>
                    <li>ID number and type</li>
                    <li>Address and contact details</li>
                    <li>Nationality</li>
                </ul>

                <h3>3. Suspicion Details</h3>
                <ul>
                    <li>Activity description</li>
                    <li>Transaction amounts</li>
                    <li>Dates and locations</li>
                    <li>Reason for suspicion</li>
                </ul>

                <h3>4. Classification & Source</h3>
                <ul>
                    <li>Report type</li>
                    <li>Classification</li>
                    <li>Source of information</li>
                </ul>

                <h3>5. FIU Details</h3>
                <ul>
                    <li>Submission information</li>
                    <li>Attachments reference</li>
                    <li>Additional notes</li>
                </ul>

                <div class="warning">
                    <strong>Required Fields:</strong> All fields marked with an asterisk (*) must be completed before saving.
                </div>
            """,
            "security": """
                <h1>Security Best Practices</h1>

                <h2>Password Security</h2>
                <ul>
                    <li>Use strong passwords (minimum 8 characters)</li>
                    <li>Include uppercase, lowercase, and numbers</li>
                    <li>Change passwords regularly</li>
                    <li>Never share passwords with others</li>
                    <li>Change default passwords immediately</li>
                </ul>

                <h2>Account Security</h2>
                <ul>
                    <li>Log out when leaving your workstation</li>
                    <li>Enable session timeout in Settings</li>
                    <li>Review audit logs regularly</li>
                    <li>Report suspicious activity immediately</li>
                </ul>

                <h2>Data Protection</h2>
                <ul>
                    <li>Create regular backups</li>
                    <li>Store backups in secure locations</li>
                    <li>Limit access to sensitive reports</li>
                    <li>Use export features responsibly</li>
                </ul>

                <div class="warning">
                    <strong>⚠️ Important:</strong> All user actions are logged for security and audit purposes.
                </div>
            """,
        }

        content = content_map.get(topic_id, f"<h1>Documentation</h1><p>Documentation for this topic is being prepared.</p>")

        return base_style + content + "</body></html>"

    def get_shortcuts_html(self):
        """Get keyboard shortcuts HTML content."""
        # Use shortcuts service if available
        if self.shortcuts_service:
            return self.shortcuts_service.generate_help_html()

        # Fallback to static HTML
        return """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; }
                h1 { color: #0d7377; border-bottom: 2px solid #0d7377; padding-bottom: 10px; }
                h2 { color: #2c3e50; margin-top: 25px; }
                table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                th { background-color: #0d7377; color: white; padding: 12px; text-align: left; }
                td { padding: 10px; border-bottom: 1px solid #ddd; }
                tr:hover { background-color: #f8f9fa; }
                .key { background-color: #ecf0f1; padding: 4px 8px; border-radius: 4px; font-family: 'Consolas', monospace; font-weight: 600; border: 1px solid #bdc3c7; }
                .note { background-color: #d1f2eb; padding: 12px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #27ae60; }
            </style>
        </head>
        <body>
            <h1>⌨️ Keyboard Shortcuts</h1>

            <h2>General Navigation</h2>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">D</span></td>
                    <td>Go to Dashboard</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">R</span></td>
                    <td>Go to Reports</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">N</span></td>
                    <td>Create New Report</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">E</span></td>
                    <td>Go to Export</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">Q</span></td>
                    <td>Quit Application</td>
                </tr>
                <tr>
                    <td><span class="key">F5</span></td>
                    <td>Refresh Current View</td>
                </tr>
            </table>

            <h2>Report Management</h2>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">F</span></td>
                    <td>Focus Search Box</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">S</span></td>
                    <td>Save Report (in edit mode)</td>
                </tr>
                <tr>
                    <td><span class="key">Esc</span></td>
                    <td>Cancel / Close Dialog</td>
                </tr>
                <tr>
                    <td><span class="key">Enter</span></td>
                    <td>Confirm Action</td>
                </tr>
                <tr>
                    <td><span class="key">Delete</span></td>
                    <td>Delete Selected Report</td>
                </tr>
            </table>

            <h2>Dialog Navigation</h2>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td><span class="key">Tab</span></td>
                    <td>Next Field</td>
                </tr>
                <tr>
                    <td><span class="key">Shift</span> + <span class="key">Tab</span></td>
                    <td>Previous Field</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">Tab</span></td>
                    <td>Next Tab</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">Shift</span> + <span class="key">Tab</span></td>
                    <td>Previous Tab</td>
                </tr>
            </table>

            <h2>Admin Functions</h2>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">U</span></td>
                    <td>User Management</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">L</span></td>
                    <td>System Logs</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">,</span></td>
                    <td>Settings</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">B</span></td>
                    <td>Backup & Restore</td>
                </tr>
            </table>

            <h2>Text Editing</h2>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">A</span></td>
                    <td>Select All</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">C</span></td>
                    <td>Copy</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">X</span></td>
                    <td>Cut</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">V</span></td>
                    <td>Paste</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">Z</span></td>
                    <td>Undo</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">Y</span></td>
                    <td>Redo</td>
                </tr>
            </table>

            <h2>Help & Support</h2>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>
                <tr>
                    <td><span class="key">F1</span></td>
                    <td>Open Help</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl</span> + <span class="key">H</span></td>
                    <td>Open Help</td>
                </tr>
            </table>

            <div class="note">
                <strong>💡 Tip:</strong> Most shortcuts can be customized in Settings → Advanced → Keyboard Shortcuts (coming soon).
            </div>
        </body>
        </html>
        """

    def get_faq_html(self):
        """Get FAQ HTML content."""
        return """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; }
                h1 { color: #0d7377; border-bottom: 2px solid #0d7377; padding-bottom: 10px; }
                h2 { color: #2c3e50; margin-top: 25px; }
                .faq-item { background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #0d7377; }
                .question { font-weight: 600; color: #2c3e50; margin-bottom: 10px; }
                .answer { color: #555; }
                ul { padding-left: 25px; }
                li { margin: 8px 0; }
            </style>
        </head>
        <body>
            <h1>❓ Frequently Asked Questions</h1>

            <div class="faq-item">
                <div class="question">Q: How do I reset my password?</div>
                <div class="answer">
                    A: Go to Settings → Security tab → click "Change Password" button. You'll need to enter your current password to set a new one.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: Can I recover deleted reports?</div>
                <div class="answer">
                    A: Yes, the system uses soft deletes. Administrators can recover deleted reports from the database backup or by contacting technical support.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: How often should I create backups?</div>
                <div class="answer">
                    A: We recommend creating backups:
                    <ul>
                        <li>Daily for active systems with frequent updates</li>
                        <li>Weekly for moderate usage</li>
                        <li>Before any major system changes</li>
                        <li>Before software updates</li>
                    </ul>
                    You can also enable automatic backups in Settings.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: What's the difference between user roles?</div>
                <div class="answer">
                    A: There are three user roles:
                    <ul>
                        <li><strong>Admin:</strong> Full system access including user management, settings, and backups</li>
                        <li><strong>Agent:</strong> Can view all reports, create new reports, and export data</li>
                        <li><strong>Reporter:</strong> Can only create new reports, limited viewing access</li>
                    </ul>
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: How do I export reports to Excel?</div>
                <div class="answer">
                    A: Currently, the system exports to CSV format which can be opened in Excel. Go to the Export view, apply your filters, and click "Export to CSV". Excel support (.xlsx) is coming soon!
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: Why can't I see the Users or Settings menu?</div>
                <div class="answer">
                    A: These features are only available to users with Administrator role. Contact your system administrator if you need access.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: How do I change the application theme?</div>
                <div class="answer">
                    A: Use the "Toggle Theme" button in the toolbar, or go to Settings → General → Application Theme to choose between Dark, Light, or System Default theme.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: Can I access the system from multiple computers?</div>
                <div class="answer">
                    A: Yes, as long as the database is accessible from those computers. However, only one active session per user is recommended for security.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: What should I do if the application crashes?</div>
                <div class="answer">
                    A: Follow these steps:
                    <ol>
                        <li>Restart the application</li>
                        <li>Check if the database file is accessible</li>
                        <li>Review the application logs in Settings → Advanced → View Logs</li>
                        <li>If the problem persists, restore from a recent backup</li>
                        <li>Contact technical support with error details</li>
                    </ol>
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: How do I search for specific reports?</div>
                <div class="answer">
                    A: In the Reports view:
                    <ul>
                        <li>Use the search box to search by Report ID, entity name, or description</li>
                        <li>Apply filters by status, date range, or classification</li>
                        <li>Click column headers to sort the results</li>
                    </ul>
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: Are my actions logged?</div>
                <div class="answer">
                    A: Yes, all user actions are logged for security and audit purposes. Administrators can view the audit trail in the System Logs section.
                </div>
            </div>

            <div class="faq-item">
                <div class="question">Q: Can I print reports?</div>
                <div class="answer">
                    A: Currently, you can export reports to CSV and print from there. Native PDF export and printing features are planned for a future update.
                </div>
            </div>
        </body>
        </html>
        """

    def open_online_help(self):
        """Open online documentation in browser."""
        # Placeholder URL - update with actual documentation URL
        url = QUrl("https://docs.example.com/fiu-system")
        QDesktopServices.openUrl(url)
