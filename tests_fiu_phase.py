"""The pending-FIU phase. Run: python tests_fiu_phase.py

The real working order, per the owner:
  agent files a new report and SAVES it -> it waits in the pending-FIU basket
  -> agent files it on the FIU portal -> agent comes back, types the FIU number
  -> only then can it be submitted, and only then does a supervisor see it.

A report with no FIU details must never reach anyone's approval queue.
"""
import os, sys, tempfile, sqlite3
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
    from services.report_service import ReportService
    from services.report_number_service import ReportNumberService
    from services.activity_service import ActivityService
    from services.version_service import VersionService
    from services.approval_service import ApprovalService
    from services.security_service import SecurityService

    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    for u, r in (('agent1', 'agent'), ('agent2', 'agent'), ('sup1', 'supervisor')):
        conn.execute("INSERT OR IGNORE INTO users (username,password,full_name,role,is_active,"
                     "created_by,must_change_password) VALUES (?,?,?,?,1,'SYSTEM',0)",
                     (u, SecurityService.hash_password('Pass@123'), u.upper(), r))
    conn.commit(); conn.close()

    log = LoggingService(dbm, None, db_logging=False)
    auth = AuthService(dbm, log)
    log.set_auth_service(auth)
    act = ActivityService(dbm, log, auth)
    nums = ReportNumberService(dbm, log, auth)
    reports = ReportService(dbm, log, auth, act)
    vers = VersionService(dbm, log, auth, reports, act)
    appr = ApprovalService(dbm, log, auth, vers, reports, act)
    reports.set_activity_service(act)
    reports.set_report_number_service(nums)
    reports.set_version_service(vers)
    return auth, reports, nums, appr, dbm


def _new_report(auth, reports, nums, user, extra=None):
    auth.authenticate(user, 'Pass@123')
    if nums.get_available_count(user) < 1:
        nums.reserve_block(user, 3)
    data = {'report_date': '01/07/2026', 'reported_entity_name': f'Entity for {user}'}
    if extra:
        data.update(extra)
    return reports.create_report(data)


def test_saving_does_not_submit():
    auth, reports, nums, appr, _ = _setup()
    ok, rid, msg = _new_report(auth, reports, nums, 'agent1')
    check("agent can save a new report", ok, msg)
    rep = reports.get_report(rid)
    check("a saved report waits for FIU details, it is not submitted",
          rep['approval_status'] == reports.STATUS_PENDING_FIU, rep['approval_status'])

    # nothing should be sitting in a supervisor's queue
    auth.authenticate('sup1', 'Pass@123')
    pend = appr.get_pending_approvals() or []
    check("a report with no FIU details never reaches a supervisor",
          not any(p.get('report_id') == rid for p in pend), pend)


def test_cannot_submit_without_fiu_details():
    auth, reports, nums, appr, _ = _setup()
    ok, rid, _ = _new_report(auth, reports, nums, 'agent1')
    ok2, aid, msg = appr.request_approval(rid, 'please review')
    check("submitting without FIU details is refused", not ok2, msg)
    check("the refusal names the FIU details", 'FIU' in (msg or ''), msg)
    check("the refusal points at the basket", 'basket' in (msg or '').lower(), msg)
    rep = reports.get_report(rid)
    check("the refused report is still safely saved in the basket",
          rep['approval_status'] == reports.STATUS_PENDING_FIU, rep['approval_status'])
    check("no approval row was created by the refused submit",
          not any(p.get('report_id') == rid
                  for p in (appr.get_user_approval_requests() or [])))


def test_partial_fiu_details_still_refused():
    auth, reports, nums, appr, _ = _setup()
    ok, rid, _ = _new_report(auth, reports, nums, 'agent1')
    reports.update_report(rid, {'fiu_number': 'FIU-2026-001'})     # date still missing
    ok2, _aid, msg = appr.request_approval(rid, 'half done')
    check("half-filled FIU details are still refused", not ok2, msg)
    check("the refusal names the missing field", 'date' in (msg or '').lower(), msg)


def test_fiu_details_then_submit():
    auth, reports, nums, appr, _ = _setup()
    ok, rid, _ = _new_report(auth, reports, nums, 'agent1')
    # the agent files it on the FIU portal, gets a number, comes back
    okU, msgU = reports.update_report(rid, {'fiu_number': 'FIU-2026-001',
                                            'fiu_date': '05/07/2026'})
    check("an agent can add FIU details to their waiting report", okU, msgU)
    ok2, aid, msg = appr.request_approval(rid, 'filed with the FIU')
    check("with FIU details the report can be submitted", ok2, msg)
    rep = reports.get_report(rid)
    check("submitting moves it out of the basket",
          rep['approval_status'] == 'pending_approval', rep['approval_status'])

    auth.authenticate('sup1', 'Pass@123')
    pend = appr.get_pending_approvals() or []
    check("now the supervisor sees it", any(p.get('report_id') == rid for p in pend))
    target = [p for p in pend if p.get('report_id') == rid][0]
    okA, msgA = appr.approve_report(target['approval_id'], 'checked against the FIU letter')
    check("supervisor can approve it", okA, msgA)


def test_agent_may_fill_fiu_at_drafting_time():
    """The agent's choice: file it with the FIU first and enter everything in
    one sitting, rather than saving and coming back."""
    auth, reports, nums, appr, _ = _setup()
    ok, rid, msg = _new_report(auth, reports, nums, 'agent1',
                               {'fiu_number': 'FIU-2026-777', 'fiu_date': '02/07/2026'})
    check("a report can be saved with its FIU details already filled", ok, msg)
    ok2, _aid, msg2 = appr.request_approval(rid, 'filed and submitted in one go')
    check("and submitted straight away", ok2, msg2)


def test_basket_is_shared():
    """Everyone sees the whole basket -- a report must not sit forgotten because
    the agent who filed it is away."""
    auth, reports, nums, appr, _ = _setup()
    _new_report(auth, reports, nums, 'agent1')
    _new_report(auth, reports, nums, 'agent2')

    for who in ('agent1', 'agent2', 'sup1', 'admin'):
        auth.authenticate(who, 'Admin@1234' if who == 'admin' else 'Pass@123')
        rows, total = reports.get_reports(reports.STATUS_PENDING_FIU, None, None, None, None, 50, 0)
        owners = {r.get('created_by') for r in rows}
        check(f"{who} sees the whole shared basket",
              total >= 2 and {'agent1', 'agent2'} <= owners, (total, owners))


def test_waiting_report_stays_editable():
    """It is the agent's own basket: they must be able to work on it."""
    auth, reports, nums, appr, _ = _setup()
    ok, rid, _ = _new_report(auth, reports, nums, 'agent1')
    okU, msgU = reports.update_report(rid, {'reported_entity_name': 'Corrected Name'})
    check("a waiting report is editable by its author", okU, msgU)
    check("the edit stuck", (reports.get_report(rid) or {}).get('reported_entity_name')
          == 'Corrected Name')
    hist = reports.get_report_history(rid) or []
    check("and the edit is versioned", len(hist) >= 1, len(hist))


def test_admin_reports_skip_the_basket():
    """An admin's own report is auto-approved today; it must not land in a
    basket that is meant for work awaiting a supervisor."""
    auth, reports, nums, appr, _ = _setup()
    auth.authenticate('admin', 'Admin@1234')
    nums.reserve_block('admin', 2)
    ok, rid, msg = reports.create_report({'report_date': '01/07/2026',
                                          'reported_entity_name': 'Admin Entity'})
    check("admin can create a report", ok, msg)
    rep = reports.get_report(rid)
    check("an admin report does not wait in the FIU basket",
          rep['approval_status'] == 'approved', rep['approval_status'])


def test_dialog_exposes_every_required_fiu_field():
    """The form must actually be able to satisfy REQUIRED_FIU_FIELDS.

    fiu_date is a real column and gates submission, but the dialog had no field
    for it -- so through the UI a report could never be submitted at all. This
    walks the REAL dialog and checks every gating field is reachable, and that
    date fields come with a calendar to pick from.
    """
    import asyncio
    import flet as ft
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))

    class FakePage:
        def __init__(self):
            self.overlay = []
            self.snack_bar = None
        def update(self): pass
        def run_task(self, fn, *a): pass

    def walk(control):
        seen, stack = set(), [control]
        while stack:
            c = stack.pop()
            if c is None or id(c) in seen:
                continue
            seen.add(id(c)); yield c
            for attr in ('controls', 'content', 'actions', 'title', 'tabs'):
                v = getattr(c, attr, None)
                if isinstance(v, (list, tuple)):
                    stack.extend(v)
                elif v is not None and 'flet' in str(type(v)):
                    stack.append(v)

    auth, reports, nums, appr, dbm = _setup()
    auth.authenticate('agent1', 'Pass@123')
    nums.reserve_block('agent1', 2)

    class _State:
        pass
    st = _State()
    st.report_service = reports
    st.approval_service = appr
    st.report_number_service = nums
    st.auth_service = auth
    st.db_manager = dbm
    st.current_user = auth.get_current_user()
    st.dropdown_service = None
    st.validation_service = None
    st.logging_service = None
    st.version_service = None
    st.intelligence_service = None

    from dialogs.report_dialog import show_report_dialog
    page = FakePage()
    show_report_dialog(page, st, report_data=None)
    check("the report dialog opens", bool(page.overlay))
    if not page.overlay:
        return
    tree = page.overlay[-1]

    hints = [(getattr(c, 'hint_text', '') or '').lower()
             for c in walk(tree) if isinstance(c, ft.TextField)]
    date_fields = [h for h in hints if 'dd/mm/yyyy' in h]
    check("the form still exposes date fields", len(date_fields) >= 3, hints)

    # every field that gates submission must be reachable in the form
    labels = " ".join(str(getattr(c, 'value', '') or '') for c in walk(tree)
                      if isinstance(c, ft.Text)).lower()
    for field in reports.REQUIRED_FIU_FIELDS:
        pretty = field.replace('fiu_', 'fiu ').replace('_', ' ')
        check(f"the form has a field for {field}", pretty in labels or field in labels,
              f"'{pretty}' not among the form labels")

    # date fields come with a calendar button
    pickers = [c for c in walk(tree)
               if isinstance(c, ft.IconButton) and c.icon == ft.Icons.CALENDAR_MONTH]
    check("date fields offer a calendar to pick from", len(pickers) >= 3, len(pickers))


def test_live_validation_and_hidden_echo_fields():
    """Errors must appear as the analyst types, not only when they hit Save,
    and a field that only echoes a checkbox must not take up screen space."""
    import flet as ft
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))

    class FakePage:
        def __init__(self):
            self.overlay = []
            self.snack_bar = None
        def update(self): pass
        def run_task(self, fn, *a): pass

    def walk(control):
        seen, stack = set(), [control]
        while stack:
            c = stack.pop()
            if c is None or id(c) in seen:
                continue
            seen.add(id(c)); yield c
            for attr in ('controls', 'content', 'actions', 'title', 'tabs'):
                v = getattr(c, attr, None)
                if isinstance(v, (list, tuple)):
                    stack.extend(v)
                elif v is not None and 'flet' in str(type(v)):
                    stack.append(v)

    auth, reports, nums, appr, dbm = _setup()
    from services.validation_service import ValidationService
    from services.logging_service import LoggingService
    auth.authenticate('agent1', 'Pass@123')
    nums.reserve_block('agent1', 2)

    class _State: pass
    st = _State()
    st.report_service = reports; st.approval_service = appr
    st.report_number_service = nums; st.auth_service = auth
    st.db_manager = dbm; st.current_user = auth.get_current_user()
    st.dropdown_service = None
    st.validation_service = ValidationService(dbm, None, auth)
    st.logging_service = None; st.version_service = None
    st.intelligence_service = None

    from dialogs.report_dialog import show_report_dialog
    page = FakePage()
    show_report_dialog(page, st, report_data=None)
    if not page.overlay:
        check("dialog opens for the live-validation check", False)
        return
    tree = page.overlay[-1]

    fields = [c for c in walk(tree) if isinstance(c, ft.TextField)]

    # a field that echoes a checkbox must not be on screen
    echoes = [c for c in fields if getattr(c, 'read_only', False)
              and str(getattr(c, 'value', '')) in ('ID', 'CR', 'Current Account', 'Membership')]
    for c in echoes:
        check(f"the read-only echo field '{c.value}' is hidden",
              not _is_visible(c, tree), c.value)

    # typing an impossible date must flag the field immediately, with no Save
    date_fields = [c for c in fields
                   if 'dd/mm/yyyy' in (getattr(c, 'hint_text', '') or '').lower()]
    check("date fields are present to validate", bool(date_fields))
    flagged = False
    for c in date_fields:
        if not c.on_change:
            continue
        c.value = "31/31/2026"
        c.on_change(None)
        if c.error_text:
            flagged = True
            break
    check("typing an impossible date flags the field live (no Save needed)", flagged)

    # and correcting it clears the error again
    if flagged:
        c.value = "01/07/2026"
        c.on_change(None)
        check("correcting the date clears the live error", not c.error_text, c.error_text)


def _is_visible(control, tree):
    """A control is visible only if it and every ancestor are visible."""
    import flet as ft
    parents = {}
    stack = [tree]
    seen = set()
    while stack:
        c = stack.pop()
        if c is None or id(c) in seen:
            continue
        seen.add(id(c))
        for attr in ('controls', 'content', 'actions', 'title', 'tabs'):
            v = getattr(c, attr, None)
            kids = v if isinstance(v, (list, tuple)) else ([v] if v is not None and 'flet' in str(type(v)) else [])
            for k in kids:
                parents[id(k)] = c
                stack.append(k)
    node = control
    while node is not None:
        if getattr(node, 'visible', True) is False:
            return False
        node = parents.get(id(node))
    return True


if __name__ == "__main__":
    test_saving_does_not_submit()
    test_cannot_submit_without_fiu_details()
    test_partial_fiu_details_still_refused()
    test_fiu_details_then_submit()
    test_agent_may_fill_fiu_at_drafting_time()
    test_basket_is_shared()
    test_waiting_report_stays_editable()
    test_admin_reports_skip_the_basket()
    test_dialog_exposes_every_required_fiu_field()
    test_live_validation_and_hidden_echo_fields()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
