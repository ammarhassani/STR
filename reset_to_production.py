"""Hard reset: wipe all TEST data and hand back a clean production database (#22).

Keeps everything an admin configured — dropdown values, custom fields, dashboard
widgets, system settings — and deletes everything transactional: reports,
approvals, versions, reserved numbers, activity/audit/logs, queues, locks. Users
are reset to a single fresh admin (must change password at first login).

ALWAYS run this on the HOST PC against the authoritative database, with the host
process stopped. It backs the database up first; even so, this is irreversible
for the wiped data. See docs/SETUP.md → "Going live".

Usage:
    python reset_to_production.py                # uses the configured DB path
    python reset_to_production.py --db PATH      # explicit database file
    python reset_to_production.py --yes          # skip the typed confirmation
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Transactional tables — every row is operational/test data and gets cleared.
_WIPE_TABLES = [
    "reports", "report_approvals", "report_versions",
    "report_number_reservations", "reserved_numbers", "report_locks",
    "activity_log", "change_history", "status_history", "audit_log",
    "system_logs", "session_log", "backup_log", "restore_log",
    "notifications", "saved_filters", "closed_months",
    "applied_commands", "gap_queue",
]

# Configuration tables — preserved untouched.
_PRESERVE_TABLES = [
    "column_settings", "dashboard_config", "system_config",
    "system_settings", "system_metadata", "migration_history",
]


def _table_exists(cur, name: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _fresh_admin_hash() -> str:
    """bcrypt hash for the temporary admin password 'admin123'."""
    from services.security_service import SecurityService
    return SecurityService.hash_password("admin123")


def hard_reset(db_path: str, admin_username: str = "admin") -> dict:
    """Wipe transactional data and reset to a single fresh admin. Returns a
    summary dict {cleared: {table: rows}, admin: username}. Assumes the caller
    has already confirmed + backed up."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = OFF")

        cleared = {}
        for t in _WIPE_TABLES:
            if _table_exists(cur, t):
                n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                cur.execute(f"DELETE FROM {t}")
                cleared[t] = n

        # Users -> a single clean admin that must change its password.
        if _table_exists(cur, "users"):
            cur.execute("DELETE FROM users")
            cur.execute(
                "INSERT INTO users (username, password, full_name, role, is_active, "
                "must_change_password, created_by) VALUES (?,?,?,?,1,1,'SYSTEM')",
                (admin_username, _fresh_admin_hash(), "Administrator", "admin"))

        # Single-writer lease back to a clean, unclaimed state.
        if _table_exists(cur, "host_lease"):
            cur.execute("DELETE FROM host_lease")
            cur.execute("INSERT INTO host_lease (id, host_id, term) VALUES (1, NULL, 0)")

        conn.commit()
        cur.execute("VACUUM")
        conn.commit()
        return {"cleared": cleared, "admin": admin_username}
    finally:
        conn.close()


def _resolve_db_path(explicit: str = None) -> str:
    if explicit:
        return explicit
    from config import Config
    Config.load()
    if not Config.DATABASE_PATH:
        raise SystemExit("No database path configured. Pass --db PATH or run setup first.")
    return Config.DATABASE_PATH


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hard reset STR to a clean production database.")
    ap.add_argument("--db", help="Path to the database file (default: configured path)")
    ap.add_argument("--yes", action="store_true", help="Skip the typed confirmation")
    ap.add_argument("--no-backup", action="store_true", help="Do not back up first (not recommended)")
    args = ap.parse_args(argv)

    db_path = _resolve_db_path(args.db)
    if not Path(db_path).exists():
        raise SystemExit(f"Database not found: {db_path}")

    print(f"Target database: {db_path}")
    print("This will PERMANENTLY DELETE all reports, approvals, versions, reserved")
    print("numbers, activity and logs, and reset users to a single fresh admin.")
    print("Configuration (dropdowns, fields, dashboard widgets, settings) is kept.")
    if not args.yes:
        if input('\nType "RESET" to proceed: ').strip() != "RESET":
            print("Aborted."); return 1

    if not args.no_backup:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{db_path}.pre-reset-{stamp}.bak"
        shutil.copy2(db_path, backup)
        print(f"Backup written: {backup}")

    summary = hard_reset(db_path)
    total = sum(summary["cleared"].values())
    print(f"\nCleared {total} row(s) across {len(summary['cleared'])} table(s).")
    print(f"Users reset to a single admin '{summary['admin']}' "
          f"(temporary password 'admin123' — change on first login).")
    print("Done. Restart the host so it republishes the clean database.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
