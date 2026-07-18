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


def _is_username(value) -> bool:
    """A username must be a non-empty string. Anything else (list/dict/None/int)
    would reach sqlite as an unsupported bind type and raise ProgrammingError
    out of the service, so it is rejected at the boundary instead."""
    return isinstance(value, str) and value.strip() != ""


class ReportNumberService:
    """
    Thread-safe service for managing report numbers and serial numbers.

    Key Features:
    - Database-level locking for atomicity
    - Owned-block reservation (reserve_block / consume_next_available)
    - Calendar-driven monthly numbering (automatic month rollover)
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
        # Numbering month = the current calendar month. Injectable so tests can
        # simulate a month rollover.
        self._now = datetime.now

    def _generate_next_numbers(self, cursor) -> Tuple[str, int]:
        """
        Generate the next sequential report number and serial number.

        Report Number Format: YYYY/MM/NNN (resets each month)
        Serial Number: Global incrementing counter (never resets)

        The month prefix is the current calendar month; it rolls over
        automatically when the month changes (no grace period, no manual close).

        Args:
            cursor: Database cursor (must be in transaction)

        Returns:
            Tuple of (report_number, serial_number)
        """
        # Month prefix is the current calendar month (auto rollover).
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

    # ---- Calendar-driven numbering month -------------------------------
    # The numbering month IS the current calendar month. It rolls over
    # automatically when the month changes — no grace period, no manual admin
    # close. Already-reserved numbers keep the month they were reserved in (the
    # number is fixed at reservation) and stay owned by their assignee until
    # acted on, so a number reserved in June still works in July.
    def _active_month(self, cursor=None) -> str:
        now = self._now()
        return f"{now.year}/{now.month:02d}"

    def get_active_numbering_month(self) -> str:
        """The current active numbering month (the calendar month)."""
        return self._active_month()

    # ---- Owned-block reservation (Phase 2) -----------------------------

    def reserve_block(self, username, count):
        """Allocate the next `count` sequential numbers to `username` as
        'available', in one transaction. count clamped to [1, 100]."""
        if not _is_username(username):
            return False, [], "Invalid user"
        try:
            count = int(count)
        except (TypeError, ValueError, OverflowError):  # OverflowError: float('inf')
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
        if not _is_username(username):
            return []
        rows = self.db_manager.execute_with_retry(
            "SELECT id, report_number, serial_number, reserved_at, transferred_from "
            "FROM reserved_numbers WHERE owned_by = ? AND status = 'available' "
            "ORDER BY serial_number", (username,))
        return [{'id': r[0], 'report_number': r[1], 'serial_number': r[2],
                 'reserved_at': r[3], 'transferred_from': r[4]} for r in (rows or [])]

    def get_available_count(self, username):
        if not _is_username(username):
            return 0
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
        if not _is_username(from_user) or not _is_username(to_user):
            return False, "Invalid user"
        if not report_numbers or not isinstance(report_numbers, (list, tuple, set)):
            return False, "No numbers selected"
        tgt = self.db_manager.execute_with_retry(
            "SELECT is_active FROM users WHERE username = ?", (to_user,))
        if not tgt or not tgt[0][0]:
            return False, "Recipient must be an active user"
        moved = 0
        for rn in report_numbers:
            if not isinstance(rn, str):
                continue  # unbindable type; a real report number is always a string
            n = self.db_manager.execute_write(
                "UPDATE reserved_numbers SET owned_by=?, transferred_from=? "
                "WHERE report_number=? AND owned_by=? AND status='available'",
                (to_user, from_user, rn, from_user))
            moved += n
        if moved == 0:
            return False, "No transferable numbers (must be yours and unused)"
        return True, f"Transferred {moved} number(s) to {to_user}"

