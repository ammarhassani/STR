"""TWO WEEKS ON THE FLOOR — a full business simulation of an FIU unit.

Not a crash test. This is the unit actually working: 20 agents each filing 50
reports a day, 5 supervisors reviewing everything they send, reports coming back
for rework and being fixed the next morning, reporters reading the books, across
10 business days (two working weeks, Sunday-Thursday).

It answers the questions a head of unit asks, not the ones a test suite asks:
  - did the agents hit 50 a day, and did the supervisors keep up?
  - how long did a report wait between being submitted and being decided?
  - did the backlog grow week on week?
  - after 10,000 reports and a month rollover, is the numbering still sound and
    is every report in a state that makes sense?

Run:  python tests_simulation_fortnight.py [days] [agents] [reports_per_agent]
Default: 10 days, 20 agents, 50 reports/agent/day.

Everything runs against the real service stack. Concurrency is threads rather
than processes, and WRITES ARE SERIALISED behind one lock -- because that is
what production does: every client write is a command queued to a single host
process that applies it alone. Twenty desks writing to one SQLite file in
parallel is not the deployed shape, and measuring it would measure a system
nobody is running. The lock stands in for the host.
"""
import os
import sys
import time
import random
import sqlite3
import tempfile
import threading
import statistics
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
N_AGENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
PER_AGENT_PER_DAY = int(sys.argv[3]) if len(sys.argv) > 3 else 50
N_SUPERVISORS = 5
N_REPORTERS = 3
PW = 'Shift@1234'

# Start mid-month so the fortnight crosses a month boundary: the numbering
# sequence resets monthly and that rollover has to survive a live workload.
START = datetime(2026, 7, 27)

ENTITIES = ["Falcon Trading Est", "Gulf Metals LLC", "Rakan Holdings", "Sadara Exchange",
            "Nujoom Logistics", "Al Waha Foods", "Tamween Corp", "Marsa Shipping",
            "Deera Contracting", "Yamama Cement Co", "Anwar Jewellery", "Bahr Marine"]
CLASSIFICATIONS = ["Money Laundering", "Terrorist Financing", "Fraud", "Tax Evasion",
                   "Corruption", "Sanctions Violation", "Other Financial Crime"]
SOURCES = ["Internal monitoring", "Customer due diligence", "Transaction monitoring",
           "External tip", "Law enforcement request", "Media report"]
TXN_TYPES = ["Cash deposit", "Cash withdrawal", "Wire transfer", "Check deposit",
             "Foreign exchange", "Investment transaction", "Multiple transactions"]

# The host is the only writer in production; everything funnels through it.
HOST = threading.Lock()

metrics = defaultdict(int)
create_latency = []
decision_latency = []          # submitted -> decided, in simulated hours
daily = []                     # one row per business day
_lock = threading.Lock()
_errors = []


def bump(key, n=1):
    with _lock:
        metrics[key] += n


def oops(who, what, detail=""):
    with _lock:
        _errors.append(f"{who}: {what} — {str(detail)[:160]}")


# --------------------------------------------------------------------- setup
def build_unit():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.security_service import SecurityService

    d = tempfile.mkdtemp(prefix="fiu_fortnight_")
    db = os.path.join(d, "fiu.db")
    initialize_database(db)
    migrate_database(db)

    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password(PW),))
    people = []
    for i in range(1, N_AGENTS + 1):
        people.append((f"agent{i:02d}", "agent"))
    for i in range(1, N_SUPERVISORS + 1):
        people.append((f"sup{i}", "supervisor"))
    for i in range(1, N_REPORTERS + 1):
        people.append((f"reporter{i}", "reporter"))
    for username, role in people:
        conn.execute(
            "INSERT OR IGNORE INTO users (username,password,full_name,role,is_active,"
            "created_by,must_change_password) VALUES (?,?,?,?,1,'SYSTEM',0)",
            (username, SecurityService.hash_password(PW), username.upper(), role))
    conn.commit()
    conn.close()
    return db


_shared_log = None
_log_lock = threading.Lock()


def _logger_for(db):
    """One LoggingService for the whole simulation.

    LoggingService grabs the process-wide logger 'fiu_system' and does
    handlers.clear() before adding its own. In production that is one per PC, so
    it is harmless -- but building one per person in a single process means 20
    threads clearing and re-adding handlers on a shared logger, which both
    serialises everything behind the logging lock and loses records. The desks
    share one, which is what 20 separate workstations would each have anyway.
    """
    global _shared_log
    if _shared_log is not None:
        return _shared_log
    with _log_lock:                    # 20 desks start at once; build it once
        if _shared_log is not None:
            return _shared_log
        import logging
        from services.logging_service import LoggingService
        built = LoggingService(None, None, db_logging=False)
        # keep the file handler (production writes one); drop the console
        # handler so a simulated fortnight is not throttled by terminal I/O
        for h in list(built.logger.handlers):
            if isinstance(h, logging.StreamHandler) and not hasattr(h, 'baseFilename'):
                built.logger.removeHandler(h)
        _shared_log = built
    return _shared_log


class Desk:
    """One person's session: their own service stack, like their own PC."""

    def __init__(self, db, username, now):
        from database.db_manager import DatabaseManager
        from services.auth_service import AuthService
        from services.report_service import ReportService
        from services.report_number_service import ReportNumberService
        from services.activity_service import ActivityService
        from services.version_service import VersionService
        from services.approval_service import ApprovalService

        self.username = username
        self.db = DatabaseManager(db)
        self.log = _logger_for(db)
        self.auth = AuthService(self.db, self.log)
        self.log.set_auth_service(self.auth)
        self.act = ActivityService(self.db, self.log, self.auth)
        self.nums = ReportNumberService(self.db, self.log, self.auth)
        self.reports = ReportService(self.db, self.log, self.auth, self.act)
        self.versions = VersionService(self.db, self.log, self.auth, self.reports, self.act)
        self.approvals = ApprovalService(self.db, self.log, self.auth,
                                         self.versions, self.reports, self.act)
        self.reports.set_activity_service(self.act)
        self.reports.set_report_number_service(self.nums)
        self.reports.set_version_service(self.versions)
        self.set_clock(now)
        ok, user, msg = self.auth.authenticate(username, PW)
        if not ok:
            oops(username, "could not log in", msg)
        self.user = user

    def set_clock(self, now):
        """The whole desk agrees what day it is."""
        self.now = now
        self.nums._now = lambda: now
        self.reports._now = lambda: now


# ------------------------------------------------------------------- the work
def agent_day(desk, day_no, today, rng, agent_idx=0):
    """One agent's shift: clear yesterday's rework first, then file the day's
    reports, chase the FIU numbers, and submit what is ready."""
    stamp = today.strftime("%d/%m/%Y")

    # 1. Rework comes first -- it is already late.
    rows, _ = desk.reports.get_reports('rework', None, None, None, desk.username, 100, 0)
    for rep in rows:
        rid = rep['report_id']
        with HOST:
            ok, msg = desk.reports.update_report(rid, {
                'first_reason_for_suspicion': f"Revised after review on {stamp}. "
                                              f"Additional transaction detail attached.",
            })
        if not ok:
            oops(desk.username, "could not fix a reworked report", msg)
            continue
        with HOST:
            ok2, _aid, msg2 = desk.approvals.request_approval(rid, "Reworked and resubmitted")
        if ok2:
            bump('resubmitted')
            with _lock:
                _submitted_at[rid] = today
        else:
            oops(desk.username, "could not resubmit after rework", msg2)

    # 2. Today's own filings.
    target = PER_AGENT_PER_DAY
    if desk.nums.get_available_count(desk.username) < target:
        with HOST:
            okr, block, msgr = desk.nums.reserve_block(desk.username, target)
        if not okr:
            oops(desk.username, "could not reserve numbers", msgr)
            return

    for i in range(target):
        t0 = time.time()
        # One live report per CIC is a real rule (a customer is not reported
        # twice while a report is open), so the simulation must not hand two
        # agents the same customer by accident. Deterministic and unique:
        cic = f"{9_000_000_000_000_000 + agent_idx * 10 ** 7 + day_no * 10 ** 4 + i:016d}"
        payload = {
            'report_date': stamp,
            'reported_entity_name': rng.choice(ENTITIES),
            'cic': cic,
            'nationality': 'Saudi Arabian',
            'gender': rng.choice(['Male', 'Female']),
            'customer_segment': rng.choice(['Retail', 'Corporate']),
            'total_transaction': str(rng.randint(25_000, 4_000_000)),
            'report_classification': rng.choice(CLASSIFICATIONS),
            'report_source': rng.choice(SOURCES),
            'type_of_suspected_transaction': rng.choice(TXN_TYPES),
            'first_reason_for_suspicion': "Pattern inconsistent with the customer's "
                                          "declared business activity.",
            'branch_id': f"{rng.randint(1, 220):03d}",
        }
        # Most reports are filed on the FIU portal the same day; some are left
        # for tomorrow, which is what keeps a real basket non-empty.
        filed_today = rng.random() < 0.85
        if filed_today:
            payload['fiu_number'] = f"FIU-{today:%Y%m}-{desk.username}-{i:03d}"
            payload['fiu_date'] = stamp

        with HOST:
            ok, rid, msg = desk.reports.create_report(payload)
        create_latency.append(time.time() - t0)
        if not ok:
            oops(desk.username, "create failed", msg)
            continue
        bump('created')

        if filed_today:
            with HOST:
                ok2, _aid, msg2 = desk.approvals.request_approval(rid, "Filed with the FIU")
            if ok2:
                bump('submitted')
                with _lock:
                    _submitted_at[rid] = today
            else:
                oops(desk.username, "submit failed", msg2)
        else:
            bump('left_in_basket')

    # 3. Yesterday's basket: the FIU numbers have come back by now.
    rows, _ = desk.reports.get_reports(desk.reports.STATUS_PENDING_FIU, None, None, None,
                                       desk.username, 100, 0)
    for rep in rows:
        rid = rep['report_id']
        with HOST:
            ok, msg = desk.reports.update_report(rid, {
                'fiu_number': f"FIU-{today:%Y%m}-{desk.username}-L{rid}",
                'fiu_date': stamp})
        if not ok:
            continue
        with HOST:
            ok2, _aid, _ = desk.approvals.request_approval(rid, "FIU details received")
        if ok2:
            bump('submitted_from_basket')
            with _lock:
                _submitted_at[rid] = today


def supervisor_day(desk, day_no, today, rng, stop_after):
    """A supervisor works the queue until it is clear or the shift ends."""
    decided = 0
    while time.time() < stop_after:
        pend = desk.approvals.get_pending_approvals() or []
        if not pend:
            break
        for p in pend:
            if time.time() >= stop_after:
                break
            rid = p.get('report_id')
            aid = p.get('approval_id')
            rep = desk.reports.get_report(rid) if rid else None
            if not rep:
                continue
            # never decide your own submission
            if (rep.get('created_by') or '') == desk.username:
                continue

            roll = rng.random()
            with HOST:
                if roll < 0.80:
                    ok, msg = desk.approvals.approve_report(aid, "Reviewed against the FIU letter.")
                    kind = 'approved'
                elif roll < 0.95:
                    ok, msg = desk.approvals.reject_report(
                        aid, "Expand the reason for suspicion and attach the transaction list.",
                        True)
                    kind = 'reworked'
                else:
                    ok, msg = desk.approvals.reject_report(
                        aid, "Does not meet the reporting threshold.", False)
                    kind = 'rejected'

            if ok:
                bump(kind)
                decided += 1
                with _lock:
                    started = _submitted_at.get(rid)
                if started:
                    decision_latency.append((today - started).days)
            elif 'already' not in (msg or '').lower():
                oops(desk.username, f"{kind} failed", msg)
    return decided


def reporter_day(desk, today):
    """A reporter reads: the day's book and the dashboard."""
    rows, total = desk.reports.get_reports(None, None, None, None, None, 200, 0)
    bump('reporter_reads', 1)
    return total


_submitted_at = {}


# ---------------------------------------------------------------------- main
def run():
    print(f"=== TWO WEEKS ON THE FLOOR ===")
    print(f"{N_AGENTS} agents x {PER_AGENT_PER_DAY}/day, {N_SUPERVISORS} supervisors, "
          f"{DAYS} business days\n")
    db = build_unit()

    agents = [f"agent{i:02d}" for i in range(1, N_AGENTS + 1)]
    sups = [f"sup{i}" for i in range(1, N_SUPERVISORS + 1)]
    reporters = [f"reporter{i}" for i in range(1, N_REPORTERS + 1)]

    day = START
    wall_start = time.time()
    for day_no in range(1, DAYS + 1):
        # Sunday-Thursday working week
        while day.weekday() in (4, 5):        # Fri, Sat
            day += timedelta(days=1)

        t_day = time.time()
        before = dict(metrics)

        # --- agents file the day's work
        desks = {}
        threads = []
        for idx, name in enumerate(agents):
            def shift(name=name, idx=idx):
                desk = Desk(db, name, day)
                desks[name] = desk
                agent_day(desk, day_no, day, random.Random(idx * 977 + day_no), idx + 1)
            th = threading.Thread(target=shift, daemon=True)
            threads.append(th); th.start()
        for th in threads:
            th.join()

        # --- supervisors clear the queue (a shift has an end)
        shift_end = time.time() + 90
        sthreads = []
        for idx, name in enumerate(sups):
            def review(name=name, idx=idx):
                desk = Desk(db, name, day)
                supervisor_day(desk, day_no, day, random.Random(500 + idx + day_no), shift_end)
            th = threading.Thread(target=review, daemon=True)
            sthreads.append(th); th.start()
        for th in sthreads:
            th.join()

        # --- reporters read
        for name in reporters:
            reporter_day(Desk(db, name, day), day)

        conn = sqlite3.connect(db)
        q = lambda sql: conn.execute(sql).fetchone()[0]
        row = {
            'day': day_no,
            'date': day.strftime('%a %d/%m'),
            'created': metrics['created'] - before.get('created', 0),
            'submitted': (metrics['submitted'] - before.get('submitted', 0)
                          + metrics['submitted_from_basket'] - before.get('submitted_from_basket', 0)
                          + metrics['resubmitted'] - before.get('resubmitted', 0)),
            'approved': metrics['approved'] - before.get('approved', 0),
            'reworked': metrics['reworked'] - before.get('reworked', 0),
            'rejected': metrics['rejected'] - before.get('rejected', 0),
            'queue': q("SELECT COUNT(*) FROM report_approvals WHERE approval_status='pending'"),
            'basket': q("SELECT COUNT(*) FROM reports WHERE approval_status='pending_fiu' AND is_deleted=0"),
            'secs': round(time.time() - t_day, 1),
        }
        conn.close()
        daily.append(row)
        print(f"  day {day_no:>2} {row['date']}  filed {row['created']:>4}  "
              f"submitted {row['submitted']:>4}  approved {row['approved']:>4}  "
              f"rework {row['reworked']:>3}  rejected {row['rejected']:>3}  "
              f"| queue {row['queue']:>4}  basket {row['basket']:>4}  ({row['secs']}s)")
        day += timedelta(days=1)

    return report(db, time.time() - wall_start)


def report(db, wall):
    conn = sqlite3.connect(db)
    q = lambda sql: conn.execute(sql).fetchone()[0]

    print("\n" + "=" * 78)
    print("THE FORTNIGHT")
    print("=" * 78)
    total_reports = q("SELECT COUNT(*) FROM reports WHERE is_deleted=0")
    target = DAYS * N_AGENTS * PER_AGENT_PER_DAY
    print(f"  reports filed              {total_reports:>7}   (target {target})")
    print(f"  approved                   {metrics['approved']:>7}")
    print(f"  sent back for rework       {metrics['reworked']:>7}")
    print(f"  rejected                   {metrics['rejected']:>7}")
    print(f"  fixed and resubmitted      {metrics['resubmitted']:>7}")
    print(f"  still waiting for the FIU  {q(chr(34) if False else 'SELECT COUNT(*) FROM reports '
          'WHERE approval_status=\'pending_fiu\' AND is_deleted=0'):>7}")
    print(f"  still in the review queue  {q('SELECT COUNT(*) FROM report_approvals '
          'WHERE approval_status=\'pending\''):>7}")

    print(f"\n  wall clock                 {wall/60:>7.1f} min")
    if create_latency:
        cl = sorted(create_latency)
        print(f"  file a report  median      {statistics.median(cl)*1000:>7.0f} ms")
        print(f"                 p95         {cl[int(len(cl)*0.95)]*1000:>7.0f} ms")
        print(f"  throughput                 {len(cl)/wall:>7.1f} reports/sec")
    if decision_latency:
        print(f"  decision turnaround        {statistics.mean(decision_latency):>7.1f} days avg, "
              f"{max(decision_latency)} worst")

    print("\n" + "-" * 78)
    print("KPIs")
    print("-" * 78)
    filed_ok = total_reports >= target * 0.99
    print(f"  {'PASS' if filed_ok else 'FAIL'}  agents filed their 50 a day "
          f"({total_reports}/{target})")
    decided = metrics['approved'] + metrics['reworked'] + metrics['rejected']
    submitted = metrics['submitted'] + metrics['submitted_from_basket'] + metrics['resubmitted']
    keep_up = decided >= submitted * 0.95
    print(f"  {'PASS' if keep_up else 'FAIL'}  supervisors kept up with the queue "
          f"({decided} decided of {submitted} submitted)")
    last_queue = daily[-1]['queue'] if daily else 0
    week1 = max((d['queue'] for d in daily[:5]), default=0)
    week2 = max((d['queue'] for d in daily[5:]), default=0)
    no_spiral = week2 <= max(week1 * 1.5, 50)
    print(f"  {'PASS' if no_spiral else 'FAIL'}  backlog did not spiral "
          f"(peak week 1 {week1}, week 2 {week2}, end {last_queue})")

    print("\n" + "-" * 78)
    print("INTEGRITY AFTER 2 WEEKS")
    print("-" * 78)
    checks = [
        ("no duplicate report numbers",
         "SELECT COUNT(*)-COUNT(DISTINCT report_number) FROM reports"),
        ("no duplicate serial numbers",
         "SELECT COUNT(*)-COUNT(DISTINCT sn) FROM reports"),
        ("no reserved number spent twice",
         "SELECT COUNT(*) FROM (SELECT used_by_report_id FROM reserved_numbers "
         "WHERE used_by_report_id IS NOT NULL GROUP BY used_by_report_id HAVING COUNT(*)>1)"),
        ("no report in an unknown state",
         "SELECT COUNT(*) FROM reports WHERE approval_status NOT IN "
         "('draft','pending_fiu','pending_approval','approved','rejected','rework')"),
        ("nothing approved without an approver",
         "SELECT COUNT(*) FROM reports r WHERE r.approval_status='approved' AND NOT EXISTS "
         "(SELECT 1 FROM report_approvals a WHERE a.report_id=r.report_id "
         "AND a.approval_status='approved')"),
        ("nobody approved their own report",
         "SELECT COUNT(*) FROM report_approvals a JOIN reports r ON r.report_id=a.report_id "
         "JOIN users u ON u.user_id=a.approver_id "
         "WHERE u.username=r.created_by AND a.approval_status!='pending'"),
        ("no approved report is missing its FIU number",
         "SELECT COUNT(*) FROM reports WHERE approval_status='approved' "
         "AND (fiu_number IS NULL OR TRIM(fiu_number)='')"),
        ("every report has a version",
         "SELECT COUNT(*) FROM reports r WHERE NOT EXISTS "
         "(SELECT 1 FROM report_versions v WHERE v.report_id=r.report_id)"),
        ("no reporter filed anything",
         "SELECT COUNT(*) FROM reports WHERE created_by IN "
         "(SELECT username FROM users WHERE role='reporter')"),
    ]
    bad = 0
    for label, sql in checks:
        got = q(sql)
        print(f"  {'ok  ' if got == 0 else 'FAIL'} {label}: {got}")
        bad += (got != 0)

    # order by the NUMERIC suffix -- the very trap this run exposed in the app
    months = conn.execute(
        "SELECT substr(report_number,1,7), COUNT(*), "
        "MIN(CAST(substr(report_number,9) AS INTEGER)), "
        "MAX(CAST(substr(report_number,9) AS INTEGER)) "
        "FROM reports GROUP BY 1 ORDER BY 1").fetchall()
    print("\n  numbering by month (the fortnight crosses a month end):")
    for m, n, lo, hi in months:
        missing = hi - lo + 1 - n
        print(f"    {m}  {n:>5} reports   {m}/{lo:03d} .. {m}/{hi:03d}"
              f"{'' if not missing else f'   ({missing} MISSING)'}")
        if missing:
            # a hole in a regulator-facing sequence has to be explainable; an
            # unexplained one is a defect, not a footnote
            bad += 1
    conn.close()

    print("\n" + "=" * 78)
    if _errors:
        print(f"PROBLEMS HIT DURING THE FORTNIGHT: {len(_errors)}")
        seen = set()
        for e in _errors:
            key = e.split('—')[0]
            if key in seen:
                continue
            seen.add(key)
            print("  " + e)
    else:
        print("no problems hit during the fortnight")
    print("=" * 78)

    ok = (not bad) and filed_ok and keep_up and no_spiral and not _errors
    print("VERDICT:", "the unit could run on this" if ok else "NOT READY — see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
