"""
Maintenance Service — scheduled background upkeep.

- R80: auto-purge soft-deleted reports past the retention window (daily).
- R107: automated database backup (weekly). No manual admin trigger.

Uses daemon threads with interval sleeps (matches the existing reservation
cleanup pattern); the app is a long-running desktop process.
"""
import os
import time
import shutil
import sqlite3
import threading
from datetime import datetime
from typing import Tuple, Optional


class MaintenanceService:
    def __init__(self, db_manager, logging_service, report_service,
                 backup_dir: Optional[str] = None, settings_service=None):
        self.db_manager = db_manager
        self.logger = logging_service
        self.report_service = report_service
        self.backup_dir = backup_dir
        self.settings_service = settings_service
        self._running = False
        self._threads = []

    # ---- retention ----------------------------------------------------
    def _retention_days(self) -> int:
        try:
            row = self.db_manager.execute_with_retry(
                "SELECT config_value FROM system_config WHERE config_key = 'backup_retention_days'")
            if row and row[0][0]:
                return max(1, int(row[0][0]))
        except Exception:
            pass
        return 30

    def run_purge(self) -> Tuple[int, str]:
        """Hard-delete reports soft-deleted beyond the retention window (R80)."""
        return self.report_service.purge_expired_deleted_reports(self._retention_days())

    # ---- backup -------------------------------------------------------
    def run_backup(self) -> Tuple[bool, str]:
        """Consistent DB snapshot into the backup directory (R107)."""
        try:
            if not self.backup_dir:
                return False, "No backup directory configured"
            os.makedirs(self.backup_dir, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = f"fiu_backup_{stamp}.db"
            dest = os.path.join(self.backup_dir, fname)

            # sqlite online backup API -> consistent even while in use
            src = sqlite3.connect(self.db_manager.db_path)
            dst = sqlite3.connect(dest)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()

            size = os.path.getsize(dest)
            self.db_manager.execute_with_retry(
                "INSERT INTO backup_log (backup_filename, backup_path, backup_size, created_by) "
                "VALUES (?, ?, ?, 'SYSTEM')", (fname, dest, size))
            self.logger.info(f"Database backup created: {fname} ({size} bytes)")
            return True, dest
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}", exc_info=True)
            return False, f"Backup failed: {str(e)}"

    # ---- schedulers ---------------------------------------------------
    def start(self):
        if self._running:
            return
        self._running = True

        def purge_loop():
            # first pass shortly after startup, then daily
            time.sleep(60)
            while self._running:
                try:
                    self.run_purge()
                except Exception as e:
                    self.logger.error(f"Purge loop error: {e}")
                time.sleep(24 * 3600)

        def backup_loop():
            # back up once at startup, then weekly
            while self._running:
                try:
                    self.run_backup()
                except Exception as e:
                    self.logger.error(f"Backup loop error: {e}")
                time.sleep(7 * 24 * 3600)

        for target, name in ((purge_loop, "AutoPurge"), (backup_loop, "WeeklyBackup")):
            t = threading.Thread(target=target, daemon=True, name=name)
            t.start()
            self._threads.append(t)
        self.logger.info("Maintenance schedulers started (purge daily, backup weekly)")

    def stop(self):
        self._running = False
