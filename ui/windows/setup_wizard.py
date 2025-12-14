"""
Setup Wizard for FIU Report Management System.
Modern multi-step wizard for first-time setup.
"""

from PyQt6.QtWidgets import (QWidget, QWizard, QWizardPage, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFileDialog, QMessageBox, QProgressBar, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap
from pathlib import Path
from database.init_db import initialize_database
from ui.theme_colors import ThemeColors


class DatabaseCreationWorker(QThread):
    """Worker thread for database creation."""

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)

    def __init__(self, db_path, backup_path):
        super().__init__()
        self.db_path = db_path
        self.backup_path = backup_path

    def run(self):
        """Create database in background."""
        try:
            self.progress.emit(10, "Creating directories...")

            # Create directories
            db_file = Path(self.db_path)
            if not str(db_file).lower().endswith('.db'):
                db_file = Path(str(db_file) + '.db')
                self.db_path = str(db_file)

            db_file.parent.mkdir(parents=True, exist_ok=True)
            Path(self.backup_path).mkdir(parents=True, exist_ok=True)

            self.progress.emit(40, "Initializing database schema...")

            # Initialize database
            success, message = initialize_database(self.db_path)

            if not success:
                self.finished.emit(False, message)
                return

            self.progress.emit(90, "Finalizing setup...")
            self.progress.emit(100, "Setup completed successfully!")

            self.finished.emit(True, "Database created successfully")

        except Exception as e:
            self.finished.emit(False, f"Error creating database: {str(e)}")


class WelcomePage(QWizardPage):
    """Welcome page for the setup wizard."""

    def __init__(self):
        super().__init__()
        self.setTitle("Welcome")
        self.setSubTitle("FIU Report Management System Setup")

        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Welcome message
        welcome_frame = QFrame()
        welcome_frame.setObjectName("card")
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setContentsMargins(30, 30, 30, 30)
        welcome_layout.setSpacing(15)

        title = QLabel("Welcome to FIU Report Management System")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setWordWrap(True)
        welcome_layout.addWidget(title)

        description = QLabel(
            "This wizard will help you set up the Financial Intelligence Unit "
            "Report Management System.\n\n"
            "You will configure:\n"
            "• Database location\n"
            "• Backup directory\n"
            "• Initial system settings\n\n"
            "Click 'Next' to continue with the setup."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; line-height: 1.6;")
        welcome_layout.addWidget(description)

        welcome_layout.addStretch()

        layout.addWidget(welcome_frame)
        layout.addStretch()

        self.setLayout(layout)


class PathConfigurationPage(QWizardPage):
    """Path configuration page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Configure Paths")
        self.setSubTitle("Select database and backup locations")

        # Default paths
        default_base = Path.home() / "FIU_System"
        default_db_path = str(default_base / "database" / "fiu_reports.db")
        default_backup_path = str(default_base / "backups")

        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Database path section
        db_frame = QFrame()
        db_frame.setObjectName("card")
        db_layout = QVBoxLayout(db_frame)
        db_layout.setContentsMargins(20, 20, 20, 20)

        db_title = QLabel("Database File Location")
        db_title.setStyleSheet(f"font-weight: 600; font-size: 11pt; color: {ThemeColors.TEXT_PRIMARY};")
        db_layout.addWidget(db_title)

        db_desc = QLabel("Choose where to store the main database file")
        db_desc.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 9pt;")
        db_layout.addWidget(db_desc)

        db_input_layout = QHBoxLayout()
        self.db_path_input = QLineEdit()
        self.db_path_input.setText(default_db_path)
        self.db_path_input.setMinimumHeight(36)
        self.registerField("db_path*", self.db_path_input)
        db_input_layout.addWidget(self.db_path_input)

        db_browse_btn = QPushButton("Browse...")
        db_browse_btn.setMaximumWidth(100)
        db_browse_btn.clicked.connect(self.browse_db_path)
        db_input_layout.addWidget(db_browse_btn)

        db_layout.addLayout(db_input_layout)
        layout.addWidget(db_frame)

        # Backup path section
        backup_frame = QFrame()
        backup_frame.setObjectName("card")
        backup_layout = QVBoxLayout(backup_frame)
        backup_layout.setContentsMargins(20, 20, 20, 20)

        backup_title = QLabel("Backup Directory")
        backup_title.setStyleSheet(f"font-weight: 600; font-size: 11pt; color: {ThemeColors.TEXT_PRIMARY};")
        backup_layout.addWidget(backup_title)

        backup_desc = QLabel("Choose where to store automatic backups")
        backup_desc.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 9pt;")
        backup_layout.addWidget(backup_desc)

        backup_input_layout = QHBoxLayout()
        self.backup_path_input = QLineEdit()
        self.backup_path_input.setText(default_backup_path)
        self.backup_path_input.setMinimumHeight(36)
        self.registerField("backup_path*", self.backup_path_input)
        backup_input_layout.addWidget(self.backup_path_input)

        backup_browse_btn = QPushButton("Browse...")
        backup_browse_btn.setMaximumWidth(100)
        backup_browse_btn.clicked.connect(self.browse_backup_path)
        backup_input_layout.addWidget(backup_browse_btn)

        backup_layout.addLayout(backup_input_layout)
        layout.addWidget(backup_frame)

        layout.addStretch()
        self.setLayout(layout)

    def browse_db_path(self):
        """Browse for database file path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database File Location",
            self.db_path_input.text(),
            "SQLite Database (*.db)"
        )
        if file_path:
            self.db_path_input.setText(file_path)

    def browse_backup_path(self):
        """Browse for backup directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Directory",
            self.backup_path_input.text()
        )
        if dir_path:
            self.backup_path_input.setText(dir_path)

    def validatePage(self):
        """Validate paths before proceeding."""
        db_path = self.db_path_input.text().strip()
        backup_path = self.backup_path_input.text().strip()

        if not db_path or not backup_path:
            QMessageBox.warning(
                self,
                "Invalid Paths",
                "Please specify both database and backup paths."
            )
            return False

        # Check if database already exists
        db_file = Path(db_path)
        if not str(db_file).lower().endswith('.db'):
            db_file = Path(str(db_file) + '.db')

        if db_file.exists():
            reply = QMessageBox.question(
                self,
                "Database Exists",
                f"A database already exists at:\n{db_file}\n\n"
                "Do you want to use the existing database?\n\n"
                "Click 'Yes' to use existing database.\n"
                "Click 'No' to create a new one (this will overwrite the existing file).",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return False
            elif reply == QMessageBox.StandardButton.Yes:
                # Set flag to skip database creation
                self.wizard().setProperty("use_existing_db", True)
                return True
            # If No, proceed with creation (will overwrite)

        self.wizard().setProperty("use_existing_db", False)
        return True


class CreationPage(QWizardPage):
    """Database creation progress page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Creating Database")
        self.setSubTitle("Please wait while we set up your system")
        self.setCommitPage(True)
        self.worker = None

        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Progress frame
        progress_frame = QFrame()
        progress_frame.setObjectName("card")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(30, 30, 30, 30)
        progress_layout.setSpacing(15)

        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet(f"font-size: 11pt; color: {ThemeColors.TEXT_PRIMARY};")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(8)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_frame)
        layout.addStretch()

        self.setLayout(layout)

    def initializePage(self):
        """Start database creation when page is shown."""
        # Check if using existing database
        if self.wizard().property("use_existing_db"):
            self.status_label.setText("Using existing database...")
            self.progress_bar.setValue(100)
            self.completeChanged.emit()
            return

        # Get paths from previous page
        db_path = self.field("db_path")
        backup_path = self.field("backup_path")

        # Create database in background
        self.worker = DatabaseCreationWorker(db_path, backup_path)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, value, message):
        """Update progress."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_finished(self, success, message):
        """Handle completion."""
        if success:
            self.status_label.setText("✓ " + message)
            self.status_label.setStyleSheet("font-size: 11pt; color: #27ae60; font-weight: 600;")
            self.progress_bar.setValue(100)
            self.wizard().setProperty("setup_success", True)
        else:
            self.status_label.setText("✗ " + message)
            self.status_label.setStyleSheet("font-size: 11pt; color: #e74c3c; font-weight: 600;")
            self.wizard().setProperty("setup_success", False)
            QMessageBox.critical(self, "Setup Error", message)

        self.completeChanged.emit()

    def isComplete(self):
        """Page is complete when worker finishes."""
        if self.wizard().property("use_existing_db"):
            return True

        return (self.worker is not None and
                not self.worker.isRunning() and
                self.wizard().property("setup_success") == True)


class CompletionPage(QWizardPage):
    """Final completion page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("Your system is ready to use")
        self.setFinalPage(True)

        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Success frame
        success_frame = QFrame()
        success_frame.setObjectName("card")
        success_layout = QVBoxLayout(success_frame)
        success_layout.setContentsMargins(30, 30, 30, 30)
        success_layout.setSpacing(15)

        check_label = QLabel("✓")
        check_label.setStyleSheet("font-size: 48pt; color: #27ae60;")
        check_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(check_label)

        title = QLabel("Setup Completed Successfully!")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(title)

        info = QLabel(
            "Your FIU Report Management System has been configured.\n\n"
            "Default admin credentials:\n"
            "Username: admin\n"
            "Password: admin123\n\n"
            "⚠ Please change these credentials after your first login.\n\n"
            "Click 'Finish' to proceed to the login screen."
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; line-height: 1.6;")
        success_layout.addWidget(info)

        layout.addWidget(success_frame)
        layout.addStretch()

        self.setLayout(layout)


class SetupWizard(QWizard):
    """Main setup wizard window."""

    setup_completed = pyqtSignal(str, str)  # db_path, backup_path

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FIU System Setup Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(700, 500)

        # Add pages
        self.addPage(WelcomePage())
        self.addPage(PathConfigurationPage())
        self.addPage(CreationPage())
        self.addPage(CompletionPage())

        # Set button text
        self.setButtonText(QWizard.WizardButton.NextButton, "Next →")
        self.setButtonText(QWizard.WizardButton.BackButton, "← Back")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Finish")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Cancel")

        # Connect finish signal
        self.finished.connect(self.on_finished)

    def on_finished(self, result):
        """Handle wizard completion."""
        if result == QWizard.DialogCode.Accepted:
            db_path = self.field("db_path")
            backup_path = self.field("backup_path")

            # Ensure .db extension
            if not str(db_path).lower().endswith('.db'):
                db_path = str(db_path) + '.db'

            self.setup_completed.emit(db_path, backup_path)
