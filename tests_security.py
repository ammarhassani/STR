"""Security hardening checks: no plaintext/demo accounts shipped, admin bcrypt +
forced password change. Run: python3.14 tests_security.py"""
import os, sys, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def test_shipped_db_is_clean():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    d = tempfile.mkdtemp(); db = os.path.join(d, "s.db")
    initialize_database(db); migrate_database(db)
    conn = sqlite3.connect(db)
    users = conn.execute("SELECT username, password, must_change_password FROM users").fetchall()
    names = {u[0] for u in users}
    check("shipped DB has only the admin account", names == {"admin"}, names)
    check("no demo agent1/reporter1 shipped", "agent1" not in names and "reporter1" not in names)
    admin = [u for u in users if u[0] == "admin"][0]
    check("admin password is a bcrypt hash (not plaintext)", SecurityService.is_bcrypt_hash(admin[1]), admin[1][:12])
    check("admin flagged must_change_password", admin[2] == 1, admin[2])
    check("no demo reports shipped", conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0)
    conn.close()


def test_forced_change_flow():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    d = tempfile.mkdtemp(); db = os.path.join(d, "s.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db); a = AuthService(dbm, LoggingService(dbm, None))
    ok, user, _ = a.authenticate("admin", "admin123")
    check("admin logs in with default bcrypt password", ok)
    check("login surfaces must_change_password=True", user.get("must_change_password") is True, user)
    # changing the password clears the flag
    a.change_password(user["user_id"], "Str0ng@New1")
    ok2, user2, _ = a.authenticate("admin", "Str0ng@New1")
    check("new password works", ok2)
    check("flag cleared after change", user2.get("must_change_password") is False, user2)
    ok3, _, _ = a.authenticate("admin", "admin123")
    check("old default password no longer works", ok3 is False)


def test_migration_adds_column_to_old_db():
    # simulate a pre-existing DB lacking the column, then migrate
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp(); db = os.path.join(d, "s.db")
    initialize_database(db)
    conn = sqlite3.connect(db)
    try:
        conn.execute("ALTER TABLE users DROP COLUMN must_change_password")
        conn.commit()
    except Exception:
        pass  # SQLite may not support DROP COLUMN on this version — skip the simulation
    conn.close()
    migrate_database(db)
    cols = [r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(users)")]
    check("migration ensures must_change_password column exists", "must_change_password" in cols, cols)


if __name__ == "__main__":
    test_shipped_db_is_clean()
    test_forced_change_flow()
    test_migration_adds_column_to_old_db()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
