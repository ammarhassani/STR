"""
Report Number Service - Concurrent-Safe Number Generation
Handles report number and serial number generation with:
- 5-minute reservation system to prevent duplicates
- Automatic expiry cleanup
- Gap detection for deleted reports
- Reuse of deleted numbers with notifications

This service is designed to handle concurrent access from multiple users safely.
"""

import sqlite3
from typing import Tuple, Optional, Dict, List
from datetime import datetime, timedelta
import threading
import time


class ReportNumberService:
    """
    Thread-safe service for managing report numbers and serial numbers.

    Key Features:
    - Database-level locking for atomicity
    - 5-minute reservation system
    - Automatic cleanup of expired reservations
    - Gap detection and reuse of deleted report numbers
    - Background cleanup task
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
        self.cleanup_thread = None
        self.cleanup_running = False

        # Start background cleanup task
        self.start_cleanup_task()

    def reserve_next_numbers(self, username: str, reservation_minutes: int = 5) -> Tuple[bool, Optional[Dict], str]:
        """
        Reserve the next available report number and serial number for a user.
        Uses database transactions to ensure thread-safety.

        This is called when a user opens the "Add Report" dialog.
        The reservation expires after N minutes if not used.

        Args:
            username: Username requesting the reservation
            reservation_minutes: Minutes to hold the reservation (default: 5)

        Returns:
            Tuple of (success, reservation_dict, message)
            reservation_dict contains: {report_number, serial_number, expires_at, has_gap, gap_info}
        """
        try:
            # Use immediate transaction to get exclusive lock
            # Set longer timeout for user operations (10 seconds)
            conn = sqlite3.connect(self.db_manager.db_path, timeout=10.0)
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            try:
                # Note: Cleanup is handled by background thread, not here
                # This prevents deadlock with concurrent cleanup operations

                # Step 1: Check system-wide concurrent reservation limit
                cursor.execute("""
                    SELECT COUNT(*) FROM report_number_reservations
                    WHERE is_used = 0 AND expires_at > datetime('now')
                """)
                current_reservations = cursor.fetchone()[0]

                # Get max concurrent reservations from settings (default: unlimited)
                cursor.execute("""
                    SELECT setting_value FROM system_settings
                    WHERE setting_key = 'max_concurrent_reservations'
                """)
                max_concurrent = cursor.fetchone()
                max_concurrent = int(max_concurrent[0]) if max_concurrent else 999

                # Collect info for logging (don't log during transaction!)
                debug_info_concurrent = f"Reservation check: {current_reservations}/{max_concurrent} concurrent reservations"

                if current_reservations >= max_concurrent:
                    conn.rollback()
                    # Log AFTER rollback using print to avoid nested DB writes
                    print(f"[WARNING] Reservation denied for {username}: Maximum concurrent reservations ({max_concurrent}) reached")
                    return False, None, f"Maximum concurrent reservations ({max_concurrent}) reached. Please wait for others to complete their reports."

                # Step 2: Check per-user reservation limit
                cursor.execute("""
                    SELECT COUNT(*) FROM report_number_reservations
                    WHERE reserved_by = ? AND is_used = 0 AND expires_at > datetime('now')
                """, (username,))
                user_reservations = cursor.fetchone()[0]

                # Get max per-user reservations from settings (default: 1)
                cursor.execute("""
                    SELECT setting_value FROM system_settings
                    WHERE setting_key = 'max_reservations_per_user'
                """)
                max_per_user = cursor.fetchone()
                max_per_user = int(max_per_user[0]) if max_per_user else 1

                # Collect info for logging (don't log during transaction!)
                debug_info_user = f"User '{username}' has {user_reservations}/{max_per_user} active reservations"

                if user_reservations >= max_per_user:
                    conn.rollback()
                    # Log AFTER rollback using print to avoid nested DB writes
                    print(f"[WARNING] Reservation denied for {username}: Already has {user_reservations} active reservation(s), max allowed: {max_per_user}")
                    return False, None, f"You already have {user_reservations} active reservation(s). Maximum allowed: {max_per_user}. Please complete or cancel your existing reservation first."

                # Step 3: Check for gaps (deleted report numbers that can be reused)
                gap_info = self._find_report_number_gap(cursor)

                # Step 3: Generate the next report number
                if gap_info:
                    # Reuse a deleted report number
                    report_number = gap_info['report_number']
                    serial_number = gap_info['serial_number']
                    has_gap = True
                else:
                    # Generate new sequential numbers
                    report_number, serial_number = self._generate_next_numbers(cursor)
                    has_gap = False

                # Step 4: Check if this number is already reserved
                cursor.execute("""
                    SELECT reservation_id, reserved_by, expires_at
                    FROM report_number_reservations
                    WHERE report_number = ? AND is_used = 0
                """, (report_number,))

                existing = cursor.fetchone()
                if existing:
                    # Number is already reserved
                    reserved_by, expires_at = existing[1], existing[2]
                    if reserved_by == username:
                        # Same user, extend the reservation
                        new_expires_at = (datetime.now() + timedelta(minutes=reservation_minutes)).isoformat()
                        cursor.execute("""
                            UPDATE report_number_reservations
                            SET expires_at = ?
                            WHERE reservation_id = ?
                        """, (new_expires_at, existing[0]))
                        conn.commit()

                        return True, {
                            'report_number': report_number,
                            'serial_number': serial_number,
                            'expires_at': new_expires_at,
                            'has_gap': has_gap,
                            'gap_info': gap_info
                        }, "Reservation extended successfully."
                    else:
                        # Reserved by someone else
                        conn.rollback()
                        return False, None, f"This report number is currently reserved by {reserved_by}. Please try again."

                # Step 5: Create new reservation
                expires_at = (datetime.now() + timedelta(minutes=reservation_minutes)).isoformat()

                cursor.execute("""
                    INSERT INTO report_number_reservations
                    (report_number, serial_number, reserved_by, reserved_at, expires_at, is_used)
                    VALUES (?, ?, ?, datetime('now'), ?, 0)
                """, (report_number, serial_number, username, expires_at))

                conn.commit()

                # Log AFTER commit using print to avoid nested DB writes
                print(f"[INFO] {debug_info_concurrent}")
                print(f"[INFO] {debug_info_user}")
                print(f"[INFO] Reserved report number {report_number} (SN: {serial_number}) for {username}")

                return True, {
                    'report_number': report_number,
                    'serial_number': serial_number,
                    'expires_at': expires_at,
                    'has_gap': has_gap,
                    'gap_info': gap_info
                }, "Numbers reserved successfully."

            except Exception as e:
                conn.rollback()
                raise e

            finally:
                conn.close()

        except Exception as e:
            self.logger.error(f"Error reserving report numbers: {str(e)}")
            return False, None, f"Error reserving numbers: {str(e)}"

    def mark_reservation_used(self, report_number: str, username: str) -> Tuple[bool, str]:
        """
        Mark a reservation as used after the report is successfully saved.

        Args:
            report_number: Report number that was used
            username: Username who used the reservation

        Returns:
            Tuple of (success, message)
        """
        try:
            query = """
                UPDATE report_number_reservations
                SET is_used = 1
                WHERE report_number = ? AND reserved_by = ? AND is_used = 0
            """
            self.db_manager.execute_with_retry(query, (report_number, username))

            self.logger.info(f"Marked reservation for {report_number} as used by {username}")
            return True, "Reservation marked as used."

        except Exception as e:
            self.logger.error(f"Error marking reservation as used: {str(e)}")
            return False, f"Error: {str(e)}"

    def cancel_reservation(self, report_number: str, username: str) -> Tuple[bool, str]:
        """
        Cancel a reservation (user closed dialog without saving).
        Adds the cancelled number to gap queue if gap reuse is enabled.

        Args:
            report_number: Report number to release
            username: Username who held the reservation

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get reservation details before deleting
            query = """
                SELECT serial_number FROM report_number_reservations
                WHERE report_number = ? AND reserved_by = ? AND is_used = 0
            """
            result = self.db_manager.execute_with_retry(query, (report_number, username))

            if not result:
                return False, "Reservation not found or already used"

            serial_number = result[0][0]

            # Delete the reservation
            query = """
                DELETE FROM report_number_reservations
                WHERE report_number = ? AND reserved_by = ? AND is_used = 0
            """
            self.db_manager.execute_with_retry(query, (report_number, username))

            # Add to gap queue if enabled
            self._add_to_gap_queue(report_number, serial_number, 'cancelled', username)

            print(f"[INFO] Cancelled reservation for {report_number} by {username}")
            return True, "Reservation cancelled."

        except Exception as e:
            print(f"[ERROR] Error cancelling reservation: {str(e)}")
            return False, f"Error: {str(e)}"

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
        # Get grace period from system config
        grace_days = self._get_month_grace_period(cursor)

        # Get month prefix with grace period applied
        prefix = self.get_month_with_grace_period(grace_days) + "/"

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

        # Next number is max of both + 1 (ensures no conflicts!)
        next_num = max(max_existing_num, max_reserved_num) + 1
        report_number = f"{prefix}{next_num:03d}"

        # Get next serial number (global counter)
        cursor.execute("SELECT COALESCE(MAX(sn), 0) FROM reports")
        max_sn = cursor.fetchone()[0]

        # Also check reserved serial numbers
        cursor.execute("SELECT COALESCE(MAX(serial_number), 0) FROM report_number_reservations WHERE is_used = 0")
        max_reserved_sn = cursor.fetchone()[0]

        serial_number = max(max_sn, max_reserved_sn) + 1

        return report_number, serial_number

    def _find_report_number_gap(self, cursor) -> Optional[Dict]:
        """
        Find the first gap in report numbers caused by deleted reports.

        A gap exists when a report was deleted, creating a missing number in the sequence.
        Example: 2025/11/001, 2025/11/002 (deleted), 2025/11/003 → Gap is 2025/11/002

        Args:
            cursor: Database cursor (must be in transaction)

        Returns:
            Dictionary with gap info or None if no gaps exist
            {report_number, serial_number, deleted_at, deleted_by}
        """
        # Find deleted reports that could be reused
        # We only reuse from the current month to keep numbering logical
        now = datetime.now()
        year = now.year
        month = f"{now.month:02d}"
        prefix = f"{year}/{month}/"

        cursor.execute("""
            SELECT report_number, sn, updated_at, updated_by
            FROM reports
            WHERE is_deleted = 1
              AND report_number LIKE ?
            ORDER BY report_number
            LIMIT 1
        """, (f"{prefix}%",))

        gap = cursor.fetchone()

        if gap:
            return {
                'report_number': gap[0],
                'serial_number': gap[1],
                'deleted_at': gap[2],
                'deleted_by': gap[3],
                'message': f"Gap detected: Report {gap[0]} was deleted and is being reused."
            }

        return None

    def get_gap_notification(self, username: str) -> Optional[str]:
        """
        Get a notification message if there are gaps in the report numbering.
        This is shown to users when adding reports.

        Args:
            username: Username to check for

        Returns:
            Notification message or None
        """
        try:
            # Find all gaps in current month
            now = datetime.now()
            prefix = f"{now.year}/{now.month:02d}/"

            query = """
                SELECT report_number, updated_at, updated_by
                FROM reports
                WHERE is_deleted = 1
                  AND report_number LIKE ?
                ORDER BY report_number
            """
            results = self.db_manager.execute_with_retry(query, (f"{prefix}%",))

            if results:
                gaps = [row[0] for row in results]

                # Get the current sequence number (next number that will be assigned)
                query = """
                    SELECT MAX(report_number)
                    FROM reports
                    WHERE is_deleted = 0 AND report_number LIKE ?
                """
                result = self.db_manager.execute_with_retry(query, (f"{prefix}%",))
                current_max = result[0][0] if result and result[0][0] else f"{prefix}000"

                if len(gaps) == 1:
                    return f"⚠️ Gap Notice: Report {gaps[0]} was deleted. Current sequence: {current_max}"
                else:
                    gap_list = ", ".join(gaps[:3])
                    if len(gaps) > 3:
                        gap_list += f", and {len(gaps) - 3} more"
                    return f"⚠️ Gap Notice: {len(gaps)} reports deleted ({gap_list}). Current sequence: {current_max}"

            return None

        except Exception as e:
            self.logger.error(f"Error getting gap notification: {str(e)}")
            return None

    def _cleanup_expired_reservations(self, cursor):
        """
        Remove expired reservations from the database.
        This runs automatically as part of the reservation process.

        Args:
            cursor: Database cursor (must be in transaction)
        """
        cursor.execute("""
            DELETE FROM report_number_reservations
            WHERE is_used = 0
              AND expires_at < datetime('now')
        """)

        deleted_count = cursor.rowcount
        # Don't log here - we're inside a transaction!
        # Logging will be done by caller after commit
        return deleted_count

    def cleanup_expired_reservations_public(self):
        """
        Public method to manually trigger cleanup of expired reservations.
        Can be called from a background task or admin function.
        Uses DEFERRED transaction to avoid blocking user operations.
        """
        deleted_count = 0
        try:
            # Use DEFERRED transaction and short timeout to avoid blocking users
            conn = sqlite3.connect(self.db_manager.db_path, timeout=0.5)
            # Use DEFERRED instead of IMMEDIATE to be less aggressive
            conn.execute("BEGIN DEFERRED")
            cursor = conn.cursor()

            try:
                deleted_count = self._cleanup_expired_reservations(cursor)
                conn.commit()
                # Log AFTER commit, not during transaction
                if deleted_count > 0:
                    # Use print instead of logger to avoid nested database writes
                    print(f"[INFO] Cleaned up {deleted_count} expired reservation(s)")
            except sqlite3.OperationalError as e:
                # Database locked - skip this cleanup cycle, will try again next time
                conn.rollback()
                # Don't log as error - this is expected during user operations
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

        except sqlite3.OperationalError:
            # Database locked - skip silently, will retry in next cycle
            pass
        except Exception as e:
            # Use print instead of logger to avoid nested database writes
            print(f"[ERROR] Error in public cleanup: {str(e)}")

    def start_cleanup_task(self):
        """
        Start background task that cleans up expired reservations every minute.
        This ensures stale reservations don't accumulate.
        """
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return  # Already running

        self.cleanup_running = True

        def cleanup_loop():
            while self.cleanup_running:
                try:
                    self.cleanup_expired_reservations_public()
                except Exception as e:
                    self.logger.error(f"Error in cleanup loop: {str(e)}")

                # Sleep for 2 minutes to reduce contention with user operations
                time.sleep(120)

        self.cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True, name="ReservationCleanup")
        self.cleanup_thread.start()
        self.logger.info("Started report number reservation cleanup task")

    def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        self.cleanup_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=2)
            self.logger.info("Stopped report number reservation cleanup task")

    def get_active_reservations(self) -> List[Dict]:
        """
        Get all active (non-expired, non-used) reservations.
        Useful for admin monitoring.

        Returns:
            List of reservation dictionaries
        """
        try:
            query = """
                SELECT reservation_id, report_number, serial_number, reserved_by,
                       reserved_at, expires_at
                FROM report_number_reservations
                WHERE is_used = 0
                  AND expires_at >= datetime('now')
                ORDER BY reserved_at DESC
            """
            results = self.db_manager.execute_with_retry(query)

            reservations = []
            for row in results:
                reservations.append({
                    'reservation_id': row[0],
                    'report_number': row[1],
                    'serial_number': row[2],
                    'reserved_by': row[3],
                    'reserved_at': row[4],
                    'expires_at': row[5],
                })

            return reservations

        except Exception as e:
            self.logger.error(f"Error getting active reservations: {str(e)}")
            return []

    def get_reservation_stats(self) -> Dict:
        """
        Get statistics about reservations.
        Useful for monitoring system health.

        Returns:
            Dictionary with statistics
        """
        try:
            stats = {}

            # Active reservations
            query = "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 0 AND expires_at >= datetime('now')"
            result = self.db_manager.execute_with_retry(query)
            stats['active_reservations'] = result[0][0] if result else 0

            # Expired reservations (need cleanup)
            query = "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 0 AND expires_at < datetime('now')"
            result = self.db_manager.execute_with_retry(query)
            stats['expired_reservations'] = result[0][0] if result else 0

            # Used reservations (historical)
            query = "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 1"
            result = self.db_manager.execute_with_retry(query)
            stats['used_reservations'] = result[0][0] if result else 0

            # Total gaps (deleted reports in current month)
            now = datetime.now()
            prefix = f"{now.year}/{now.month:02d}/"
            query = "SELECT COUNT(*) FROM reports WHERE is_deleted = 1 AND report_number LIKE ?"
            result = self.db_manager.execute_with_retry(query, (f"{prefix}%",))
            stats['current_month_gaps'] = result[0][0] if result else 0

            return stats

        except Exception as e:
            self.logger.error(f"Error getting reservation stats: {str(e)}")
            return {}

    def reserve_batch_numbers(self, count: int = 10, reservation_minutes: int = 5) -> Tuple[bool, List[Dict], str]:
        """
        Reserve a batch of report numbers at once for faster multi-user access.
        This pre-reserves numbers that can be quickly assigned to users.

        Args:
            count: Number of report numbers to reserve in batch
            reservation_minutes: Minutes to hold each reservation

        Returns:
            Tuple of (success, list of reservation dicts, message)
        """
        try:
            # Use timeout to prevent deadlocks
            conn = sqlite3.connect(self.db_manager.db_path, timeout=5.0)
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            try:
                # Note: Cleanup is handled by background thread, not here

                reservations = []
                for i in range(count):
                    # Check for gaps first
                    gap_info = self._find_report_number_gap(cursor)

                    if gap_info:
                        report_number = gap_info['report_number']
                        serial_number = gap_info['serial_number']
                        has_gap = True
                    else:
                        report_number, serial_number = self._generate_next_numbers(cursor)
                        has_gap = False

                    # Create reservation with generic batch username
                    expires_at = (datetime.now() + timedelta(minutes=reservation_minutes)).isoformat()
                    cursor.execute("""
                        INSERT INTO report_number_reservations
                        (report_number, serial_number, reserved_by, expires_at, is_used)
                        VALUES (?, ?, ?, ?, 0)
                    """, (report_number, serial_number, f"BATCH_POOL", expires_at))

                    reservations.append({
                        'report_number': report_number,
                        'serial_number': serial_number,
                        'expires_at': expires_at,
                        'has_gap': has_gap
                    })

                conn.commit()
                self.logger.info(f"Reserved batch of {count} report numbers")
                return True, reservations, f"Reserved {count} numbers successfully"

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

        except Exception as e:
            error_msg = f"Error reserving batch numbers: {str(e)}"
            self.logger.error(error_msg)
            return False, [], error_msg

    def get_next_from_pool(self, username: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Get next available number from the pre-reserved pool.
        Much faster than individual reservation for concurrent users.

        Args:
            username: Username claiming the number

        Returns:
            Tuple of (success, reservation_dict, message)
        """
        try:
            # Use timeout to prevent deadlocks
            conn = sqlite3.connect(self.db_manager.db_path, timeout=5.0)
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            try:
                # Find an available number from the pool
                cursor.execute("""
                    SELECT report_number, serial_number, expires_at
                    FROM report_number_reservations
                    WHERE reserved_by = 'BATCH_POOL'
                      AND is_used = 0
                      AND expires_at >= datetime('now')
                    ORDER BY serial_number ASC
                    LIMIT 1
                """)

                result = cursor.fetchone()

                if not result:
                    # Pool is empty, fall back to individual reservation
                    conn.rollback()
                    conn.close()
                    return self.reserve_next_numbers(username)

                report_number, serial_number, expires_at = result

                # Claim this number for the user
                cursor.execute("""
                    UPDATE report_number_reservations
                    SET reserved_by = ?, reserved_at = datetime('now')
                    WHERE report_number = ? AND reserved_by = 'BATCH_POOL'
                """, (username, report_number))

                conn.commit()

                return True, {
                    'report_number': report_number,
                    'serial_number': serial_number,
                    'expires_at': expires_at,
                    'has_gap': False
                }, "Number claimed from pool"

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

        except Exception as e:
            error_msg = f"Error getting number from pool: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def get_pool_size(self) -> int:
        """Get current size of the batch pool."""
        try:
            query = """
                SELECT COUNT(*)
                FROM report_number_reservations
                WHERE reserved_by = 'BATCH_POOL'
                  AND is_used = 0
                  AND expires_at >= datetime('now')
            """
            result = self.db_manager.execute_with_retry(query)
            return result[0][0] if result else 0
        except:
            return 0

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

    # Gap Queue Management Methods

    def _add_to_gap_queue(self, report_number: str, serial_number: int, gap_type: str, created_by: str = None):
        """
        Add a cancelled reservation to the gap queue for reuse.

        Args:
            report_number: Report number that became available
            serial_number: Serial number
            gap_type: Type of gap ('cancelled', 'deleted', 'error')
            created_by: Username who created the gap
        """
        try:
            # Check if gap reuse is enabled
            query = """
                SELECT setting_value FROM system_settings
                WHERE setting_key = 'enable_gap_reuse'
            """
            result = self.db_manager.execute_with_retry(query)
            if not result or result[0][0] != '1':
                return  # Gap reuse disabled

            # Add to gap queue
            query = """
                INSERT OR IGNORE INTO gap_queue
                (report_number, serial_number, gap_type, created_by, reason, status, priority)
                VALUES (?, ?, ?, ?, ?, 'available', 0)
            """
            reason = f"Reservation cancelled by {created_by}" if gap_type == 'cancelled' else gap_type
            self.db_manager.execute_with_retry(
                query,
                (report_number, serial_number, gap_type, created_by, reason)
            )

            print(f"[INFO] Added {report_number} to gap queue ({gap_type})")

            # Check for merge opportunities
            self._check_gap_merge()

        except Exception as e:
            print(f"[ERROR] Error adding to gap queue: {str(e)}")

    def get_next_gap(self) -> Optional[Dict]:
        """
        Get the next available gap from the queue.
        Returns highest priority gap first.

        Returns:
            Dictionary with gap info or None if no gaps available
        """
        try:
            query = """
                SELECT gap_id, report_number, serial_number, gap_type, created_at
                FROM gap_queue
                WHERE status = 'available'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """
            result = self.db_manager.execute_with_retry(query)

            if result:
                return {
                    'gap_id': result[0][0],
                    'report_number': result[0][1],
                    'serial_number': result[0][2],
                    'gap_type': result[0][3],
                    'created_at': result[0][4]
                }

            return None

        except Exception as e:
            print(f"[ERROR] Error getting next gap: {str(e)}")
            return None

    def claim_gap(self, gap_id: int) -> Tuple[bool, str]:
        """
        Claim a gap from the queue (mark as used).

        Args:
            gap_id: Gap queue ID

        Returns:
            Tuple of (success, message)
        """
        try:
            query = """
                UPDATE gap_queue
                SET status = 'used'
                WHERE gap_id = ? AND status = 'available'
            """
            self.db_manager.execute_with_retry(query, (gap_id,))
            return True, "Gap claimed successfully"

        except Exception as e:
            return False, f"Error claiming gap: {str(e)}"

    def _check_gap_merge(self):
        """
        Check for consecutive gaps and trigger merge alert if threshold exceeded.
        """
        try:
            # Get merge threshold
            query = """
                SELECT setting_value FROM system_settings
                WHERE setting_key = 'gap_merge_threshold'
            """
            result = self.db_manager.execute_with_retry(query)
            threshold = int(result[0][0]) if result else 3

            # Count consecutive gaps
            query = """
                SELECT COUNT(*) FROM gap_queue
                WHERE status = 'available'
            """
            result = self.db_manager.execute_with_retry(query)
            gap_count = result[0][0] if result else 0

            if gap_count >= threshold:
                print(f"[WARNING] {gap_count} gaps in queue - merge recommended (threshold: {threshold})")

        except Exception as e:
            print(f"[ERROR] Error checking gap merge: {str(e)}")

    def get_gap_queue_stats(self) -> Dict:
        """
        Get statistics about the gap queue.

        Returns:
            Dictionary with gap queue statistics
        """
        try:
            stats = {}

            # Available gaps
            query = "SELECT COUNT(*) FROM gap_queue WHERE status = 'available'"
            result = self.db_manager.execute_with_retry(query)
            stats['available_gaps'] = result[0][0] if result else 0

            # Used gaps
            query = "SELECT COUNT(*) FROM gap_queue WHERE status = 'used'"
            result = self.db_manager.execute_with_retry(query)
            stats['used_gaps'] = result[0][0] if result else 0

            # Gaps by type
            query = "SELECT gap_type, COUNT(*) FROM gap_queue WHERE status = 'available' GROUP BY gap_type"
            result = self.db_manager.execute_with_retry(query)
            stats['gaps_by_type'] = {row[0]: row[1] for row in result} if result else {}

            return stats

        except Exception as e:
            print(f"[ERROR] Error getting gap stats: {str(e)}")
            return {}

    def cleanup_gap_queue(self) -> int:
        """
        Clean up old used gaps from the queue.

        Returns:
            Number of gaps cleaned up
        """
        try:
            query = """
                DELETE FROM gap_queue
                WHERE status = 'used'
                AND datetime(created_at) < datetime('now', '-30 days')
            """
            self.db_manager.execute_with_retry(query)

            # Get count of deleted rows
            result = self.db_manager.execute_with_retry("SELECT changes()")
            cleaned = result[0][0] if result else 0

            if cleaned > 0:
                print(f"[INFO] Cleaned up {cleaned} old gaps from queue")

            return cleaned

        except Exception as e:
            print(f"[ERROR] Error cleaning gap queue: {str(e)}")
            return 0

    def __del__(self):
        """Cleanup when service is destroyed."""
        self.stop_cleanup_task()
