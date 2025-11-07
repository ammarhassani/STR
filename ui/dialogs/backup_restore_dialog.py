"""
Backup & Restore Dialog
Comprehensive backup and restore functionality for database.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QFileDialog, QProgressBar,
                             QGroupBox, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt6.QtGui import QFont
from pathlib import Path
from datetime import datetime
import shutil
import sqlite3
from services.icon_service import get_icon


class BackupWorker(QThread):
    """Worker thread for creating backups."""

    finished = pyqtSignal(bool, str, str)  # success, message, file_path
    progress = pyqtSignal(int, str)

    def __init__(self, source_db_path, backup_dir):
        super().__init__()
        self.source_db_path = source_db_path
        self.backup_dir = backup_dir

    def run(self):
        """Create database backup."""
        try:
            self.progress.emit(10, "Preparing backup...")

            # Create backup directory if it doesn't exist
            backup_path = Path(self.backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)

            self.progress.emit(30, "Creating backup...")

            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"fiu_backup_{timestamp}.db"
            backup_file_path = backup_path / backup_filename

            # Copy database file
            shutil.copy2(self.source_db_path, str(backup_file_path))

            self.progress.emit(70, "Verifying backup...")

            # Verify backup integrity
            try:
                conn = sqlite3.connect(str(backup_file_path))
                conn.execute("PRAGMA integrity_check")
                conn.close()
            except Exception as e:
                raise Exception(f"Backup verification failed: {str(e)}")

            self.progress.emit(100, "Backup completed!")

            self.finished.emit(
                True,
                f"Backup created successfully:\n{backup_file_path}",
                str(backup_file_path)
            )

        except Exception as e:
            self.finished.emit(False, f"Backup failed: {str(e)}", "")


class RestoreWorker(QThread):
    """Worker thread for restoring from backup."""

    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(int, str)

    def __init__(self, backup_file_path, target_db_path):
        super().__init__()
        self.backup_file_path = backup_file_path
        self.target_db_path = target_db_path

    def run(self):
        """Restore database from backup."""
        try:
            self.progress.emit(10, "Verifying backup file...")

            # Verify backup file exists
            if not Path(self.backup_file_path).exists():
                raise Exception("Backup file not found")

            # Verify backup integrity
            try:
                conn = sqlite3.connect(self.backup_file_path)
                conn.execute("PRAGMA integrity_check")
                conn.close()
            except Exception as e:
                raise Exception(f"Backup file is corrupted: {str(e)}")

            self.progress.emit(40, "Creating backup of current database...")

            # Create backup of current database before restoring
            current_db_path = Path(self.target_db_path)
            if current_db_path.exists():
                backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_backup = current_db_path.parent / f"pre_restore_backup_{backup_timestamp}.db"
                shutil.copy2(str(current_db_path), str(temp_backup))

            self.progress.emit(70, "Restoring database...")

            # Restore database
            shutil.copy2(self.backup_file_path, self.target_db_path)

            self.progress.emit(100, "Restore completed!")

            self.finished.emit(
                True,
                "Database restored successfully!\n\nPlease restart the application to complete the restore process."
            )

        except Exception as e:
            self.finished.emit(False, f"Restore failed: {str(e)}")


class BackupRestoreDialog(QDialog):
    """
    Dialog for database backup and restore operations.

    Features:
    - Create manual backups
    - View existing backups
    - Restore from backups
    - Delete old backups
    - Export/import backups
    """

    backup_created = pyqtSignal(str)  # backup_file_path
    restore_completed = pyqtSignal()

    def __init__(self, db_manager, config, logging_service, parent=None):
        """
        Initialize backup/restore dialog.

        Args:
            db_manager: DatabaseManager instance
            config: Config object
            logging_service: LoggingService instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.config = config
        self.logging_service = logging_service
        self.backup_worker = None
        self.restore_worker = None

        self.setup_ui()
        self.refresh_backup_list()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Backup & Restore")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("Database Backup & Restore")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        layout.addWidget(header)

        # Info label
        info_label = QLabel(
            "Create backups of your database to protect against data loss. "
            "You can restore from any backup to revert to a previous state."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(info_label)

        # Backup actions group
        actions_group = QGroupBox("Backup Actions")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        create_backup_btn = QPushButton("Create Backup Now")
        create_backup_btn.setIcon(get_icon('save'))
        create_backup_btn.setObjectName("primaryButton")
        create_backup_btn.clicked.connect(self.create_backup)
        actions_layout.addWidget(create_backup_btn)

        import_backup_btn = QPushButton("Import Backup")
        import_backup_btn.setIcon(get_icon('download'))
        import_backup_btn.clicked.connect(self.import_backup)
        actions_layout.addWidget(import_backup_btn)

        open_folder_btn = QPushButton("Open Backup Folder")
        open_folder_btn.setIcon(get_icon('folder-open'))
        open_folder_btn.clicked.connect(self.open_backup_folder)
        actions_layout.addWidget(open_folder_btn)

        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Existing backups group
        backups_group = QGroupBox("Existing Backups")
        backups_layout = QVBoxLayout()

        # Backup list
        self.backup_list = QListWidget()
        self.backup_list.setMinimumHeight(250)
        self.backup_list.currentItemChanged.connect(self.on_backup_selected)
        backups_layout.addWidget(self.backup_list)

        # Backup info
        self.backup_info_text = QTextEdit()
        self.backup_info_text.setReadOnly(True)
        self.backup_info_text.setMaximumHeight(100)
        self.backup_info_text.setPlaceholderText("Select a backup to view details...")
        backups_layout.addWidget(self.backup_info_text)

        # Backup actions
        backup_actions_layout = QHBoxLayout()

        self.restore_btn = QPushButton("Restore Selected")
        self.restore_btn.setIcon(get_icon('refresh'))
        self.restore_btn.setObjectName("primaryButton")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.restore_backup)
        backup_actions_layout.addWidget(self.restore_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.setIcon(get_icon('file-export'))
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_backup)
        backup_actions_layout.addWidget(self.export_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(get_icon('trash'))
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_backup)
        backup_actions_layout.addWidget(self.delete_btn)

        backup_actions_layout.addStretch()
        backups_layout.addLayout(backup_actions_layout)

        backups_group.setLayout(backups_layout)
        layout.addWidget(backups_group)

        # Progress section
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("card")
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 16, 16, 16)

        self.progress_label = QLabel("Processing...")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(6)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_frame)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        refresh_btn = QPushButton("Refresh List")
        refresh_btn.setIcon(get_icon('refresh'))
        refresh_btn.clicked.connect(self.refresh_backup_list)
        button_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.setIcon(get_icon('times'))
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def refresh_backup_list(self):
        """Refresh the list of available backups."""
        self.backup_list.clear()
        self.backup_info_text.clear()

        try:
            backup_dir = Path(self.config.BACKUP_PATH)
            if not backup_dir.exists():
                backup_dir.mkdir(parents=True, exist_ok=True)
                return

            # Find all backup files
            backup_files = list(backup_dir.glob("*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            for backup_file in backup_files:
                item = QListWidgetItem(backup_file.name)
                item.setData(Qt.ItemDataRole.UserRole, str(backup_file))

                # Get file size and modified time
                file_stat = backup_file.stat()
                file_size = file_stat.st_size / (1024 * 1024)  # Convert to MB
                modified_time = datetime.fromtimestamp(file_stat.st_mtime)

                tooltip = f"Size: {file_size:.2f} MB\nModified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"
                item.setToolTip(tooltip)

                self.backup_list.addItem(item)

            if self.backup_list.count() == 0:
                item = QListWidgetItem("No backups found")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.backup_list.addItem(item)

        except Exception as e:
            self.logging_service.error(f"Error refreshing backup list: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load backup list: {str(e)}")

    def on_backup_selected(self, current, previous):
        """
        Handle backup selection.

        Args:
            current: Current list item
            previous: Previous list item
        """
        if not current or not current.data(Qt.ItemDataRole.UserRole):
            self.restore_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.backup_info_text.clear()
            return

        self.restore_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        # Show backup info
        backup_path = Path(current.data(Qt.ItemDataRole.UserRole))
        file_stat = backup_path.stat()
        file_size = file_stat.st_size / (1024 * 1024)
        created_time = datetime.fromtimestamp(file_stat.st_ctime)
        modified_time = datetime.fromtimestamp(file_stat.st_mtime)

        info_text = f"""<b>Backup Information</b><br><br>
<b>File:</b> {backup_path.name}<br>
<b>Size:</b> {file_size:.2f} MB<br>
<b>Created:</b> {created_time.strftime('%Y-%m-%d %H:%M:%S')}<br>
<b>Modified:</b> {modified_time.strftime('%Y-%m-%d %H:%M:%S')}<br>
<b>Path:</b> {str(backup_path)}
"""
        self.backup_info_text.setHtml(info_text)

    def create_backup(self):
        """Create a new database backup."""
        reply = QMessageBox.question(
            self,
            "Create Backup",
            "Create a backup of the current database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Show progress
            self.progress_frame.setVisible(True)
            self.progress_bar.setValue(0)

            # Create worker
            db_path = self.config.DATABASE_PATH
            backup_dir = self.config.BACKUP_PATH

            self.backup_worker = BackupWorker(db_path, backup_dir)
            self.backup_worker.progress.connect(self.on_progress)
            self.backup_worker.finished.connect(self.on_backup_finished)
            self.backup_worker.start()

    def on_backup_finished(self, success: bool, message: str, file_path: str):
        """
        Handle backup completion.

        Args:
            success: Whether backup was successful
            message: Result message
            file_path: Backup file path
        """
        self.progress_frame.setVisible(False)

        if success:
            QMessageBox.information(self, "Backup Success", message)
            self.backup_created.emit(file_path)
            self.refresh_backup_list()
            self.logging_service.log_user_action("BACKUP_CREATED", {'file_path': file_path})
        else:
            QMessageBox.critical(self, "Backup Failed", message)
            self.logging_service.error(f"Backup failed: {message}")

    def restore_backup(self):
        """Restore database from selected backup."""
        current_item = self.backup_list.currentItem()
        if not current_item:
            return

        backup_path = current_item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.warning(
            self,
            "Restore Database",
            "⚠️ WARNING ⚠️\n\n"
            "Restoring from a backup will replace your current database.\n"
            "All changes made since this backup will be lost!\n\n"
            "A backup of your current database will be created first.\n\n"
            "Are you absolutely sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Show progress
            self.progress_frame.setVisible(True)
            self.progress_bar.setValue(0)

            # Create worker
            target_db_path = self.config.DATABASE_PATH

            self.restore_worker = RestoreWorker(backup_path, target_db_path)
            self.restore_worker.progress.connect(self.on_progress)
            self.restore_worker.finished.connect(self.on_restore_finished)
            self.restore_worker.start()

    def on_restore_finished(self, success: bool, message: str):
        """
        Handle restore completion.

        Args:
            success: Whether restore was successful
            message: Result message
        """
        self.progress_frame.setVisible(False)

        if success:
            QMessageBox.information(
                self,
                "Restore Success",
                message
            )
            self.restore_completed.emit()
            self.logging_service.log_user_action("DATABASE_RESTORED", {})
        else:
            QMessageBox.critical(self, "Restore Failed", message)
            self.logging_service.error(f"Restore failed: {message}")

    def export_backup(self):
        """Export selected backup to a chosen location."""
        current_item = self.backup_list.currentItem()
        if not current_item:
            return

        backup_path = current_item.data(Qt.ItemDataRole.UserRole)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backup",
            str(Path.home() / Path(backup_path).name),
            "Database Files (*.db);;All Files (*)"
        )

        if file_path:
            try:
                shutil.copy2(backup_path, file_path)
                QMessageBox.information(
                    self,
                    "Export Success",
                    f"Backup exported to:\n{file_path}"
                )
                self.logging_service.log_user_action("BACKUP_EXPORTED", {'file_path': file_path})
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export backup:\n{str(e)}"
                )

    def import_backup(self):
        """Import a backup file from external location."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Backup",
            str(Path.home()),
            "Database Files (*.db);;All Files (*)"
        )

        if file_path:
            try:
                backup_dir = Path(self.config.BACKUP_PATH)
                backup_dir.mkdir(parents=True, exist_ok=True)

                # Copy to backup directory with new name
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"imported_backup_{timestamp}.db"
                new_path = backup_dir / new_filename

                shutil.copy2(file_path, str(new_path))

                QMessageBox.information(
                    self,
                    "Import Success",
                    f"Backup imported successfully as:\n{new_filename}"
                )
                self.refresh_backup_list()
                self.logging_service.log_user_action("BACKUP_IMPORTED", {'file_path': str(new_path)})
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    f"Failed to import backup:\n{str(e)}"
                )

    def delete_backup(self):
        """Delete selected backup."""
        current_item = self.backup_list.currentItem()
        if not current_item:
            return

        backup_path = Path(current_item.data(Qt.ItemDataRole.UserRole))

        reply = QMessageBox.question(
            self,
            "Delete Backup",
            f"Are you sure you want to delete this backup?\n\n{backup_path.name}\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                backup_path.unlink()
                QMessageBox.information(self, "Deleted", "Backup deleted successfully.")
                self.refresh_backup_list()
                self.logging_service.log_user_action("BACKUP_DELETED", {'file_path': str(backup_path)})
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    f"Failed to delete backup:\n{str(e)}"
                )

    def open_backup_folder(self):
        """Open the backup folder in file explorer."""
        try:
            backup_dir = Path(self.config.BACKUP_PATH)
            backup_dir.mkdir(parents=True, exist_ok=True)

            import os
            import subprocess
            import platform

            if platform.system() == 'Windows':
                os.startfile(str(backup_dir))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', str(backup_dir)])
            else:  # Linux
                subprocess.Popen(['xdg-open', str(backup_dir)])

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open backup folder:\n{str(e)}"
            )

    def on_progress(self, value: int, message: str):
        """
        Handle progress updates.

        Args:
            value: Progress value (0-100)
            message: Progress message
        """
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
