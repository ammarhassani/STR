"""#5 + #14 — report intelligence layer. Run: python3.14 tests_intelligence.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _svc(now=None):
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.intelligence_service import IntelligenceService
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    return dbm, IntelligenceService(dbm, None, now=now)


def _insert(dbm, report_number, sn, entity, date, cic=None, account=None, deleted=0,
            total=None, classification=None, status='approved'):
    dbm.execute_with_retry(
        "INSERT INTO reports (report_number, sn, report_date, reported_entity_name, "
        "cic, account_membership, total_transaction, report_classification, "
        "approval_status, created_by, is_deleted) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (report_number, sn, date, entity, cic, account, total, classification, status, 'ag1', deleted))


def test_cic_history():
    dbm, intel = _svc()
    _insert(dbm, 'R-1', 1, 'Acme', '01/07/2026', cic='1234567890123456')
    _insert(dbm, 'R-2', 2, 'Acme Again', '05/07/2026', cic='1234567890123456')
    _insert(dbm, 'R-3', 3, 'Other', '05/07/2026', cic='9999999999999999')
    _insert(dbm, 'R-4', 4, 'Deleted', '05/07/2026', cic='1234567890123456', deleted=1)

    h = intel.cic_history('1234567890123456')
    check("finds both live reports on the CIC", h['count'] == 2, h['count'])
    check("excludes deleted reports", all(r['report_number'] != 'R-4' for r in h['reports']))
    check("does not pull other CICs", all(r['cic'] == '1234567890123456' for r in h['reports']))

    # exclude the report being edited
    rid = [r['report_id'] for r in h['reports'] if r['report_number'] == 'R-1'][0]
    h2 = intel.cic_history('1234567890123456', exclude_report_id=rid)
    check("excludes the report being edited", h2['count'] == 1 and h2['reports'][0]['report_number'] == 'R-2', h2)

    check("empty CIC -> no history", intel.cic_history('')['count'] == 0)
    check("unknown CIC -> no history", intel.cic_history('0000000000000000')['count'] == 0)


def test_account_rapid_repeat():
    dbm, intel = _svc()
    _insert(dbm, 'A-1', 1, 'E', '01/07/2026', account='ACC-100')
    _insert(dbm, 'A-2', 2, 'E', '02/07/2026', account='ACC-100')   # +1 day
    _insert(dbm, 'A-3', 3, 'E', '03/07/2026', account='ACC-100')   # +2 days
    _insert(dbm, 'A-4', 4, 'E', '10/07/2026', account='ACC-100')   # far outside window
    _insert(dbm, 'A-5', 5, 'E', '01/07/2026', account='ACC-999')   # different account

    # entering a new report on ACC-100 dated 01/07 — repeats within 0-2 days
    r = intel.account_rapid_repeat('ACC-100', '01/07/2026', within_days=2)
    nums = sorted(x['report_number'] for x in r['reports'])
    check("counts repeats within +/-2 days", r['count'] == 3, r['count'])
    check("includes the same-day and +1/+2 day reports", nums == ['A-1', 'A-2', 'A-3'], nums)
    check("excludes the report outside the window", 'A-4' not in nums)
    check("excludes a different account", 'A-5' not in nums)

    # exclude the report being edited (say A-1 is the current one)
    rid = dbm.execute_with_retry("SELECT report_id FROM reports WHERE report_number='A-1'")[0][0]
    r2 = intel.account_rapid_repeat('ACC-100', '01/07/2026', within_days=2, exclude_report_id=rid)
    check("excluding current report drops it from the count", r2['count'] == 2, r2['count'])

    check("account with no reports at all -> count 0",
          intel.account_rapid_repeat('ACC-000', '01/07/2026')['count'] == 0)
    # a single prior report far outside the window is not a rapid repeat
    check("prior report outside window -> count 0",
          intel.account_rapid_repeat('ACC-100', '20/08/2026', within_days=2)['count'] == 0)
    check("unparseable date -> no signal (never crash)",
          intel.account_rapid_repeat('ACC-100', 'garbage')['count'] == 0)
    check("empty account -> no signal", intel.account_rapid_repeat('', '01/07/2026')['count'] == 0)


def test_cic_summary_signals():
    from datetime import datetime
    # fixed "now" so days_since_last is deterministic
    dbm, intel = _svc(now=lambda: datetime(2026, 7, 20))
    _insert(dbm, 'S-1', 1, 'Acme Corp', '01/07/2026', cic='1111111111111111',
            total='1,000.50', classification='Cash', status='approved')
    _insert(dbm, 'S-2', 2, 'Acme Holdings', '15/07/2026', cic='1111111111111111',
            total='2500', classification='Wire', status='pending_approval')
    _insert(dbm, 'S-3', 3, 'Acme Corp', '10/07/2026', cic='1111111111111111',
            total='500', classification='Cash', status='rework')

    h = intel.cic_history('1111111111111111')
    s = h['summary']
    check("count is 3", h['count'] == 3, h['count'])
    check("distinct entities collapsed", sorted(s['entities']) == ['Acme Corp', 'Acme Holdings'], s['entities'])
    check("amount sum parsed across formats", abs(s['amount_sum'] - 4000.5) < 0.01, s['amount_sum'])
    check("amount min/max", s['amount_min'] == 500.0 and s['amount_max'] == 2500.0, (s['amount_min'], s['amount_max']))
    check("distinct classifications", sorted(s['classifications']) == ['Cash', 'Wire'], s['classifications'])
    check("pending counts pending_approval + rework", s['pending'] == 2, s['pending'])
    # most recent report_date is 15/07; now is 20/07 -> 5 days
    check("days since last report", s['days_since_last'] == 5, s['days_since_last'])


def test_customer_profile_lookup():
    """The CIC is the customer code the analyst starts from: typing it must
    bring back what the bank already recorded for that customer, so nobody
    retypes (or mistypes) the name/ID/branch on every new report."""
    dbm, intel = _svc()
    dbm.execute_with_retry(
        "INSERT INTO reports (report_number, sn, report_date, reported_entity_name, cic, "
        "nationality, gender, id_cr, branch_id, account_membership, approval_status, "
        "created_by, is_deleted, created_at) "
        "VALUES ('R-10',10,'01/07/2026','Falcon Trading Est','1234567890123456',"
        "'Saudi Arabian','Male','7012345678','045','12345678','approved','ag1',0,'2026-07-01')")

    prof = intel.customer_profile('1234567890123456')
    check("known CIC returns a profile", prof is not None)
    check("profile carries the entity name",
          (prof or {}).get('reported_entity_name') == 'Falcon Trading Est', prof)
    check("profile carries nationality, branch and ID",
          (prof or {}).get('nationality') == 'Saudi Arabian'
          and (prof or {}).get('branch_id') == '045'
          and (prof or {}).get('id_cr') == '7012345678', prof)
    check("the account is NOT carried over (a customer may hold several, or an "
          "account and a membership)", 'account_membership' not in (prof or {}), prof)
    check("unknown CIC returns nothing", intel.customer_profile('9999999999999999') is None)
    check("blank CIC returns nothing", intel.customer_profile('') is None)

    rid = dbm.execute_with_retry(
        "SELECT report_id FROM reports WHERE report_number='R-10'")[0][0]
    check("the report being edited is not its own source",
          intel.customer_profile('1234567890123456', exclude_report_id=rid) is None)

    # a newer report for the same customer supersedes the older details
    dbm.execute_with_retry(
        "INSERT INTO reports (report_number, sn, report_date, reported_entity_name, cic, "
        "nationality, approval_status, created_by, is_deleted, created_at) "
        "VALUES ('R-11',11,'05/07/2026','Falcon Trading LLC','1234567890123456',"
        "'Saudi Arabian','approved','ag1',0,'2026-07-05')")
    check("most recent report wins",
          (intel.customer_profile('1234567890123456') or {}).get('reported_entity_name')
          == 'Falcon Trading LLC')

    # a soft-deleted report must never be used as a source of customer details
    # updated_by must be set on the SAME update: the soft-delete audit trigger
    # copies it into change_history.changed_by, which is NOT NULL
    dbm.execute_with_retry(
        "UPDATE reports SET is_deleted=1, updated_by='ag1', updated_at=datetime('now') "
        "WHERE report_number='R-11'")
    check("deleted reports are not used as a profile source",
          (intel.customer_profile('1234567890123456') or {}).get('reported_entity_name')
          == 'Falcon Trading Est')


if __name__ == "__main__":
    test_cic_history()
    test_cic_summary_signals()
    test_account_rapid_repeat()
    test_customer_profile_lookup()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
