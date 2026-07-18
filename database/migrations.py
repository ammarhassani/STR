"""
Database Migrations
Handles schema updates for existing databases.
"""

import sqlite3
from typing import Tuple


def migrate_database(db_path: str) -> Tuple[bool, str]:
    """
    Run all necessary migrations on the database.

    Args:
        db_path: Path to database file

    Returns:
        Tuple of (success, message)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        messages = []

        # Migration 0: Ensure system_config table exists (critical for all dropdown functionality)
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='system_config'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE system_config (
                    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    config_type TEXT CHECK(config_type IN ('dropdown', 'setting', 'column', 'path')),
                    config_category TEXT,
                    display_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT,
                    updated_by TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_system_config_key ON system_config(config_key)
            """)
            cursor.execute("""
                CREATE INDEX idx_system_config_type ON system_config(config_type)
            """)
            cursor.execute("""
                CREATE INDEX idx_system_config_category ON system_config(config_category)
            """)
            conn.commit()
            messages.append("Created system_config table")

        # Migration 1: Add theme_preference column to users table
        try:
            cursor.execute("SELECT theme_preference FROM users LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            # CHECK constraints in ALTER TABLE ADD COLUMN require SQLite 3.25.0+
            # Validation is handled at application level
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN theme_preference TEXT DEFAULT 'light'
            """)
            conn.commit()
            messages.append("Added theme_preference column to users table")

        # Migration 2: Create report_versions table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='report_versions'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE report_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    change_summary TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (report_id) REFERENCES reports(report_id)
                )
            """)
            conn.commit()
            messages.append("Created report_versions table")

        # Migration 3: Create report_approvals table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='report_approvals'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE report_approvals (
                    approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    version_id INTEGER,
                    approval_status TEXT CHECK(approval_status IN ('pending', 'approved', 'rejected', 'rework')) DEFAULT 'pending',
                    approver_id INTEGER,
                    approval_comment TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at TEXT DEFAULT (datetime('now')),
                    reviewed_at TEXT,
                    FOREIGN KEY (report_id) REFERENCES reports(report_id),
                    FOREIGN KEY (approver_id) REFERENCES users(user_id),
                    FOREIGN KEY (version_id) REFERENCES report_versions(version_id)
                )
            """)
            conn.commit()
            messages.append("Created report_approvals table")

        # Migration 4: Create notifications table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='notifications'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT CHECK(notification_type IN ('info', 'warning', 'approval_request', 'approval_result')),
                    related_report_id INTEGER,
                    is_read INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (related_report_id) REFERENCES reports(report_id)
                )
            """)
            conn.commit()
            messages.append("Created notifications table")

        # Migration 5: Add versioning columns to reports table
        try:
            cursor.execute("SELECT current_version FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN current_version INTEGER DEFAULT 1
            """)
            conn.commit()
            messages.append("Added current_version column to reports table")

        try:
            cursor.execute("SELECT approval_status FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            # Add approval_status column without CHECK constraint
            # (CHECK constraints in ALTER TABLE ADD COLUMN require SQLite 3.25.0+)
            # Validation is handled at application level
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN approval_status TEXT DEFAULT 'draft'
            """)
            conn.commit()
            messages.append("Added approval_status column to reports table")

        # Migration 6: Ensure system_logs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='system_logs'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE system_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    log_level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    function_name TEXT,
                    message TEXT NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    exception_type TEXT,
                    exception_message TEXT,
                    stack_trace TEXT,
                    extra_data TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
            """)
            conn.commit()
            messages.append("Created system_logs table")

        # Migration 7: Create report_number_reservations table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='report_number_reservations'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE report_number_reservations (
                    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_number TEXT NOT NULL,
                    serial_number INTEGER NOT NULL,
                    reserved_by TEXT NOT NULL,
                    reserved_at TEXT DEFAULT (datetime('now')),
                    expires_at TEXT NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    FOREIGN KEY (reserved_by) REFERENCES users(username)
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_reservations_expiry
                ON report_number_reservations(expires_at, is_used)
            """)
            cursor.execute("""
                CREATE INDEX idx_reservations_user
                ON report_number_reservations(reserved_by)
            """)
            conn.commit()
            messages.append("Created report_number_reservations table")

        # Migration 8: Create restore_log table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='restore_log'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE restore_log (
                    restore_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restore_number TEXT UNIQUE NOT NULL,
                    report_id INTEGER NOT NULL,
                    report_number TEXT NOT NULL,
                    serial_number INTEGER NOT NULL,
                    previous_state TEXT NOT NULL,
                    restored_by TEXT NOT NULL,
                    restored_at TEXT DEFAULT (datetime('now')),
                    restore_reason TEXT,
                    FOREIGN KEY (report_id) REFERENCES reports(report_id),
                    FOREIGN KEY (restored_by) REFERENCES users(username)
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_restore_log_report
                ON restore_log(report_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_restore_log_date
                ON restore_log(restored_at)
            """)
            conn.commit()
            messages.append("Created restore_log table")

        # Migration 9: Add new columns to reports table
        # Add legal_entity_owner as BOOLEAN (INTEGER in SQLite)
        try:
            cursor.execute("SELECT legal_entity_owner_checkbox FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN legal_entity_owner_checkbox INTEGER DEFAULT 0
            """)
            conn.commit()
            messages.append("Added legal_entity_owner_checkbox column to reports table")

        # Add acc_membership_checkbox
        try:
            cursor.execute("SELECT acc_membership_checkbox FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN acc_membership_checkbox INTEGER DEFAULT 0
            """)
            conn.commit()
            messages.append("Added acc_membership_checkbox column to reports table")

        # Add relationship field (auto-generated from acc_membership_checkbox)
        try:
            cursor.execute("SELECT relationship FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN relationship TEXT
            """)
            conn.commit()
            messages.append("Added relationship column to reports table")

        # Migration 10: Remove CHECK constraint from status column
        # SQLite doesn't support DROP COLUMN easily, so we mark it for application-level handling
        # We'll hide it in the UI and stop using it
        # Note: Actual column removal requires table recreation (handled in migration 11)

        # Migration 11: Add system settings for batch reservation and grace period
        cursor.execute("""
            INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, config_category, is_active)
            VALUES
                ('batch_pool_size', '20', 'setting', 'system', 1),
                ('reservation_expiry_minutes', '5', 'setting', 'system', 1),
                ('records_per_page', '50', 'setting', 'system', 1)
        """)
        # Check if any rows were inserted
        if cursor.rowcount > 0:
            conn.commit()
            messages.append("Added system settings for batch reservation and grace period")

        # Migration 12: Populate dropdown values in system_config (only if empty)
        # Check if dropdown values already exist
        cursor.execute("SELECT COUNT(*) FROM system_config WHERE config_type = 'dropdown'")
        dropdown_count = cursor.fetchone()[0]

        # Only populate if no dropdown values exist (first run)
        if dropdown_count == 0:
            # Populate all dropdown categories with default values
            dropdown_inserts = []

            # 1. Nationality (Fixed category)
            nationalities = [
                'Saudi Arabian', 'Emirati', 'Qatari', 'Bahraini', 'Kuwaiti', 'Omani',
                'Egyptian', 'Jordanian', 'Lebanese', 'Syrian', 'Iraqi', 'Palestinian',
                'Yemeni', 'Sudanese', 'Moroccan', 'Algerian', 'Tunisian', 'Libyan',
                'Pakistani', 'Indian', 'Bangladeshi', 'Filipino', 'Indonesian',
                'American', 'British', 'French', 'German', 'Other'
            ]
            for idx, nat in enumerate(nationalities, 1):
                dropdown_inserts.append(
                    f"('nationality_{nat.lower().replace(' ', '_')}', '{nat}', 'dropdown', 'nationality', {idx}, 1)"
                )

            # 2. Second Reason for Suspicion (Admin-manageable)
            second_reasons = [
                'Unusual transaction patterns',
                'Structuring to avoid reporting limits',
                'Suspicious cash deposits',
                'Transactions with high-risk countries',
                'Lack of economic justification',
                'Complex ownership structure',
                'Inconsistent business activity',
                'Rapid movement of funds',
                'Use of third parties',
                'Other suspicious indicators'
            ]
            for idx, reason in enumerate(second_reasons, 1):
                dropdown_inserts.append(
                    f"('second_reason_{idx}', '{reason}', 'dropdown', 'second_reason_for_suspicion', {idx}, 1)"
                )

            # 3. Type of Suspected Transaction (Admin-manageable)
            transaction_types = [
                'Cash deposit',
                'Cash withdrawal',
                'Wire transfer',
                'Check deposit',
                'Foreign exchange',
                'Investment transaction',
                'Loan transaction',
                'Trade finance',
                'Multiple transactions',
                'Other'
            ]
            for idx, ttype in enumerate(transaction_types, 1):
                dropdown_inserts.append(
                    f"('transaction_type_{idx}', '{ttype}', 'dropdown', 'type_of_suspected_transaction', {idx}, 1)"
                )

            # 4. Report Classification (Admin-manageable)
            classifications = [
                'Money Laundering',
                'Terrorist Financing',
                'Fraud',
                'Tax Evasion',
                'Corruption',
                'Sanctions Violation',
                'Other Financial Crime'
            ]
            for idx, cls in enumerate(classifications, 1):
                dropdown_inserts.append(
                    f"('classification_{idx}', '{cls}', 'dropdown', 'report_classification', {idx}, 1)"
                )

            # 5. Report Source (Fixed category)
            sources = [
                'Internal monitoring',
                'Customer due diligence',
                'Transaction monitoring',
                'External tip',
                'Law enforcement request',
                'Media report',
                'Other'
            ]
            for idx, source in enumerate(sources, 1):
                dropdown_inserts.append(
                    f"('report_source_{idx}', '{source}', 'dropdown', 'report_source', {idx}, 1)"
                )

            # 6. Reporting Entity (Fixed category)
            entities = [
                'Bank',
                'Exchange company',
                'Insurance company',
                'Securities firm',
                'Money service business',
                'Real estate',
                'Precious metals dealer',
                'Other financial institution'
            ]
            for idx, entity in enumerate(entities, 1):
                dropdown_inserts.append(
                    f"('reporting_entity_{idx}', '{entity}', 'dropdown', 'reporting_entity', {idx}, 1)"
                )

            # 7. FIU Feedback (Admin-manageable)
            feedbacks = [
                'Under investigation',
                'No action required',
                'Referred to law enforcement',
                'Request for additional information',
                'Case closed',
                'Ongoing monitoring',
                'Other'
            ]
            for idx, feedback in enumerate(feedbacks, 1):
                dropdown_inserts.append(
                    f"('fiu_feedback_{idx}', '{feedback}', 'dropdown', 'fiu_feedback', {idx}, 1)"
                )

            # 8. Gender (Fixed category - for completeness)
            genders = ['ذكر', 'أنثى']
            for idx, gender in enumerate(genders, 1):
                dropdown_inserts.append(
                    f"('gender_{idx}', '{gender}', 'dropdown', 'gender', {idx}, 1)"
                )

            # 9. ARB Staff (Fixed category - for completeness)
            arb_options = ['نعم', 'لا']
            for idx, arb in enumerate(arb_options, 1):
                dropdown_inserts.append(
                    f"('arb_staff_{idx}', '{arb}', 'dropdown', 'arb_staff', {idx}, 1)"
                )


            # Insert all dropdown values
            insert_query = f"""
                INSERT OR IGNORE INTO system_config
                (config_key, config_value, config_type, config_category, display_order, is_active)
                VALUES {', '.join(dropdown_inserts)}
            """
            cursor.execute(insert_query)
            conn.commit()
            messages.append(f"Populated {len(dropdown_inserts)} dropdown values across 9 categories")

        # Migration 13: Add id_type column for ID/CR distinction
        try:
            cursor.execute("SELECT id_type FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN id_type TEXT DEFAULT 'ID'
            """)
            conn.commit()
            messages.append("Added id_type column to reports table")

        # Migration 15: Populate default validation rules for ID/CR and Account/Membership fields
        import json

        # Check if validation rules are already set for id_cr
        cursor.execute("""
            SELECT validation_rules FROM column_settings
            WHERE column_name = 'id_cr'
        """)
        id_cr_rules = cursor.fetchone()

        if id_cr_rules is None or not id_cr_rules[0]:
            # Set default validation rules for ID/CR field
            id_cr_validation = json.dumps({
                "length": 10,
                "pattern": "^[0-9]{10}$",
                "saudi_starts_with": "1",
                "cr_starts_with": "7"
            })

            cursor.execute("""
                UPDATE column_settings
                SET validation_rules = ?, updated_at = datetime('now')
                WHERE column_name = 'id_cr'
            """, (id_cr_validation,))

            if cursor.rowcount > 0:
                conn.commit()
                messages.append("Added validation rules for ID/CR field")

        # Check if validation rules are already set for account_membership
        cursor.execute("""
            SELECT validation_rules FROM column_settings
            WHERE column_name = 'account_membership'
        """)
        account_rules = cursor.fetchone()

        if account_rules is None or not account_rules[0]:
            # Set default validation rules for Account/Membership field
            account_validation = json.dumps({
                "account_length": 21,
                "membership_length": 8
            })

            cursor.execute("""
                UPDATE column_settings
                SET validation_rules = ?, updated_at = datetime('now')
                WHERE column_name = 'account_membership'
            """, (account_validation,))

            if cursor.rowcount > 0:
                conn.commit()
                messages.append("Added validation rules for Account/Membership field")

        # Migration 16: Create migration_history tracking table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='migration_history'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE migration_history (
                    migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_number INTEGER UNIQUE NOT NULL,
                    migration_name TEXT NOT NULL,
                    applied_at TEXT DEFAULT (datetime('now')),
                    execution_time_ms INTEGER,
                    success INTEGER DEFAULT 1,
                    error_message TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_migration_history_number ON migration_history(migration_number)
            """)
            cursor.execute("""
                CREATE INDEX idx_migration_history_applied ON migration_history(applied_at)
            """)
            conn.commit()
            messages.append("Created migration_history tracking table")

        # Migration 17: Add missing performance indexes
        indexes_to_create = [
            ("idx_reports_approval_status", "reports", "approval_status"),
            ("idx_report_versions_report_id", "report_versions", "report_id"),
            ("idx_report_approvals_status", "report_approvals", "approval_status"),
            ("idx_report_approvals_approver_id", "report_approvals", "approver_id"),
            ("idx_notifications_user_read", "notifications", "user_id, is_read"),
            ("idx_change_history_record_id", "change_history", "record_id"),
            ("idx_status_history_to_status", "status_history", "to_status"),
            ("idx_report_approvals_report_version", "report_approvals", "report_id, version_id"),
            ("idx_report_versions_created_at", "report_versions", "created_at"),
            ("idx_notifications_created_at", "notifications", "created_at"),
            ("idx_report_number_reservations_number", "report_number_reservations", "report_number"),
            ("idx_report_approvals_requested_by", "report_approvals", "requested_by")
        ]

        created_indexes = []
        for index_name, table_name, columns in indexes_to_create:
            # Check if index already exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name=?
            """, (index_name,))

            if not cursor.fetchone():
                try:
                    cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({columns})")
                    created_indexes.append(index_name)
                except sqlite3.OperationalError as e:
                    # Table or column might not exist yet - skip
                    pass

        if created_indexes:
            conn.commit()
            messages.append(f"Created {len(created_indexes)} performance indexes")

        # Migration 18: Add reservation management settings
        # First, create system_settings table if it doesn't exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='system_settings'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE system_settings (
                    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    description TEXT,
                    category TEXT,
                    is_editable INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.commit()
            messages.append("Created system_settings table")

        # Insert reservation management settings
        cursor.execute("""
            SELECT COUNT(*) FROM system_settings
            WHERE setting_key IN ('max_concurrent_reservations', 'max_reservations_per_user')
        """)
        existing_settings = cursor.fetchone()[0]

        if existing_settings < 2:
            settings_to_add = [
                ('max_concurrent_reservations', '10', 'Maximum number of concurrent report number reservations allowed system-wide', 'Reservation Management'),
                ('max_reservations_per_user', '1', 'Maximum number of active reservations allowed per user', 'Reservation Management')
            ]

            for key, value, description, category in settings_to_add:
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings
                    (setting_key, setting_value, description, category, is_editable)
                    VALUES (?, ?, ?, ?, 1)
                """, (key, value, description, category))

            conn.commit()
            messages.append("Added reservation management settings (max: 10 concurrent, 1 per user)")

        # Migration 19: Create gap_queue table for managing cancelled reservation gaps
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='gap_queue'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE gap_queue (
                    gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_number TEXT UNIQUE NOT NULL,
                    serial_number INTEGER NOT NULL,
                    gap_type TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    created_by TEXT,
                    priority INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'available'
                )
            """)

            cursor.execute("""
                CREATE INDEX idx_gap_queue_status ON gap_queue(status)
            """)

            cursor.execute("""
                CREATE INDEX idx_gap_queue_priority ON gap_queue(priority DESC, created_at ASC)
            """)

            conn.commit()
            messages.append("Created gap_queue table for managing reservation gaps")

            # Add gap queue settings
            gap_settings = [
                ('enable_gap_reuse', '1', 'Enable automatic reuse of gaps from cancelled reservations', 'Gap Management'),
                ('gap_merge_threshold', '3', 'Number of consecutive gaps before triggering merge alert', 'Gap Management'),
                ('auto_cleanup_gaps', '1', 'Automatically clean up expired gaps', 'Gap Management')
            ]

            for key, value, description, category in gap_settings:
                cursor.execute("""
                    INSERT OR IGNORE INTO system_settings
                    (setting_key, setting_value, description, category, is_editable)
                    VALUES (?, ?, ?, ?, 1)
                """, (key, value, description, category))

            conn.commit()
            messages.append("Added gap management settings")

        # Migration 20: Remove gender CHECK constraint (encoding issues)
        # Check if constraint still exists by trying to insert an invalid value
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
            if cursor.fetchone():
                # SQLite doesn't allow dropping constraints, so we need to recreate the table
                # First, check if we need this migration by looking at table schema
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reports'")
                table_sql = cursor.fetchone()[0]

                if "CHECK(gender IN" in table_sql:
                    # Backup existing data
                    cursor.execute("SELECT COUNT(*) FROM reports")
                    report_count = cursor.fetchone()[0]

                    # Create temporary table without CHECK constraint
                    cursor.execute("""
                        CREATE TABLE reports_new AS SELECT * FROM reports
                    """)

                    # Drop old table
                    cursor.execute("DROP TABLE reports")

                    # Recreate table without CHECK constraint (get column list from old table)
                    cursor.execute("""
                        CREATE TABLE reports (
                            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sn INTEGER UNIQUE NOT NULL,
                            report_number TEXT UNIQUE NOT NULL,
                            report_date TEXT NOT NULL,
                            outgoing_letter_number TEXT,
                            reported_entity_name TEXT NOT NULL,
                            legal_entity_owner TEXT,
                            gender TEXT,
                            nationality TEXT,
                            id_cr TEXT,
                            account_membership TEXT,
                            branch_id TEXT,
                            cic TEXT,
                            first_reason_for_suspicion TEXT,
                            second_reason_for_suspicion TEXT,
                            type_of_suspected_transaction TEXT,
                            arb_staff TEXT,
                            total_transaction TEXT,
                            report_classification TEXT,
                            report_source TEXT,
                            reporting_entity TEXT,
                            reporter_initials TEXT,
                            sending_date TEXT,
                            original_copy_confirmation TEXT,
                            fiu_number TEXT,
                            fiu_letter_receive_date TEXT,
                            fiu_feedback TEXT,
                            fiu_letter_number TEXT,
                            fiu_date TEXT,
                            status TEXT DEFAULT 'pending',
                            is_deleted INTEGER DEFAULT 0,
                            created_at TEXT DEFAULT (datetime('now')),
                            created_by TEXT NOT NULL,
                            updated_at TEXT,
                            updated_by TEXT,
                            current_version INTEGER DEFAULT 1,
                            approval_status TEXT DEFAULT 'draft',
                            legal_entity_owner_checkbox INTEGER DEFAULT 0,
                            acc_membership_checkbox INTEGER DEFAULT 0,
                            relationship TEXT,
                            id_type TEXT
                        )
                    """)

                    # Restore data
                    cursor.execute("INSERT INTO reports SELECT * FROM reports_new")

                    # Drop temp table
                    cursor.execute("DROP TABLE reports_new")

                    # Recreate indexes
                    cursor.execute("CREATE INDEX idx_reports_number ON reports(report_number)")
                    cursor.execute("CREATE INDEX idx_reports_date ON reports(report_date)")
                    cursor.execute("CREATE INDEX idx_reports_status ON reports(status)")
                    cursor.execute("CREATE INDEX idx_reports_entity ON reports(reported_entity_name)")

                    conn.commit()
                    messages.append(f"Removed gender CHECK constraint (migrated {report_count} reports)")
        except Exception as e:
            # If migration fails, just log it and continue
            messages.append(f"Gender constraint migration skipped: {str(e)}")

        # Migration 21: Create activity_log table for GitHub-style changelog
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='activity_log'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE activity_log (
                    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    action_type TEXT NOT NULL CHECK(action_type IN (
                        'CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'APPROVE',
                        'REJECT', 'VERSION_CREATE', 'VERSION_DELETE', 'VERSION_RESTORE',
                        'HARD_DELETE', 'SOFT_DELETE', 'UNDELETE'
                    )),
                    report_id INTEGER,
                    report_number TEXT,
                    version_id INTEGER,
                    version_number INTEGER,
                    description TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
                    FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE SET NULL,
                    FOREIGN KEY (version_id) REFERENCES report_versions(version_id) ON DELETE SET NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX idx_activity_log_user ON activity_log(user_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_activity_log_report ON activity_log(report_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_activity_log_action ON activity_log(action_type)
            """)
            cursor.execute("""
                CREATE INDEX idx_activity_log_created ON activity_log(created_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX idx_activity_log_composite ON activity_log(report_id, created_at DESC)
            """)
            conn.commit()
            messages.append("Created activity_log table for GitHub-style changelog")

        # Migration 22: Add soft delete columns to report_versions table
        try:
            cursor.execute("SELECT is_deleted FROM report_versions LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE report_versions
                ADD COLUMN is_deleted INTEGER DEFAULT 0
            """)
            conn.commit()
            messages.append("Added is_deleted column to report_versions table")

        try:
            cursor.execute("SELECT deleted_at FROM report_versions LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE report_versions
                ADD COLUMN deleted_at TEXT
            """)
            conn.commit()
            messages.append("Added deleted_at column to report_versions table")

        try:
            cursor.execute("SELECT deleted_by FROM report_versions LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE report_versions
                ADD COLUMN deleted_by TEXT
            """)
            conn.commit()
            messages.append("Added deleted_by column to report_versions table")

        # Migration 23: Add delete tracking columns to reports table
        try:
            cursor.execute("SELECT deleted_at FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN deleted_at TEXT
            """)
            conn.commit()
            messages.append("Added deleted_at column to reports table")

        try:
            cursor.execute("SELECT deleted_by FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN deleted_by TEXT
            """)
            conn.commit()
            messages.append("Added deleted_by column to reports table")

        # Add index for version soft delete queries
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_report_versions_is_deleted'
        """)
        if not cursor.fetchone():
            try:
                cursor.execute("""
                    CREATE INDEX idx_report_versions_is_deleted ON report_versions(is_deleted)
                """)
                conn.commit()
                messages.append("Created index for report_versions is_deleted column")
            except sqlite3.OperationalError:
                pass

        # Migration 24: Fix approval workflow for existing reports
        # - Admin-created reports should be 'approved'
        # - Non-admin reports need entries in report_approvals to appear in approval panel
        try:
            # First, auto-approve all admin-created reports that aren't already approved
            cursor.execute("""
                UPDATE reports
                SET approval_status = 'approved', updated_at = datetime('now')
                WHERE created_by IN (SELECT username FROM users WHERE role = 'admin')
                AND (approval_status IS NULL OR approval_status != 'approved')
                AND is_deleted = 0
            """)
            admin_reports_fixed = cursor.rowcount
            conn.commit()

            if admin_reports_fixed > 0:
                messages.append(f"Auto-approved {admin_reports_fixed} admin-created reports")

            # Now handle non-admin reports that are in draft/pending but have no approval request
            cursor.execute("""
                SELECT r.report_id, r.created_by
                FROM reports r
                LEFT JOIN report_approvals ra ON r.report_id = ra.report_id
                WHERE r.created_by NOT IN (SELECT username FROM users WHERE role = 'admin')
                AND (r.approval_status IS NULL OR r.approval_status IN ('draft', ''))
                AND ra.approval_id IS NULL
                AND r.is_deleted = 0
            """)
            reports_needing_approval = cursor.fetchall()

            for report_id, created_by in reports_needing_approval:
                # Update report status to pending_approval
                cursor.execute("""
                    UPDATE reports
                    SET approval_status = 'pending_approval', updated_at = datetime('now')
                    WHERE report_id = ?
                """, (report_id,))

                # Create approval request
                cursor.execute("""
                    INSERT INTO report_approvals (report_id, approval_status, requested_by, approval_comment, requested_at)
                    VALUES (?, 'pending', ?, 'Auto-submitted by migration', datetime('now'))
                """, (report_id, created_by))

            conn.commit()

            if reports_needing_approval:
                messages.append(f"Created approval requests for {len(reports_needing_approval)} non-admin reports")

        except Exception as e:
            messages.append(f"Approval workflow migration skipped: {str(e)}")

        # Migration 25: Drop status column from reports table (no longer used)
        try:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reports'")
            result = cursor.fetchone()
            if result:
                # Check if status column exists (exact column name via PRAGMA:
                # substring matching on table SQL would also hit approval_status)
                cursor.execute("PRAGMA table_info(reports)")
                report_columns = {row[1] for row in cursor.fetchall()}
                if 'status' in report_columns:
                    # Backup existing data
                    cursor.execute("SELECT COUNT(*) FROM reports")
                    report_count = cursor.fetchone()[0]

                    # Drop ALL views before renaming the table: SQLite refuses
                    # ALTER TABLE ... RENAME while any view references reports
                    # (e.g. v_user_activity, which the old code missed). Save
                    # definitions so they can be recreated afterwards.
                    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view'")
                    saved_views = cursor.fetchall()
                    for view_name, _ in saved_views:
                        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

                    # Drop leftover temp table from a previously aborted run.
                    # Safe: we only reach here when reports still exists with
                    # its status column, so reports_new can only be stale.
                    cursor.execute("DROP TABLE IF EXISTS reports_new")

                    # Create temporary table without status column
                    cursor.execute("""
                        CREATE TABLE reports_new (
                            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sn INTEGER UNIQUE NOT NULL,
                            report_number TEXT UNIQUE NOT NULL,
                            report_date TEXT NOT NULL,
                            outgoing_letter_number TEXT,
                            reported_entity_name TEXT NOT NULL,
                            legal_entity_owner TEXT,
                            gender TEXT,
                            nationality TEXT,
                            id_cr TEXT,
                            account_membership TEXT,
                            branch_id TEXT,
                            cic TEXT,
                            first_reason_for_suspicion TEXT,
                            second_reason_for_suspicion TEXT,
                            type_of_suspected_transaction TEXT,
                            arb_staff TEXT,
                            total_transaction TEXT,
                            report_classification TEXT,
                            report_source TEXT,
                            reporting_entity TEXT,
                            reporter_initials TEXT,
                            sending_date TEXT,
                            original_copy_confirmation TEXT,
                            fiu_number TEXT,
                            fiu_letter_receive_date TEXT,
                            fiu_feedback TEXT,
                            fiu_letter_number TEXT,
                            fiu_date TEXT,
                            is_deleted INTEGER DEFAULT 0,
                            created_at TEXT DEFAULT (datetime('now')),
                            created_by TEXT NOT NULL,
                            updated_at TEXT,
                            updated_by TEXT,
                            current_version INTEGER DEFAULT 1,
                            approval_status TEXT DEFAULT 'draft',
                            legal_entity_owner_checkbox INTEGER DEFAULT 0,
                            acc_membership_checkbox INTEGER DEFAULT 0,
                            relationship TEXT,
                            id_type TEXT,
                            deleted_at TEXT,
                            deleted_by TEXT,
                            case_id TEXT
                        )
                    """)

                    # Copy data from old table (excluding status column).
                    # Column list is computed dynamically: migration 26 (case_id)
                    # may or may not have run before this one depending on the
                    # DB's history, so copy whatever columns both tables share.
                    cursor.execute("PRAGMA table_info(reports)")
                    src_cols = {row[1] for row in cursor.fetchall()}
                    cursor.execute("PRAGMA table_info(reports_new)")
                    dst_cols = [row[1] for row in cursor.fetchall()]
                    common = ", ".join(c for c in dst_cols if c in src_cols)
                    cursor.execute(f"""
                        INSERT INTO reports_new ({common})
                        SELECT {common} FROM reports
                    """)

                    # Drop old table
                    cursor.execute("DROP TABLE reports")

                    # Rename new table
                    cursor.execute("ALTER TABLE reports_new RENAME TO reports")

                    # Recreate indexes
                    cursor.execute("CREATE INDEX idx_reports_number ON reports(report_number)")
                    cursor.execute("CREATE INDEX idx_reports_date ON reports(report_date)")
                    cursor.execute("CREATE INDEX idx_reports_entity ON reports(reported_entity_name)")
                    cursor.execute("CREATE INDEX idx_reports_approval_status ON reports(approval_status)")

                    # Recreate the views dropped above from their saved SQL
                    for view_name, view_sql in saved_views:
                        if view_sql:
                            try:
                                cursor.execute(view_sql)
                            except sqlite3.OperationalError as view_err:
                                messages.append(f"Could not recreate view {view_name}: {view_err}")
                    cursor.execute("""
                        CREATE VIEW IF NOT EXISTS v_active_reports AS
                        SELECT * FROM reports WHERE is_deleted = 0
                    """)
                    cursor.execute("""
                        CREATE VIEW IF NOT EXISTS v_reports_with_history AS
                        SELECT
                            r.*,
                            COUNT(DISTINCT ch.change_id) as change_count,
                            MAX(ch.changed_at) as last_modified
                        FROM reports r
                        LEFT JOIN change_history ch ON r.report_id = ch.record_id AND ch.table_name = 'reports'
                        WHERE r.is_deleted = 0
                        GROUP BY r.report_id
                    """)

                    conn.commit()
                    messages.append(f"Dropped status column from reports table ({report_count} reports migrated)")

        except Exception as e:
            messages.append(f"Status column migration skipped: {str(e)}")

        # Migration 26: Add case_id column to reports table
        try:
            cursor.execute("SELECT case_id FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN case_id TEXT
            """)
            conn.commit()
            messages.append("Added case_id column to reports table")

        # Migration 27: Seed column_settings rows for all report fields on existing DBs.
        # schema.sql seeds these only when a database is created fresh; older DBs are
        # missing rows for most fields, which silently disables generic field validation.
        # Re-executing the INSERT OR IGNORE from schema.sql is safe: column_name is
        # UNIQUE, so existing rows (including admin-customized rules) are untouched.
        try:
            import os
            import re
            cursor.execute("SELECT COUNT(*) FROM column_settings")
            before_count = cursor.fetchone()[0]

            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            match = re.search(
                r"INSERT OR IGNORE INTO column_settings.*?;",
                schema_sql,
                re.DOTALL
            )
            if match:
                cursor.execute(match.group(0))
                conn.commit()
                cursor.execute("SELECT COUNT(*) FROM column_settings")
                added = cursor.fetchone()[0] - before_count
                if added > 0:
                    messages.append(f"Seeded {added} column_settings rows for field validation")
        except Exception as e:
            messages.append(f"Column settings seed skipped: {str(e)}")

        # Migration 28: Port stored dashboard widgets off the dropped status
        # column. Only rewrites the exact SYSTEM-seeded queries so admin-
        # customized widget SQL is never clobbered. Also removes the stale
        # 'status' row from column_settings (field no longer exists on reports).
        try:
            widget_rewrites = [
                ("SELECT COUNT(*) as value FROM reports WHERE status = 'Open' AND is_deleted = 0",
                 "SELECT COUNT(*) as value FROM reports WHERE approval_status IN ('draft', 'rework') AND is_deleted = 0",
                 "Draft / Rework"),
                ("SELECT COUNT(*) as value FROM reports WHERE status = 'Under Investigation' AND is_deleted = 0",
                 "SELECT COUNT(*) as value FROM reports WHERE approval_status = 'pending_approval' AND is_deleted = 0",
                 "Pending Approval"),
                ("SELECT COUNT(*) as value FROM reports WHERE status IN ('Close Case', 'Closed with STR') AND is_deleted = 0",
                 "SELECT COUNT(*) as value FROM reports WHERE approval_status = 'approved' AND is_deleted = 0",
                 "Approved"),
                ("SELECT status as label, COUNT(*) as value FROM reports WHERE is_deleted = 0 GROUP BY status",
                 "SELECT approval_status as label, COUNT(*) as value FROM reports WHERE is_deleted = 0 GROUP BY approval_status",
                 None),
            ]
            rewritten = 0
            for old_sql, new_sql, new_title in widget_rewrites:
                if new_title:
                    cursor.execute(
                        "UPDATE dashboard_config SET sql_query = ?, title = ? WHERE sql_query = ?",
                        (new_sql, new_title, old_sql)
                    )
                else:
                    cursor.execute(
                        "UPDATE dashboard_config SET sql_query = ? WHERE sql_query = ?",
                        (new_sql, old_sql)
                    )
                rewritten += cursor.rowcount

            cursor.execute("DELETE FROM column_settings WHERE column_name = 'status'")
            removed_status_row = cursor.rowcount
            conn.commit()

            if rewritten or removed_status_row:
                messages.append(f"Ported {rewritten} dashboard widgets to approval_status")
        except Exception as e:
            messages.append(f"Dashboard widget port skipped: {str(e)}")

        # Migration 29: Record-edit locks (R28) — one active editor per report
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='report_locks'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE report_locks (
                        report_id INTEGER PRIMARY KEY,
                        locked_by TEXT NOT NULL,
                        locked_by_name TEXT,
                        locked_at TEXT DEFAULT (datetime('now')),
                        expires_at TEXT NOT NULL
                    )
                """)
                conn.commit()
                messages.append("Created report_locks table")
        except Exception as e:
            messages.append(f"report_locks table skipped: {str(e)}")

        # Migration 30: Closed months (R50/R51) — numbering grace period
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='closed_months'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE closed_months (
                        month TEXT PRIMARY KEY,
                        closed_by TEXT NOT NULL,
                        closed_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.commit()
                messages.append("Created closed_months table")
        except Exception as e:
            messages.append(f"closed_months table skipped: {str(e)}")

        # Migration 31: Seed the FIU second-reason-for-suspicion catalog (R73).
        # ~147 reference values, IT-managed (not editable in Dropdown Management).
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM system_config WHERE config_type='dropdown' "
                "AND config_category='second_reason_for_suspicion'")
            existing = cursor.fetchone()[0]
            if existing < 50:  # only seed if not already populated
                import os as _os, json as _json
                ref = _os.path.join(_os.path.dirname(__file__), 'second_reasons.json')
                if _os.path.exists(ref):
                    with open(ref, encoding='utf-8') as f:
                        reasons = _json.load(f)
                    added = 0
                    for idx, val in enumerate(reasons, 1):
                        key = f"second_reason_ref_{idx}"
                        cursor.execute(
                            "INSERT OR IGNORE INTO system_config "
                            "(config_key, config_value, config_type, config_category, display_order, is_active) "
                            "VALUES (?, ?, 'dropdown', 'second_reason_for_suspicion', ?, 1)",
                            (key, val, idx))
                        added += cursor.rowcount
                    conn.commit()
                    if added:
                        messages.append(f"Seeded {added} second-reason reference values")
        except Exception as e:
            messages.append(f"Second-reason seed skipped: {str(e)}")

        # Migration 32: Total Transaction is a numeric amount (BRD R63), not a
        # "NNN SAR" string. Replace the old SAR-suffix pattern on existing DBs.
        try:
            cursor.execute(
                "SELECT validation_rules FROM column_settings WHERE column_name = 'total_transaction'")
            row = cursor.fetchone()
            if row and row[0] and 'SAR' in row[0]:
                cursor.execute(
                    "UPDATE column_settings SET validation_rules = ?, updated_at = datetime('now') "
                    "WHERE column_name = 'total_transaction'",
                    ('{"pattern": "^\\\\d{1,15}(\\\\.\\\\d{1,3})?$", "example": "605040 or 605040.50"}',))
                conn.commit()
                messages.append("Updated Total Transaction rule to numeric (removed SAR requirement)")
        except Exception as e:
            messages.append(f"Total Transaction rule update skipped: {str(e)}")

        # Migration 33: idempotency ledger for host command-RPC (exactly-once apply)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applied_commands'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE applied_commands (
                        command_id TEXT PRIMARY KEY,
                        response_json TEXT,
                        applied_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.commit()
                messages.append("Created applied_commands table")
        except Exception as e:
            messages.append(f"applied_commands table skipped: {str(e)}")

        # Migration 34: owned, transferable, non-expiring reserved number blocks (Phase 2)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reserved_numbers'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE reserved_numbers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_number TEXT UNIQUE NOT NULL,
                        serial_number INTEGER UNIQUE NOT NULL,
                        owned_by TEXT NOT NULL,
                        status TEXT CHECK(status IN ('available','used')) DEFAULT 'available',
                        used_by_report_id INTEGER,
                        reserved_at TEXT DEFAULT (datetime('now')),
                        transferred_from TEXT
                    )
                """)
                cursor.execute("CREATE INDEX idx_reserved_owner_status ON reserved_numbers(owned_by, status)")
                cursor.execute("CREATE INDEX idx_reserved_number ON reserved_numbers(report_number)")
                conn.commit()
                messages.append("Created reserved_numbers table")
        except Exception as e:
            messages.append(f"reserved_numbers table skipped: {str(e)}")

        # host_lease: single-row monotonic term for manual failover (Phase 3a)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='host_lease'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE host_lease (
                        id INTEGER PRIMARY KEY CHECK(id = 1),
                        host_id TEXT,
                        term INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                cursor.execute("INSERT OR IGNORE INTO host_lease (id, host_id, term) VALUES (1, NULL, 0)")
                conn.commit()
                messages.append("Created host_lease table")
        except Exception as e:
            messages.append(f"host_lease table skipped: {str(e)}")

        # Numbering is calendar-driven now (#15): drop the dead month grace-period config.
        try:
            cursor.execute("DELETE FROM system_config WHERE config_key = 'month_grace_period'")
            conn.commit()
        except Exception as e:
            messages.append(f"month_grace_period cleanup skipped: {str(e)}")

        # must_change_password: force a password change at next login (security)
        try:
            cursor.execute("PRAGMA table_info(users)")
            if 'must_change_password' not in [r[1] for r in cursor.fetchall()]:
                cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
                conn.commit()
                messages.append("Added must_change_password column to users")
        except Exception as e:
            messages.append(f"must_change_password column skipped: {str(e)}")

        conn.close()

        if messages:
            return True, "; ".join(messages)
        else:
            return True, "No migrations needed"

    except Exception as e:
        return False, f"Migration failed: {str(e)}"
