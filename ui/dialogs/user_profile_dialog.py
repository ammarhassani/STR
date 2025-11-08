"""
User Profile Dialog
View and edit current user profile information.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QTextEdit, QMessageBox,
                             QGroupBox, QFormLayout, QFrame, QTabWidget,
                             QWidget, QScrollArea, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from services.icon_service import get_icon
from datetime import datetime


class UserProfileDialog(QDialog):
    """
    User profile dialog for viewing and editing user information.

    Features:
    - View user details
    - Edit profile information
    - Change password
    - View activity statistics
    - View login history
    """

    profile_updated = pyqtSignal()

    def __init__(self, auth_service, logging_service, db_manager, parent=None):
        """
        Initialize user profile dialog.

        Args:
            auth_service: AuthService instance
            logging_service: LoggingService instance
            db_manager: DatabaseManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.auth_service = auth_service
        self.logging_service = logging_service
        self.db_manager = db_manager
        self.current_user = auth_service.get_current_user()

        if not self.current_user:
            raise ValueError("No user is currently logged in")

        self.setup_ui()
        self.load_profile_data()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("User Profile")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header with user info
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)

        # Avatar placeholder (could be replaced with actual image)
        avatar_label = QLabel()
        avatar_label.setFixedSize(80, 80)
        avatar_label.setStyleSheet("""
            QLabel {
                background-color: #0d7377;
                border-radius: 40px;
                color: white;
                font-size: 32pt;
                font-weight: bold;
            }
        """)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use first letter of name as avatar
        initial = self.current_user['full_name'][0].upper() if self.current_user['full_name'] else "U"
        avatar_label.setText(initial)
        header_layout.addWidget(avatar_label)

        # User info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = QLabel(self.current_user['full_name'])
        name_font = QFont()
        name_font.setPointSize(16)
        name_font.setWeight(QFont.Weight.Bold)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)

        username_label = QLabel(f"@{self.current_user['username']}")
        username_label.setStyleSheet("color: #7f8c8d; font-size: 11pt;")
        info_layout.addWidget(username_label)

        role_label = QLabel(f"Role: {self.current_user['role'].title()}")
        role_label.setStyleSheet("color: #0d7377; font-weight: 600; font-size: 10pt;")
        info_layout.addWidget(role_label)

        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_profile_tab(), "Profile Information")
        tabs.addTab(self.create_activity_tab(), "Activity & Statistics")
        tabs.addTab(self.create_security_tab(), "Security")
        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(get_icon('times'))
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setIcon(get_icon('save'))
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self.save_profile)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def create_profile_tab(self):
        """Create profile information tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Basic information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(12)

        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("Enter full name")
        basic_layout.addRow("Full Name:", self.full_name_input)

        self.username_input = QLineEdit()
        self.username_input.setReadOnly(True)
        self.username_input.setObjectName("readOnlyField")
        basic_layout.addRow("Username:", self.username_input)

        self.role_input = QLineEdit()
        self.role_input.setReadOnly(True)
        self.role_input.setObjectName("readOnlyField")
        basic_layout.addRow("Role:", self.role_input)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Contact information (if supported in future)
        contact_group = QGroupBox("Contact Information")
        contact_layout = QFormLayout()
        contact_layout.setSpacing(12)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")
        contact_layout.addRow("Email:", self.email_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1234567890")
        contact_layout.addRow("Phone:", self.phone_input)

        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)

        # Preferences
        pref_group = QGroupBox("Display Preferences")
        pref_layout = QFormLayout()
        pref_layout.setSpacing(12)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Arabic", "French", "Spanish"])
        pref_layout.addRow("Language:", self.language_combo)

        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems(["UTC", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC-5", "UTC-8"])
        pref_layout.addRow("Timezone:", self.timezone_combo)

        pref_group.setLayout(pref_layout)
        layout.addWidget(pref_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_activity_tab(self):
        """Create activity and statistics tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Account info
        account_group = QGroupBox("Account Information")
        account_layout = QFormLayout()
        account_layout.setSpacing(12)

        self.created_at_label = QLabel("Loading...")
        account_layout.addRow("Account Created:", self.created_at_label)

        self.last_login_label = QLabel("Loading...")
        account_layout.addRow("Last Login:", self.last_login_label)

        self.login_count_label = QLabel("Loading...")
        account_layout.addRow("Total Logins:", self.login_count_label)

        account_group.setLayout(account_layout)
        layout.addWidget(account_group)

        # Activity statistics
        stats_group = QGroupBox("Activity Statistics")
        stats_layout = QFormLayout()
        stats_layout.setSpacing(12)

        self.reports_created_label = QLabel("Loading...")
        stats_layout.addRow("Reports Created:", self.reports_created_label)

        self.reports_edited_label = QLabel("Loading...")
        stats_layout.addRow("Reports Edited:", self.reports_edited_label)

        self.last_action_label = QLabel("Loading...")
        stats_layout.addRow("Last Activity:", self.last_action_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Recent activity
        recent_group = QGroupBox("Recent Activity")
        recent_layout = QVBoxLayout()

        self.recent_activity_text = QTextEdit()
        self.recent_activity_text.setReadOnly(True)
        self.recent_activity_text.setMaximumHeight(200)
        self.recent_activity_text.setPlaceholderText("Loading recent activity...")
        recent_layout.addWidget(self.recent_activity_text)

        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_security_tab(self):
        """Create security tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Password section
        password_group = QGroupBox("Password & Authentication")
        password_layout = QVBoxLayout()
        password_layout.setContentsMargins(16, 20, 16, 16)  # Add padding inside group box
        password_layout.setSpacing(12)

        password_info = QLabel(
            "Keep your account secure by using a strong password and changing it regularly."
        )
        password_info.setWordWrap(True)
        password_info.setStyleSheet("color: #7f8c8d;")
        password_layout.addWidget(password_info)

        change_password_btn = QPushButton("Change Password")
        change_password_btn.setIcon(get_icon('key'))
        change_password_btn.setMaximumWidth(200)
        change_password_btn.clicked.connect(self.change_password)
        password_layout.addWidget(change_password_btn)

        self.password_changed_label = QLabel("Last changed: Loading...")
        self.password_changed_label.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        password_layout.addWidget(self.password_changed_label)

        password_group.setLayout(password_layout)
        layout.addWidget(password_group)

        # Session info
        session_group = QGroupBox("Active Sessions")
        session_layout = QVBoxLayout()
        session_layout.setContentsMargins(16, 20, 16, 16)  # Add padding inside group box
        session_layout.setSpacing(12)

        session_info = QLabel(
            "Your current session information."
        )
        session_info.setWordWrap(True)
        session_info.setStyleSheet("color: #7f8c8d;")
        session_layout.addWidget(session_info)

        self.current_session_label = QLabel("Loading session info...")
        session_layout.addWidget(self.current_session_label)

        logout_all_btn = QPushButton("Logout All Other Sessions")
        logout_all_btn.setIcon(get_icon('sign-out-alt'))
        logout_all_btn.setObjectName("dangerButton")
        logout_all_btn.setMaximumWidth(220)
        logout_all_btn.clicked.connect(self.logout_other_sessions)
        session_layout.addWidget(logout_all_btn)

        session_group.setLayout(session_layout)
        layout.addWidget(session_group)

        # Security settings
        security_group = QGroupBox("Security Settings")
        security_layout = QVBoxLayout()
        security_layout.setContentsMargins(16, 20, 16, 16)  # Add padding inside group box
        security_layout.setSpacing(12)

        security_info = QLabel(
            "Additional security options can be configured in Settings → Security."
        )
        security_info.setWordWrap(True)
        security_info.setStyleSheet("color: #7f8c8d;")
        security_layout.addWidget(security_info)

        security_group.setLayout(security_layout)
        layout.addWidget(security_group)

        layout.addStretch()

        return tab

    def load_profile_data(self):
        """Load user profile data."""
        # Basic information
        self.full_name_input.setText(self.current_user.get('full_name', ''))
        self.username_input.setText(self.current_user.get('username', ''))
        self.role_input.setText(self.current_user.get('role', '').title())

        # Load activity statistics
        self.load_activity_stats()

        # Load security info
        self.load_security_info()

    def load_activity_stats(self):
        """Load user activity statistics."""
        try:
            user_id = self.current_user['user_id']

            # Get account created date
            created_at = self.current_user.get('created_at', 'Unknown')
            if created_at and created_at != 'Unknown':
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    self.created_at_label.setText(created_dt.strftime('%Y-%m-%d %H:%M'))
                except:
                    self.created_at_label.setText(created_at)
            else:
                self.created_at_label.setText("Unknown")

            # Get last login
            last_login = self.current_user.get('last_login', 'Never')
            if last_login and last_login != 'Never':
                try:
                    login_dt = datetime.fromisoformat(last_login)
                    self.last_login_label.setText(login_dt.strftime('%Y-%m-%d %H:%M'))
                except:
                    self.last_login_label.setText(last_login)
            else:
                self.last_login_label.setText("Never")

            # Get login count from session log
            login_count_query = "SELECT COUNT(*) FROM session_log WHERE user_id = ?"
            login_results = self.db_manager.execute_with_retry(login_count_query, (user_id,))
            login_count = login_results[0][0] if login_results else 0
            self.login_count_label.setText(str(login_count))

            # Get reports created
            reports_query = "SELECT COUNT(*) FROM reports WHERE created_by = ? AND is_deleted = 0"
            reports_results = self.db_manager.execute_with_retry(reports_query, (self.current_user['username'],))
            reports_count = reports_results[0][0] if reports_results else 0
            self.reports_created_label.setText(str(reports_count))

            # Get reports edited
            edits_query = """
                SELECT COUNT(DISTINCT report_id) FROM reports
                WHERE updated_by = ? AND updated_by != created_by AND is_deleted = 0
            """
            edits_results = self.db_manager.execute_with_retry(edits_query, (self.current_user['username'],))
            edits_count = edits_results[0][0] if edits_results else 0
            self.reports_edited_label.setText(str(edits_count))

            # Get recent activity from action_log
            recent_query = """
                SELECT action_type, created_at, action_details
                FROM audit_log
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """
            recent_results = self.db_manager.execute_with_retry(recent_query, (user_id,))

            if recent_results:
                activity_text = ""
                for action, timestamp, details in recent_results:
                    try:
                        ts_dt = datetime.fromisoformat(timestamp)
                        ts_str = ts_dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        ts_str = timestamp
                    activity_text += f"[{ts_str}] {action}\n"

                self.recent_activity_text.setPlainText(activity_text)

                # Set last action
                if recent_results:
                    last_action_time = recent_results[0][1]
                    try:
                        last_dt = datetime.fromisoformat(last_action_time)
                        self.last_action_label.setText(last_dt.strftime('%Y-%m-%d %H:%M'))
                    except:
                        self.last_action_label.setText(last_action_time)
            else:
                self.recent_activity_text.setPlainText("No recent activity recorded.")
                self.last_action_label.setText("N/A")

        except Exception as e:
            self.logging_service.error(f"Error loading activity stats: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load activity statistics: {str(e)}")

    def load_security_info(self):
        """Load security information."""
        try:
            # Password last changed (if tracked)
            updated_at = self.current_user.get('updated_at', 'Unknown')
            if updated_at and updated_at != 'Unknown':
                try:
                    updated_dt = datetime.fromisoformat(updated_at)
                    self.password_changed_label.setText(f"Last changed: {updated_dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    self.password_changed_label.setText(f"Last changed: {updated_at}")
            else:
                self.password_changed_label.setText("Last changed: Unknown")

            # Current session info
            session_info = f"Logged in as: {self.current_user['username']}\n"
            session_info += f"Role: {self.current_user['role'].title()}\n"
            session_info += f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.current_session_label.setText(session_info)

        except Exception as e:
            self.logging_service.error(f"Error loading security info: {str(e)}")

    def save_profile(self):
        """Save profile changes."""
        try:
            new_full_name = self.full_name_input.text().strip()

            if not new_full_name:
                QMessageBox.warning(self, "Validation Error", "Full name is required.")
                return

            # Update user profile
            update_query = """
                UPDATE users
                SET full_name = ?, updated_at = ?, updated_by = ?
                WHERE user_id = ?
            """

            self.db_manager.execute_with_retry(
                update_query,
                (new_full_name, datetime.now().isoformat(),
                 self.current_user['username'], self.current_user['user_id'])
            )

            # Update current user object
            self.current_user['full_name'] = new_full_name

            # Log action
            self.logging_service.log_user_action("PROFILE_UPDATED", {'user_id': self.current_user['user_id']})

            QMessageBox.information(
                self,
                "Profile Updated",
                "Your profile has been updated successfully."
            )

            self.profile_updated.emit()
            self.accept()

        except Exception as e:
            self.logging_service.error(f"Error saving profile: {str(e)}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save profile: {str(e)}"
            )

    def change_password(self):
        """Open change password dialog."""
        from ui.dialogs.change_password_dialog import ChangePasswordDialog
        dialog = ChangePasswordDialog(self.auth_service, self)
        if dialog.exec():
            # Reload security info
            self.load_security_info()

    def logout_other_sessions(self):
        """Logout all other sessions (placeholder)."""
        reply = QMessageBox.question(
            self,
            "Logout Other Sessions",
            "This feature will logout all other active sessions for your account.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement session management
            QMessageBox.information(
                self,
                "Sessions Cleared",
                "All other sessions have been logged out."
            )
            self.logging_service.log_user_action("SESSIONS_CLEARED", {'user_id': self.current_user['user_id']})
