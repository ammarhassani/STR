"""
Report Number Service - Concurrent-Safe Number Generation
Handles report number and serial number generation using an owned-block
reservation model: a user reserves a block of numbers up front
(reserve_block), and consumes them one at a time when saving a report
(consume_next_available). See reserve_block/get_available_numbers/
get_available_count/consume_next_available/transfer_numbers below.

This service is designed to handle concurrent access from multiple users safely.
"""

import re
import sqlite3
from typing import Tuple, Optional, Dict, List
from datetime import datetime, timedelta


class ReportNumberService:
    """
    Thread-safe service for managing report numbers and serial numbers.

    Key Features:
    - Database-level locking for atomicity
    - Owned-block reservation (reserve_block / consume_next_available)
    - Month close / grace period (R50, R51)
    """

    def __init__(self, db_manager, logging_service):
        """
        Initialize the report number service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service

    def _generate_next_numbers(self, cursor) -> Tuple[str, int]:
        """
        Generate the next sequential report number and serial number.

        Report Number Format: YYYY/MM/NNN (resets each month)
        Serial Number: Global incrementing counter (never resets)

        Uses grace period for month transitions (configurable, default 3 days).

        Args:
            cursor: Database cursor (must be in transaction)

        Returns:
            Tuple of (report_number, serial_number)
        """
        # Month prefix respects admin month-close (R50/R51): numbering stays in
        # the open month until an admin closes it, then advances by one.
        prefix = self._active_month(cursor) + "/"

        # Get next report number for this month
        # Extract the maximum number from existing reports (not COUNT!)
        cursor.execute("""
            SELECT report_number
            FROM reports
            WHERE report_number LIKE ?
            ORDER BY report_number DESC
            LIMIT 1
        """, (f"{prefix}%",))

        result = cursor.fetchone()
        max_existing_num = 0
        if result:
            # Extract number from "2025/11/003" -> 3
            last_report = result[0]
            max_existing_num = int(last_report.split('/')[-1])

        # Also check reserved numbers for this month
        cursor.execute("""
            SELECT report_number
            FROM report_number_reservations
            WHERE report_number LIKE ? AND is_used = 0
            ORDER BY report_number DESC
            LIMIT 1
        """, (f"{prefix}%",))

        result = cursor.fetchone()
        max_reserved_num = 0
        if result:
            # Extract number from "2025/11/003" -> 3
            last_reserved = result[0]
            max_reserved_num = int(last_reserved.split('/')[-1])

        # Also check owned-block reservations (reserved_numbers): these hold
        # report_number permanently (UNIQUE NOT NULL), including numbers
        # allocated earlier in the *same* reserve_block loop/transaction —
        # without this a multi-number reserve_block would generate the same
        # number repeatedly and hit the UNIQUE constraint.
        cursor.execute("""
            SELECT report_number
            FROM reserved_numbers
            WHERE report_number LIKE ?
            ORDER BY report_number DESC
            LIMIT 1
        """, (f"{prefix}%",))
        result = cursor.fetchone()
        max_block_num = 0
        if result:
            max_block_num = int(result[0].split('/')[-1])

        # Next number is max of all three + 1 (ensures no conflicts!)
        next_num = max(max_existing_num, max_reserved_num, max_block_num) + 1
        report_number = f"{prefix}{next_num:03d}"

        # Get next serial number (global counter)
        cursor.execute("SELECT COALESCE(MAX(sn), 0) FROM reports")
        max_sn = cursor.fetchone()[0]

        # Also check reserved serial numbers
        cursor.execute("SELECT COALESCE(MAX(serial_number), 0) FROM report_number_reservations WHERE is_used = 0")
        max_reserved_sn = cursor.fetchone()[0]

        # Also check owned-block serial numbers (serial_number is UNIQUE NOT NULL)
        cursor.execute("SELECT COALESCE(MAX(serial_number), 0) FROM reserved_numbers")
        max_block_sn = cursor.fetchone()[0]

        serial_number = max(max_sn, max_reserved_sn, max_block_sn) + 1

        return report_number, serial_number

    def _get_month_grace_period(self, cursor) -> int:
        """
        Get month grace period setting from system config.

        Args:
            cursor: Database cursor

        Returns:
            Grace period in days (default: 3)
        """
        try:
            cursor.execute("""
                SELECT config_value
                FROM system_config
                WHERE config_key = 'month_grace_period'
                  AND is_active = 1
            """)
            result = cursor.fetchone()
            if result:
                return int(result[0])
        except:
            pass
        return 3  # Default to 3 days

    def get_month_with_grace_period(self, grace_days: int = 3) -> str:
        """
        Get the current month for report numbering with grace period.

        Example: If grace_days=3:
        - On Dec 1st, 2nd, 3rd → returns "2025/11" (still November)
        - On Dec 4th onwards → returns "2025/12" (December)

        Args:
            grace_days: Number of days into new month to keep using previous month

        Returns:
            Month prefix as "YYYY/MM"
        """
        now = datetime.now()

        # If we're within the grace period of a new month, use previous month
        if now.day <= grace_days and grace_days > 0:
            # Go back to previous month
            if now.month == 1:
                # January -> previous December
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = now.month - 1
        else:
            year = now.year
            month = now.month

        return f"{year}/{month:02d}"

    # ---- Month close / grace period (R50, R51) ------------------------
    @staticmethod
    def _next_month(month: str) -> str:
        """'2025/07' -> '2025/08', '2025/12' -> '2026/01'."""
        y, m = int(month[:4]), int(month[5:7])
        return f"{y+1}/01" if m == 12 else f"{y}/{m+1:02d}"

    def _active_month(self, cursor) -> str:
        """The month numbering should use RIGHT NOW. Numbering never advances by
        the calendar on its own (grace period, R50); it advances only when an
        admin closes the current month (R51). So: one past the latest closed
        month, else the month of the latest existing report, else this month."""
        cursor.execute("SELECT MAX(month) FROM closed_months")
        row = cursor.fetchone()
        if row and row[0]:
            return self._next_month(row[0])
        cursor.execute(
            "SELECT MAX(substr(report_number, 1, 7)) FROM reports "
            "WHERE report_number GLOB '[0-9][0-9][0-9][0-9]/[0-9][0-9]/*'")
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        now = datetime.now()
        return f"{now.year}/{now.month:02d}"

    def is_month_closed(self, month: str) -> bool:
        try:
            r = self.db_manager.execute_with_retry(
                "SELECT 1 FROM closed_months WHERE month = ?", (month,))
            return bool(r)
        except Exception:
            return False

    def close_month(self, month: str, username: str) -> Tuple[bool, str]:
        """Close a numbering month so numbering advances to the next (R51).
        Admin only; a closed month can never be reopened (no such method)."""
        try:
            if not re.match(r'^\d{4}/(0[1-9]|1[0-2])$', str(month)):
                return False, "Invalid month format (expected YYYY/MM)"
            who = self.db_manager.execute_with_retry(
                "SELECT role FROM users WHERE username = ? AND is_active = 1", (username,))
            if not who or who[0][0] != 'admin':
                return False, "Only administrators can close a month"
            if self.is_month_closed(month):
                return False, "This month is already closed"
            self.db_manager.execute_write(
                "INSERT INTO closed_months (month, closed_by) VALUES (?, ?)", (month, username))
            self.logger.info(f"Month {month} closed by {username}")
            return True, f"Month {month} closed; numbering advanced"
        except Exception as e:
            self.logger.error(f"Error closing month: {str(e)}")
            return False, f"Error closing month: {str(e)}"

    def get_active_numbering_month(self) -> str:
        """Public read of the current active numbering month."""
        conn = sqlite3.connect(self.db_manager.db_path)
        try:
            return self._active_month(conn.cursor())
        finally:
            conn.close()

    # ---- Owned-block reservation (Phase 2) -----------------------------

    def reserve_block(self, username, count):
        """Allocate the next `count` sequential numbers to `username` as
        'available', in one transaction. count clamped to [1, 100]."""
        try:
            count = int(count)
        except (TypeError, ValueError):
            return False, [], "Invalid count"
        if count < 1 or count > 100:
            return False, [], "Count must be between 1 and 100"
        conn = sqlite3.connect(self.db_manager.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            allocated = []
            for _ in range(count):
                report_number, serial_number = self._generate_next_numbers(cursor)
                cursor.execute(
                    "INSERT INTO reserved_numbers (report_number, serial_number, owned_by, status) "
                    "VALUES (?, ?, ?, 'available')", (report_number, serial_number, username))
                allocated.append(report_number)
            conn.commit()
            self.logger.info(f"Reserved block of {count} numbers for {username}")
            return True, allocated, f"Reserved {count} numbers"
        except Exception as e:
            conn.rollback()
            self.logger.error(f"reserve_block error: {e}")
            return False, [], f"Error: {e}"
        finally:
            conn.close()

    def get_available_numbers(self, username):
        """This user's 'available' numbers, ascending."""
        rows = self.db_manager.execute_with_retry(
            "SELECT id, report_number, serial_number, reserved_at, transferred_from "
            "FROM reserved_numbers WHERE owned_by = ? AND status = 'available' "
            "ORDER BY serial_number", (username,))
        return [{'id': r[0], 'report_number': r[1], 'serial_number': r[2],
                 'reserved_at': r[3], 'transferred_from': r[4]} for r in (rows or [])]

    def get_available_count(self, username):
        r = self.db_manager.execute_with_retry(
            "SELECT COUNT(*) FROM reserved_numbers WHERE owned_by = ? AND status = 'available'", (username,))
        return r[0][0] if r else 0

    def consume_next_available(self, username, report_id):
        """Atomically flip the user's lowest 'available' number to 'used',
        linking used_by_report_id=report_id. Called by create_report as a
        separate, single-statement atomic update immediately after the
        report insert — there is no shared transaction (db_manager
        auto-commits per statement)."""
        n = self.db_manager.execute_write(
            "UPDATE reserved_numbers SET status='used', used_by_report_id=? "
            "WHERE id = (SELECT id FROM reserved_numbers WHERE owned_by=? AND status='available' "
            "ORDER BY serial_number LIMIT 1)", (report_id, username))
        if n != 1:
            return False, None, "You have no reserved numbers available"
        r = self.db_manager.execute_with_retry(
            "SELECT report_number FROM reserved_numbers WHERE used_by_report_id=? ORDER BY id DESC LIMIT 1",
            (report_id,))
        return True, (r[0][0] if r else None), "ok"

    def transfer_numbers(self, from_user, to_user, report_numbers):
        """Reassign owned_by for the given 'available' numbers (must currently
        be owned by from_user). to_user must be an active user."""
        if not report_numbers:
            return False, "No numbers selected"
        tgt = self.db_manager.execute_with_retry(
            "SELECT is_active FROM users WHERE username = ?", (to_user,))
        if not tgt or not tgt[0][0]:
            return False, "Recipient must be an active user"
        moved = 0
        for rn in report_numbers:
            n = self.db_manager.execute_write(
                "UPDATE reserved_numbers SET owned_by=?, transferred_from=? "
                "WHERE report_number=? AND owned_by=? AND status='available'",
                (to_user, from_user, rn, from_user))
            moved += n
        if moved == 0:
            return False, "No transferable numbers (must be yours and unused)"
        return True, f"Transferred {moved} number(s) to {to_user}"

