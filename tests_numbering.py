"""#15 — calendar-driven numbering + reservation persistence across month rollover.
No grace period, no manual close; a reserved number is a $100 bill that keeps its
month and stays with its owner until used or transferred.
Run: python3.14 tests_numbering.py
"""
import os, sys, tempfile, sqlite3, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _setup():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.report_number_service import ReportNumberService
    from services.report_service import ReportService
    from services.security_service import SecurityService
    d = tempfile.mkdtemp(); db = os.path.join(d, "n.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db); log = LoggingService(dbm, None, db_logging=False)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    conn.commit(); conn.close()
    auth = AuthService(dbm, log)
    auth.authenticate('admin', 'Admin@1234')
    auth.create_user('agent1', 'Pass@123', 'Agent One', 'agent')
    numbers = ReportNumberService(dbm, log)
    reports = ReportService(dbm, log, auth); reports.set_report_number_service(numbers)
    return dbm, auth, numbers, reports


def test_calendar_month_no_grace():
    _, _, N, _ = _setup()
    # grace is gone: on day 1 of a month it's already that month (no lingering prev)
    N._now = lambda: datetime.datetime(2026, 8, 1)
    check("day-1 of month = that calendar month (no grace)", N.get_active_numbering_month() == "2026/08",
          N.get_active_numbering_month())
    N._now = lambda: datetime.datetime(2026, 8, 31)
    check("day-31 same month", N.get_active_numbering_month() == "2026/08")
    check("close_month removed", not hasattr(N, "close_month"))
    check("grace method removed", not hasattr(N, "get_month_with_grace_period"))


def test_rollover_and_reservation_persistence():
    _, auth, N, R = _setup()

    # --- June: reserve 3 ---
    N._now = lambda: datetime.datetime(2026, 6, 15)
    R._now = lambda: datetime.datetime(2026, 6, 15)
    ok, june, _ = N.reserve_block('agent1', 3)
    check("june reserve opens at 001", ok and june == ['2026/06/001', '2026/06/002', '2026/06/003'], june)

    # --- roll to August (grace would have kept July; it must NOT) ---
    N._now = lambda: datetime.datetime(2026, 8, 1)
    R._now = lambda: datetime.datetime(2026, 8, 1)
    ok2, aug, _ = N.reserve_block('agent1', 2)
    check("new month opens its own sequence at 001", ok2 and aug == ['2026/08/001', '2026/08/002'], aug)

    # --- June numbers persist: still owned + available after the month ended ---
    avail = {n['report_number']: n for n in N.get_available_numbers('agent1')}
    check("june $100-bills still owned+available in august",
          {'2026/06/001', '2026/06/002', '2026/06/003'} <= set(avail), list(avail))
    # serial numbers are global and never reset (june 1-3, august 4-5)
    serials = sorted(n['serial_number'] for n in avail.values())
    check("serial numbers global + continuous (never reset)", serials == [1, 2, 3, 4, 5], serials)

    # --- a report created in august still spends the lowest reserved bill (a june one) ---
    auth.authenticate('agent1', 'Pass@123')
    ok3, rid, msg = R.create_report({
        'report_date': '01/08/2026', 'reported_entity_name': 'Entity X',
        'nationality': 'Saudi Arabian', 'total_transaction': '1000'})
    check("create after rollover consumes a reserved number", ok3, msg)
    rep = R.get_report(rid)
    check("consumed the lowest bill = the june number", rep and rep['report_number'] == '2026/06/001',
          rep.get('report_number') if rep else None)
    # that june number is now 'used', the rest remain
    left = {n['report_number'] for n in N.get_available_numbers('agent1')}
    check("used june number leaves the available pool", '2026/06/001' not in left)
    check("other reserved numbers still available", {'2026/06/002', '2026/08/001'} <= left, list(left))


def test_year_rollover():
    _, _, N, _ = _setup()
    N._now = lambda: datetime.datetime(2026, 12, 31)
    okd, dec, _ = N.reserve_block('agent1', 1)
    N._now = lambda: datetime.datetime(2027, 1, 1)
    okj, jan, _ = N.reserve_block('agent1', 1)
    check("december is 2026/12/001", okd and dec == ['2026/12/001'], dec)
    check("january rolls the year -> 2027/01/001", okj and jan == ['2027/01/001'], jan)


if __name__ == "__main__":
    test_calendar_month_no_grace()
    test_rollover_and_reservation_persistence()
    test_year_rollover()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
