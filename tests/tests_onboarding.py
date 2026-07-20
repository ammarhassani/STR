"""#1 — two-way handshake user onboarding. Run: python3.14 tests_onboarding.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _auth():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.security_service import SecurityService
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db); log = LoggingService(dbm, None, db_logging=False)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    conn.commit(); conn.close()
    return AuthService(dbm, log)


def test_handshake_happy_path():
    auth = _auth()
    auth.authenticate('admin', 'Admin@1234')

    # admin creates a user ID + role ONLY (no password, no name)
    ok, msg = auth.create_pending_user('reporter7', 'reporter')
    check("admin creates a pending user (ID + role only)", ok, msg)
    check("new user is pending", auth.get_onboarding_status('reporter7') == 'pending')

    # admin CANNOT log in as that user, and neither can anyone with a blank pw
    okp, _u, m = auth.authenticate('reporter7', '')
    check("pending user cannot authenticate with empty password", not okp, m)
    check("authenticate signals onboarding required", m == "ONBOARDING_REQUIRED", m)
    okp2, _u2, _m2 = auth.authenticate('reporter7', 'anything')
    check("pending user cannot authenticate with any password", not okp2)

    # the USER self-registers their own name + password
    okc, mc = auth.complete_onboarding('reporter7', 'Reporter Seven', 'MyStr0ng!Pass')
    check("user completes onboarding (sets own name + password)", okc, mc)
    check("user no longer pending", auth.get_onboarding_status('reporter7') == 'active')

    # now they can log in with the password ONLY they know
    oka, u, ma = auth.authenticate('reporter7', 'MyStr0ng!Pass')
    check("user logs in with their self-set password", oka, ma)
    check("full name was set by the user", u and u['full_name'] == 'Reporter Seven', u)
    check("role is what the admin assigned", u and u['role'] == 'reporter', u)


def test_onboarding_guards():
    auth = _auth()
    auth.authenticate('admin', 'Admin@1234')
    auth.create_pending_user('u1', 'agent')

    # weak / empty password rejected
    ok, m = auth.complete_onboarding('u1', 'U One', 'short')
    check("weak password rejected", not ok, m)
    ok, m = auth.complete_onboarding('u1', '', 'GoodPass123')
    check("empty full name rejected", not ok, m)
    ok, m = auth.complete_onboarding('nosuch', 'X', 'GoodPass123')
    check("unknown user rejected", not ok, m)

    # can't complete twice
    auth.complete_onboarding('u1', 'U One', 'GoodPass123')
    ok, m = auth.complete_onboarding('u1', 'U One', 'GoodPass123')
    check("cannot re-complete an already-registered user", not ok, m)


def test_admin_gating():
    auth = _auth()
    auth.authenticate('admin', 'Admin@1234')
    auth.create_pending_user('agentx', 'agent')
    auth.complete_onboarding('agentx', 'Agent X', 'GoodPass123')

    # a non-admin cannot create pending users nor reset onboarding
    auth.authenticate('agentx', 'GoodPass123')
    ok, _ = auth.create_pending_user('sneak', 'admin')
    check("non-admin CANNOT create a pending user", not ok)
    ok, _ = auth.reset_onboarding('agentx')
    check("non-admin CANNOT reset onboarding", not ok)


def test_reset_onboarding_rearms():
    auth = _auth()
    auth.authenticate('admin', 'Admin@1234')
    auth.create_pending_user('rep9', 'reporter')
    auth.complete_onboarding('rep9', 'Rep Nine', 'FirstPass123')
    check("registered before reset", auth.get_onboarding_status('rep9') == 'active')

    # admin re-arms (forgotten password)
    auth.authenticate('admin', 'Admin@1234')
    ok, m = auth.reset_onboarding('rep9')
    check("admin resets onboarding", ok, m)
    check("user is pending again", auth.get_onboarding_status('rep9') == 'pending')
    # old password no longer works
    okold, _u, _m = auth.authenticate('rep9', 'FirstPass123')
    check("old password refused after reset", not okold)
    # user sets a NEW password
    auth.complete_onboarding('rep9', 'Rep Nine', 'SecondPass456')
    oknew, _u, _m = auth.authenticate('rep9', 'SecondPass456')
    check("user logs in with the new self-set password", oknew)


if __name__ == "__main__":
    test_handshake_happy_path()
    test_onboarding_guards()
    test_admin_gating()
    test_reset_onboarding_rearms()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
