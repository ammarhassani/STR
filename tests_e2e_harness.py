"""
STR Full-Capability E2E + 10-User Stress Harness
Sandbox DB, real service stack per simulated user (mirrors app_state wiring).
"""
import os
import sys
import shutil
import sqlite3
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

REPO = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(SCRATCH, 'sandbox')
DB_PATH = os.path.join(SANDBOX, 'fiu_sandbox.db')
LOG_DIR = os.path.join(SANDBOX, 'logs')
EXPORT_DIR = os.path.join(SANDBOX, 'exports')

sys.path.insert(0, REPO)

# ---------------------------------------------------------------- registry
RESULTS = {}          # feature -> list of (check_name, ok, detail)
RESULTS_LOCK = threading.Lock()

def check(feature, name, ok, detail=''):
    with RESULTS_LOCK:
        RESULTS.setdefault(feature, []).append((name, bool(ok), str(detail)[:200]))
    if not ok:
        print(f"  FAIL [{feature}] {name}: {detail}")

# ---------------------------------------------------------------- sandbox
def build_sandbox():
    if os.path.exists(SANDBOX):
        shutil.rmtree(SANDBOX)
    os.makedirs(LOG_DIR)
    os.makedirs(EXPORT_DIR)
    from database.init_db import initialize_database, validate_database
    from database.migrations import migrate_database
    ok, msg = initialize_database(DB_PATH)
    assert ok, f"init failed: {msg}"
    ok, msg = migrate_database(DB_PATH)
    assert ok, f"migrate failed: {msg}"
    ok2, msg2 = migrate_database(DB_PATH)
    check('16 Database layer', 'migrations idempotent (2nd run no-op)',
          ok2 and 'No migrations needed' in msg2, msg2)
    ok, msg = validate_database(DB_PATH)
    check('16 Database layer', 'fresh DB passes validation', ok, msg)

    # Seed an admin with a proper bcrypt hash (setup wizard normally does this)
    from services.security_service import SecurityService
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO users (username, password, full_name, role, is_active, created_by) "
        "VALUES ('admin', 'x', 'System Admin', 'admin', 1, 'SYSTEM') "
        "ON CONFLICT(username) DO NOTHING")
    conn.execute(
        "UPDATE users SET password = ?, role = 'admin', is_active = 1, "
        "failed_login_attempts = 0 WHERE username = 'admin'",
        (SecurityService.hash_password('Admin@1234'),))
    # Test fixtures: the shipped schema no longer ships demo agent1/reporter1
    # (removed — they were plaintext accounts). Seed them here (plaintext on
    # purpose: several tests exercise the plaintext->bcrypt auto-migration).
    conn.execute("INSERT OR IGNORE INTO users (username,password,full_name,role,is_active,created_by) "
                 "VALUES ('agent1','pass123','Test Agent','agent',1,'SYSTEM'),"
                 "('reporter1','pass123','Test Reporter','reporter',1,'SYSTEM')")
    conn.commit()
    conn.close()

# ---------------------------------------------------------------- client
class Client:
    """One simulated app instance / user session, wired like app_state."""
    def __init__(self, tag):
        from database.db_manager import DatabaseManager
        from services.logging_service import LoggingService
        from services.auth_service import AuthService
        from services.report_service import ReportService
        from services.dashboard_service import DashboardService
        from services.approval_service import ApprovalService
        from services.version_service import VersionService
        from services.dropdown_service import DropdownService
        from services.validation_service import ValidationService
        from services.settings_service import SettingsService
        from services.report_number_service import ReportNumberService
        from services.activity_service import ActivityService
        from services.restore_service import RestoreService

        self.tag = tag
        self.db = DatabaseManager(DB_PATH)
        self.log = LoggingService(self.db, Path(LOG_DIR))
        self.auth = AuthService(self.db, self.log)
        self.settings = SettingsService(self.db, self.auth)
        self.reports = ReportService(self.db, self.log, self.auth)
        self.dashboard = DashboardService(self.db, self.log)
        self.dropdowns = DropdownService(self.db, self.log, self.auth)
        self.validation = ValidationService(self.db, self.log)
        self.numbers = ReportNumberService(self.db, self.log)
        self.activity = ActivityService(self.db, self.log, self.auth)
        self.versions = VersionService(self.db, self.log, self.auth, self.reports, self.activity)
        self.approvals = ApprovalService(self.db, self.log, self.auth, self.versions,
                                         self.reports, self.activity)
        self.reports.set_activity_service(self.activity)
        self.reports.set_report_number_service(self.numbers)
        self.versions.set_activity_service(self.activity)
        self.restore = RestoreService(self.db, self.log)

    def login(self, username, password):
        ok, user, msg = self.auth.authenticate(username, password)
        return ok, user, msg

    def make_report(self, extra=None):
        """Ensure the user owns an available reserved number (reserve a block of
        20 on first use), then create a minimal valid report WITHOUT passing
        report_number/sn — create_report auto-consumes the lowest available
        owned number. Returns (ok, report_id, resv, msg) where resv is the
        {report_number, serial_number} that got consumed, or None on failure."""
        u = self.auth.get_current_user()['username']
        if self.numbers.get_available_count(u) < 1:
            ok, nums, msg = self.numbers.reserve_block(u, 20)
            if not ok:
                return False, None, None, f"reserve: {msg}"
        data = {
            'report_date': datetime.now().strftime('%d/%m/%Y'),
            'reported_entity_name': f'Entity {u} {time.time()}',
            'nationality': 'Saudi Arabian',
            'total_transaction': '1000',
        }
        if extra:
            data.update(extra)
        ok, rid, msg = self.reports.create_report(data)
        resv = None
        if ok:
            rep = self.reports.get_report(rid)
            if rep:
                resv = {'report_number': rep['report_number'], 'serial_number': rep['sn']}
        return ok, rid, resv, msg


# ================================================================ PHASE 1
def phase1():
    F = '01 Auth & sessions'
    c = Client('t-auth')
    ok, user, msg = c.login('admin', 'WRONG')
    check(F, 'wrong password rejected', not ok, msg)
    ok, user, msg = c.login('admin', 'Admin@1234')
    check(F, 'admin bcrypt login', ok and user['role'] == 'admin', msg)
    check(F, 'is_authenticated after login', c.auth.is_authenticated())

    # legacy plaintext auto-migration (agent1 seeded with plaintext 'pass123')
    c2 = Client('t-auth2')
    ok, user, msg = c2.login('agent1', 'pass123')
    check(F, 'legacy plaintext login works', ok, msg)
    row = c2.db.execute_with_retry("SELECT password FROM users WHERE username='agent1'")
    from services.security_service import SecurityService
    check(F, 'plaintext auto-migrated to bcrypt on login',
          SecurityService.is_bcrypt_hash(row[0][0]))
    ok, _, _ = c2.login('agent1', 'pass123')
    check(F, 'login still works post-migration', ok)

    # lockout: 5 bad attempts
    c3 = Client('t-lock')
    for _ in range(5):
        c3.login('reporter1', 'nope')
    ok, _, msg = c3.login('reporter1', 'pass123')
    check(F, 'account locks after 5 failed attempts', not ok, msg)
    uid = c3.db.execute_with_retry("SELECT user_id FROM users WHERE username='reporter1'")[0][0]
    ok, msg = c.auth.unlock_account(uid)
    check(F, 'admin unlock_account', ok, msg)
    ok, _, msg = c3.login('reporter1', 'pass123')
    check(F, 'login works after unlock', ok, msg)

    # user CRUD
    ok, msg = c.auth.create_user('tempuser', 'Temp@1234', 'Temp User', 'agent')
    check(F, 'create_user', ok, msg)
    row = c.db.execute_with_retry("SELECT password FROM users WHERE username='tempuser'")
    check(F, 'create_user stores bcrypt (not plaintext)',
          SecurityService.is_bcrypt_hash(row[0][0]))
    ok, _, msg = Client('t-new').login('tempuser', 'Temp@1234')
    check(F, 'new user can login with hashed pw', ok, msg)
    ok, msg = c.auth.create_user('tempuser', 'x', 'dup', 'agent')
    check(F, 'duplicate username rejected', not ok, msg)
    ok, msg = c.auth.create_user('badrole', 'x', 'x', 'superuser')
    check(F, 'invalid role rejected', not ok, msg)
    users = c.auth.get_all_users()
    check(F, 'get_all_users returns seeded users', len(users) >= 4, len(users))
    tuid = [u for u in users if u['username'] == 'tempuser'][0]['user_id']
    ok, msg = c.auth.update_user(tuid, full_name='Temp Updated', role='reporter')
    check(F, 'update_user', ok, msg)
    ok, msg = c.auth.reset_password(tuid, 'NewPw@1234')
    check(F, 'reset_password', ok, msg)
    ok, _, msg = Client('t-x').login('tempuser', 'NewPw@1234')
    check(F, 'login with reset password', ok, msg)
    ok = c.auth.change_password(tuid, 'Changed@1234')
    check(F, 'change_password', ok)
    ok, _, _ = Client('t-x2').login('tempuser', 'Changed@1234')
    check(F, 'login with changed password', ok)
    ok, msg = c.auth.delete_user(tuid)
    check(F, 'delete_user', ok, msg)
    ok, _, _ = Client('t-x3').login('tempuser', 'Changed@1234')
    check(F, 'deleted user cannot login', not ok)
    c.auth.logout()
    check(F, 'logout clears session', not c.auth.is_authenticated())
    c.login('admin', 'Admin@1234')

    # ------------------------------------------------------------ RBAC
    F = '02 Roles & permissions'
    from utils.permissions import has_permission, get_user_permissions, can_access_route
    check(F, 'admin can delete_report', has_permission('admin', 'delete_report'))
    check(F, 'agent cannot delete_report', not has_permission('agent', 'delete_report'))
    check(F, 'reporter cannot add_report', not has_permission('reporter', 'add_report'))
    check(F, 'agent edits own report',
          has_permission('agent', 'edit_report', resource_owner='a', current_user='a'))
    check(F, "agent cannot edit other's report",
          not has_permission('agent', 'edit_report', resource_owner='a', current_user='b'))
    check(F, 'agent edits ownerless report (arg-swap regression)',
          has_permission('agent', 'edit_report', resource_owner=None, current_user='a'))
    check(F, 'unknown role denied', not has_permission('ghost', 'view_reports'))
    check(F, 'permission matrix consistent across all roles',
          len({frozenset(get_user_permissions(r)) for r in ('admin', 'supervisor', 'agent', 'reporter')}) == 1)
    check(F, 'route guard: reporter blocked from add_report',
          not can_access_route('reporter', 'add_report'))
    check(F, 'route guard: admin panel admin-only',
          can_access_route('admin', 'admin_panel') and not can_access_route('agent', 'admin_panel'))
    agent = Client('t-agent'); agent.login('agent1', 'pass123')
    check(F, 'service-level: agent has add_report', agent.auth.has_permission('add_report'))
    check(F, 'service-level: agent lacks manage_users', not agent.auth.has_permission('manage_users'))

    # ------------------------------------------------------------ numbers (owned-block model)
    F = '03 Report number reservations'
    u = 'agent1'
    ok, nums, msg = agent.numbers.reserve_block(u, 5)
    check(F, 'reserve_block returns N numbers', ok and len(nums) == 5, msg)
    check(F, 'available count reflects reserved block',
          agent.numbers.get_available_count(u) == 5, agent.numbers.get_available_count(u))
    admin2 = Client('t-admin2'); admin2.login('admin', 'Admin@1234')
    ok, nums2, msg = admin2.numbers.reserve_block('admin', 3)
    check(F, 'second user gets disjoint numbers',
          ok and len(nums2) == 3 and not (set(nums) & set(nums2)), msg)
    check(F, 'invalid count rejected', not agent.numbers.reserve_block(u, 0)[0])

    # consume-on-create: create_report (via make_report, no report_number passed)
    # must auto-consume the user's lowest available owned number.
    before_count = agent.numbers.get_available_count(u)
    ok, rid_n, resv_n, msg = agent.make_report()
    check(F, 'create_report consumes an owned number', ok and resv_n, msg)
    check(F, 'available count decrements on consume',
          agent.numbers.get_available_count(u) == before_count - 1,
          agent.numbers.get_available_count(u))
    check(F, 'consumed number matches lowest available',
          resv_n and resv_n['report_number'] == nums[0], (resv_n, nums))

    # transfer_numbers: moves ownership between two users
    avail_before = agent.numbers.get_available_numbers(u)
    to_move = avail_before[0]['report_number']
    ok, msg = agent.numbers.transfer_numbers(u, 'admin', [to_move])
    check(F, 'transfer_numbers moves ownership', ok, msg)
    check(F, 'transferred number leaves sender available list',
          to_move not in [n['report_number'] for n in agent.numbers.get_available_numbers(u)])
    check(F, 'transferred number appears in recipient available list',
          to_move in [n['report_number'] for n in admin2.numbers.get_available_numbers('admin')])
    ok, msg = agent.numbers.transfer_numbers(u, 'admin', ['2099/99/999'])
    check(F, 'transfer of unowned number rejected', not ok, msg)
    ok, msg = agent.numbers.transfer_numbers(u, 'no_such_user', [avail_before[1]['report_number']])
    check(F, 'transfer to unknown user rejected', not ok, msg)

    # uniqueness: report/serial numbers stay unique across owned-block + reports
    dup = agent.reports.create_report({'sn': resv_n['serial_number'],
                                       'report_number': resv_n['report_number'],
                                       'report_date': 'x', 'reported_entity_name': 'x'})
    check(F, 'duplicate report/serial number rejected', not dup[0], dup[2])
    all_nums = agent.numbers.get_available_numbers(u) + admin2.numbers.get_available_numbers('admin')
    rn_list = [n['report_number'] for n in all_nums]
    check(F, 'no duplicate report numbers across owners', len(rn_list) == len(set(rn_list)), rn_list)

    month = agent.numbers.get_active_numbering_month()
    check(F, 'numbering month is the current calendar month (YYYY/MM)',
          month == f"{datetime.now().year}/{datetime.now().month:02d}", month)

    # ------------------------------------------------------------ report CRUD
    F = '04 Report CRUD'
    ok, rid, resv, msg = agent.make_report()
    check(F, 'agent create report', ok and rid, msg)
    ok2, rid2, resv2, msg2 = agent.make_report()
    check(F, 'second create report', ok2, msg2)
    dup = agent.reports.create_report({'sn': resv['serial_number'],
                                       'report_number': resv['report_number'],
                                       'report_date': 'x', 'reported_entity_name': 'x'})
    check(F, 'duplicate report_number rejected', not dup[0], dup[2])
    miss = agent.reports.create_report({'sn': 999999})
    check(F, 'missing required fields rejected', not miss[0], miss[2])
    rep = agent.reports.get_report(rid)
    check(F, 'get_report returns row', rep and rep['report_id'] == rid)
    check(F, 'agent-created report auto-pending',
          rep['approval_status'] == 'pending_approval', rep['approval_status'])
    # An agent's new report is auto-pending, and a report under approval is
    # frozen (BRD 04§4 / 06§14) -- the approver must decide on exactly the text
    # they were shown. Editing only reopens after a rework decision.
    frozen, fmsg = agent.reports.update_report(rid, {'reported_entity_name': 'Sneaky Edit'})
    check(F, 'edit blocked while pending approval', not frozen, fmsg)
    rep = agent.reports.get_report(rid)
    check(F, 'pending report unchanged by the blocked edit',
          rep['reported_entity_name'] != 'Sneaky Edit', rep['reported_entity_name'])

    # Send it back for rework, then the author may edit again.
    sup = Client('t-sup-crud'); sup.login('admin', 'Admin@1234')
    pend = [p for p in (sup.approvals.get_pending_approvals() or [])
            if p.get('report_id') == rid]
    check(F, 'submitted report is in the approval queue', bool(pend))
    if pend:
        rw_ok, rw_msg = sup.approvals.reject_report(pend[0]['approval_id'],
                                                    'please correct the entity name', True)
        check(F, 'rework decision accepted', rw_ok, rw_msg)
    ok, msg = agent.reports.update_report(rid, {'reported_entity_name': 'Updated Entity',
                                                'nationality': 'Egyptian'})
    check(F, 'update_report after rework', ok, msg)
    rep = agent.reports.get_report(rid)
    check(F, 'update persisted', rep['reported_entity_name'] == 'Updated Entity')
    rows, total = agent.reports.get_reports(search_term='Updated Entity')
    check(F, 'search filter finds report', total >= 1 and any(r['report_id'] == rid for r in rows))
    inj = agent.reports.update_report(rid, {'reported_entity_name': 'Updated Entity',
                                            'evil_column': 'DROP TABLE'})
    check(F, 'unknown fields filtered (whitelist)', inj[0], inj[1])
    rows, total = agent.reports.get_reports(created_by='agent1')
    check(F, 'created_by filter', total >= 2, total)
    rows, total = agent.reports.get_reports(limit=1, offset=0)
    check(F, 'pagination limit', len(rows) == 1 and total >= 2, (len(rows), total))
    admin_c = Client('t-admin3'); admin_c.login('admin', 'Admin@1234')
    # pending reports cannot be deleted (business rule); use an admin report
    # which is auto-approved, so it is deletable
    ok, rid_del, _, _ = admin_c.make_report()
    check(F, 'pending report delete blocked', not admin_c.reports.delete_report(rid2)[0],
          'agent report is pending')
    ok, msg = admin_c.reports.delete_report(rid_del)
    check(F, 'soft delete (approved report)', ok, msg)
    check(F, 'deleted count reflects', admin_c.reports.get_deleted_reports_count() >= 1)
    rows, total = agent.reports.get_reports()
    check(F, 'soft-deleted excluded from list', all(r['report_id'] != rid_del for r in rows))
    ok, msg = admin_c.reports.restore_report(rid_del)
    check(F, 'restore soft-deleted', ok, msg)
    impact = admin_c.reports.get_report_impact(rid_del)
    check(F, 'get_report_impact dict', isinstance(impact, dict), impact)
    ok, msg = admin_c.reports.delete_report(rid_del)
    ok, msg = admin_c.reports.hard_delete_report(rid_del, 'e2e cleanup')
    check(F, 'hard delete', ok, msg)
    check(F, 'hard-deleted gone', agent.reports.get_report(rid_del) is None)

    # ------------------------------------------------------------ validation
    F = '05 Field validation'
    v = agent.validation
    check(F, 'required empty fails', not v.validate_field_generic('reported_entity_name', '')[0])
    check(F, 'pattern pass (initials AB)', v.validate_field_generic('reporter_initials', 'AB')[0])
    check(F, 'pattern fail (initials abc)', not v.validate_field_generic('reporter_initials', 'abc')[0])
    check(F, 'numeric amount pass', v.validate_field_generic('total_transaction', '500')[0])
    check(F, 'non-numeric amount fail', not v.validate_field_generic('total_transaction', '500 USD')[0])
    check(F, 'integer type fail', not v.validate_field_generic('fiu_number', 'abc')[0])
    check(F, 'maxLength fail', not v.validate_field_generic('nationality', 'x' * 101)[0])
    check(F, 'optional empty passes', v.validate_field_generic('nationality', '')[0])
    check(F, 'min value fail (sn=0)', not v.validate_field_generic('sn', '0')[0])
    check(F, 'id_cr saudi 10-digit pass', v.validate_field_from_db('id_cr', '1234567890')[0])
    check(F, 'id_cr short fail', not v.validate_field_from_db('id_cr', '123')[0])
    ok, msg = admin_c.validation.update_validation_rules(
        'nationality', {'maxLength': 50}, 'admin')
    check(F, 'admin updates rules', ok, msg)
    check(F, 'updated rule enforced', not v.validate_field_generic('nationality', 'x' * 51)[0])
    ok, msg = admin_c.validation.update_required_status('nationality', True, 'admin')
    check(F, 'toggle required on', ok, msg)
    check(F, 'new required enforced', not v.validate_field_generic('nationality', '')[0])
    admin_c.validation.update_required_status('nationality', False, 'admin')
    settings = v.get_all_field_settings()
    check(F, 'get_all_field_settings covers all fields', len(settings) >= 25, len(settings))

    # ------------------------------------------------------------ versions
    F = '06 Version history'
    ok, vid1, msg = agent.versions.create_version_snapshot(rid, 'first snapshot')
    check(F, 'create snapshot', ok and vid1, msg)
    agent.reports.update_report(rid, {'reported_entity_name': 'V2 Entity'})
    ok, vid2, msg = agent.versions.create_version_snapshot(rid, 'second snapshot')
    check(F, 'second snapshot', ok and vid2, msg)
    versions = agent.versions.get_report_versions(rid)
    check(F, 'list versions', len(versions) >= 2, len(versions))
    snap = agent.versions.get_version_snapshot(vid1)
    check(F, 'fetch snapshot payload', snap is not None)
    cmp_ = agent.versions.compare_versions_detailed(vid1, vid2)
    check(F, 'detailed diff detects change',
          cmp_ and 'reported_entity_name' in cmp_.get('differences', {}),
          list(cmp_.get('differences', {})) if cmp_ else cmp_)
    ok, msg = agent.versions.restore_version(vid1, 'e2e restore')
    check(F, 'non-admin version restore denied', not ok, msg)
    ok, msg = admin_c.versions.restore_version(vid1, 'e2e restore')
    check(F, 'admin restores old version', ok, msg)
    rep = agent.reports.get_report(rid)
    check(F, 'restore reverted field', rep['reported_entity_name'] == 'Updated Entity',
          rep['reported_entity_name'])
    n = agent.versions.get_version_count(rid)
    check(F, 'version count', n >= 2, n)
    ok, msg = admin_c.versions.soft_delete_version(vid1, 'cleanup')
    check(F, 'soft delete version', ok, msg)
    ok, msg = admin_c.versions.restore_deleted_version(vid1)
    check(F, 'restore deleted version', ok, msg)

    # ------------------------------------------------------------ approvals
    F = '07 Approval workflow'
    ok, rid3, _, msg = agent.make_report()
    check(F, 'setup report for approval', ok, msg)
    rep = agent.reports.get_report(rid3)
    check(F, 'agent create auto-submits (pending_approval)',
          rep['approval_status'] == 'pending_approval', rep['approval_status'])
    ok, _, msg = agent.approvals.request_approval(rid3, 'again')
    check(F, 'double-submit blocked', not ok and 'pending' in msg.lower(), msg)
    pend = admin_c.approvals.get_pending_approvals()
    mine = [p for p in pend if p['report_id'] == rid3]
    check(F, 'admin sees pending queue', len(mine) == 1, len(pend))
    appr_id = mine[0]['approval_id'] if mine else None
    ok, msg = admin_c.approvals.approve_report(appr_id, 'looks good')
    check(F, 'admin approves', ok, msg)
    rep = agent.reports.get_report(rid3)
    check(F, 'status -> approved', rep['approval_status'] == 'approved', rep['approval_status'])
    # reject + rework path
    ok, rid4, _, msg = agent.make_report()
    pend = admin_c.approvals.get_pending_approvals()
    appr2 = [p for p in pend if p['report_id'] == rid4][0]['approval_id']
    ok, msg = admin_c.approvals.reject_report(appr2, 'fix entity name', request_rework=True)
    check(F, 'admin requests rework', ok, msg)
    rep = agent.reports.get_report(rid4)
    check(F, 'status -> rework', rep['approval_status'] == 'rework', rep['approval_status'])
    ok, appr3, msg = agent.approvals.request_approval(rid4, 'fixed')
    check(F, 'resubmit after rework', ok and appr3, msg)
    ok, msg = admin_c.approvals.reject_report(appr3, 'still wrong', request_rework=False)
    check(F, 'hard reject', ok, msg)
    rep = agent.reports.get_report(rid4)
    check(F, 'status -> rejected', rep['approval_status'] == 'rejected', rep['approval_status'])
    # admin-created reports skip workflow
    ok, rid5, _, msg = admin_c.make_report()
    rep = admin_c.reports.get_report(rid5)
    check(F, 'admin-created report auto-approved', rep['approval_status'] == 'approved',
          rep['approval_status'])
    allap, total = admin_c.approvals.get_all_approvals()
    check(F, 'approvals audit list', total >= 3, total)
    # notifications
    agent_uid = agent.auth.get_current_user()['user_id']
    notifs = agent.approvals.get_user_notifications(agent_uid)
    check(F, 'agent notified of decisions', len(notifs) >= 1, len(notifs))
    unread = agent.approvals.get_unread_notification_count(agent_uid)
    check(F, 'unread count > 0', unread >= 1, unread)
    if notifs:
        ok, msg = agent.approvals.mark_notification_read(notifs[0]['notification_id'])
        check(F, 'mark notification read', ok, msg)
        check(F, 'unread count decremented',
              agent.approvals.get_unread_notification_count(agent_uid) == unread - 1)

    # ------------------------------------------------------------ dropdowns
    F = '08 Dropdown management'
    cats = admin_c.dropdowns.get_all_categories()
    check(F, 'categories present', len(cats) >= 8, len(cats))
    ok, msg = admin_c.dropdowns.add_dropdown_value('report_source', 'E2E Source', 'admin')
    check(F, 'add value', ok, msg)
    vals = admin_c.dropdowns.get_all_dropdown_values('report_source')
    new = [x for x in vals if x['value'] == 'E2E Source']
    check(F, 'added value listed', len(new) == 1)
    cid = new[0]['config_id']
    ok, msg = admin_c.dropdowns.update_dropdown_value(cid, 'E2E Source v2', 'admin')
    check(F, 'update value', ok, msg)
    ok, msg = admin_c.dropdowns.delete_dropdown_value(cid, 'admin')
    check(F, 'delete (deactivate) value', ok, msg)
    check(F, 'deleted not in active list',
          'E2E Source v2' not in admin_c.dropdowns.get_active_dropdown_values('report_source'))
    ok, msg = admin_c.dropdowns.restore_dropdown_value(cid, 'admin')
    check(F, 'restore value', ok, msg)
    ids = [x['config_id'] for x in admin_c.dropdowns.get_all_dropdown_values('report_source')]
    ok, msg = admin_c.dropdowns.reorder_dropdown_values('report_source', list(reversed(ids)), 'admin')
    check(F, 'reorder values', ok, msg)
    ok, msg = admin_c.dropdowns.bulk_import_dropdown_values(
        'fiu_feedback', ['Bulk A', 'Bulk B'], 'admin')
    check(F, 'bulk import', ok, msg)
    check(F, 'arb_staff admin-manageable (screenshot regression)',
          admin_c.dropdowns.is_category_admin_manageable('arb_staff'))
    admin_c.dropdowns.delete_dropdown_value(cid, 'admin')

    # ------------------------------------------------------------ settings
    F = '09 Settings'
    s = admin_c.settings
    check(F, 'save global setting', s.save_setting('rows_per_page', 50))
    check(F, 'read back', s.get_setting('rows_per_page') in (50, '50'), s.get_setting('rows_per_page'))
    check(F, 'set theme', s.set_theme('dark'))
    check(F, 'get theme', s.get_theme() == 'dark', s.get_theme())
    auid = admin_c.auth.get_current_user()['user_id']
    check(F, 'per-user setting isolated', s.save_setting('toast_duration', 9, user_id=auid))
    allset = s.get_all_settings(user_id=auid)
    check(F, 'get_all_settings dict', isinstance(allset, dict) and allset, len(allset))
    check(F, 'session timeout default int', isinstance(s.get_session_timeout(), int))
    check(F, 'reset_to_defaults', s.reset_to_defaults(user_id=auid))

    # ------------------------------------------------------------ dashboard
    F = '10 Dashboard & analytics'
    d = admin_c.dashboard
    stats = d.get_summary_statistics()
    actual_total = admin_c.db.execute_with_retry(
        "SELECT COUNT(*) FROM reports WHERE is_deleted=0")[0][0]
    check(F, 'summary totals match DB', stats.get('total_reports') == actual_total,
          (stats.get('total_reports'), actual_total))
    check(F, 'approved KPI matches', stats.get('closed_cases') ==
          admin_c.db.execute_with_retry(
              "SELECT COUNT(*) FROM reports WHERE approval_status='approved' AND is_deleted=0")[0][0])
    bys = d.get_reports_by_status()
    check(F, 'by-status uses approval labels',
          bys and all(x['status'] in ('Draft', 'Pending Approval', 'Approved', 'Rejected', 'Rework', 'Unknown')
                      for x in bys), bys)
    bym = d.get_reports_by_month(12)
    check(F, 'by-month returns current month', any(x for x in bym), bym[:2])
    top = d.get_top_reporters(5)
    check(F, 'top reporters listed', isinstance(top, list) and top, top[:2])
    widgets = d.get_dashboard_widgets('admin')
    check(F, 'stored widgets load', isinstance(widgets, list) and len(widgets) >= 4, len(widgets))
    bad = [w for w in widgets if 'status' in (w.get('sql_query') or '')
           and 'approval_status' not in (w.get('sql_query') or '')]
    check(F, 'no widget references dropped status column', not bad, bad)

    # ------------------------------------------------------------ activity
    F = '11 Activity log'
    a = agent.activity
    ok = a.log_activity(action_type='CREATE', description='e2e probe activity', report_id=rid)
    check(F, 'log_activity', ok is not False)
    rec, rec_total = a.get_recent_activities(limit=10)
    check(F, 'recent activities returned', isinstance(rec, list) and rec and rec_total >= len(rec),
          (len(rec), rec_total))
    repacts = a.get_report_activities(rid)
    check(F, 'per-report activities', isinstance(repacts, list) and repacts, len(repacts))
    uacts = a.get_user_activities(agent_uid)
    check(F, 'per-user activities', isinstance(uacts, list), len(uacts))
    summ = a.get_activity_summary(7)
    check(F, 'activity summary dict', isinstance(summ, dict) and summ, list(summ)[:3])
    ok, n, msg = admin_c.activity.delete_old_activities(days_to_keep=365)
    check(F, 'cleanup old activities', ok, msg)

    # ------------------------------------------------------------ logging
    F = '12 System logging'
    admin_c.log.info('e2e log probe info')
    admin_c.log.error('e2e log probe error')
    logs = admin_c.log.get_logs(limit=50)
    text = str(logs)
    check(F, 'logs written and readable', 'e2e log probe' in text, len(logs) if isinstance(logs, list) else type(logs))
    st = admin_c.log.get_log_statistics()
    check(F, 'log statistics', isinstance(st, dict) and st, list(st)[:3])
    logf = os.path.join(EXPORT_DIR, 'logs_export.txt')
    n_exported = admin_c.log.export_logs_to_file(logf)
    check(F, 'export logs to file', n_exported > 0 and os.path.exists(logf), n_exported)
    n = admin_c.log.clear_logs(older_than_days=365)
    check(F, 'clear old logs runs', isinstance(n, int), n)

    # ------------------------------------------------------------ security utils
    F = '13 Security utilities'
    from services.security_service import SecurityService as S
    h = S.hash_password('Str0ng!Pass')
    check(F, 'bcrypt hash+verify', S.verify_password('Str0ng!Pass', h))
    check(F, 'verify rejects wrong', not S.verify_password('other', h))
    check(F, 'is_bcrypt_hash detects', S.is_bcrypt_hash(h) and not S.is_bcrypt_hash('plain'))
    score, label = S.check_password_strength('weak')
    score2, label2 = S.check_password_strength('V3ry$trongPassw0rd!')
    check(F, 'strength scoring ordered', score2 > score, (score, score2))
    check(F, 'sanitize_input strips control chars',
          S.sanitize_input('a\x00b<script>') != 'a\x00b<script>')
    check(F, 'sanitize_filename', '/' not in S.sanitize_filename('../../etc/passwd'))
    check(F, 'LIKE pattern escaped', '%' not in S.sanitize_sql_like_pattern('50%')
          or '\\%' in S.sanitize_sql_like_pattern('50%'))
    check(F, 'constant_time_compare', S.constant_time_compare('abc', 'abc')
          and not S.constant_time_compare('abc', 'abd'))
    check(F, 'audit hash stable', S.hash_for_audit('x') == S.hash_for_audit('x'))

    # ------------------------------------------------------------ export
    F = '14 xlsx export'
    from utils.export import export_reports
    from utils.xlsx_writer import read_xlsx_rows
    path = export_reports(admin_c.db, filters=None, output_dir=EXPORT_DIR)
    check(F, 'full export file created', path and os.path.exists(path), path)
    check(F, 'export is an xlsx file', str(path).endswith('.xlsx'), path)
    if path and os.path.exists(path):
        rows = len(read_xlsx_rows(path)) - 1
        check(F, 'row count matches non-deleted reports', rows == actual_total, (rows, actual_total))
    path2 = export_reports(admin_c.db, filters={'status': 'approved'}, output_dir=EXPORT_DIR)
    if path2 and os.path.exists(path2):
        rows2 = len(read_xlsx_rows(path2)) - 1
        approved = admin_c.db.execute_with_retry(
            "SELECT COUNT(*) FROM reports WHERE approval_status='approved' AND is_deleted=0")[0][0]
        check(F, 'status-filtered export (approval_status)', rows2 == approved, (rows2, approved))
    path3 = export_reports(admin_c.db, filters={'search_term': 'ZZZ_NO_MATCH'}, output_dir=EXPORT_DIR)
    if path3 and os.path.exists(path3):
        rows3 = len(read_xlsx_rows(path3)) - 1
        check(F, 'no-match export empty', rows3 == 0, rows3)

    # ------------------------------------------------------------ restore svc
    F = '15 Deleted-report restore'
    ok, rid6, _, _ = admin_c.make_report()
    ok, rid7, _, _ = admin_c.make_report()
    admin_c.reports.delete_report(rid6)
    admin_c.reports.delete_report(rid7)
    ok, msg = admin_c.restore.restore_report(rid6, 'admin', 'e2e single restore')
    check(F, 'audited single restore', ok, msg)
    check(F, 'restored visible again',
          admin_c.reports.get_report(rid6) and admin_c.reports.get_report(rid6)['is_deleted'] == 0)
    okn, failn, msg = admin_c.restore.bulk_restore_reports([rid7], 'admin', 'e2e bulk')
    check(F, 'bulk restore', okn == 1 and failn == 0, msg)
    hist = admin_c.restore.get_restore_history(limit=10)
    check(F, 'restore history recorded', len(hist) >= 2, len(hist))
    stats = admin_c.restore.get_restore_stats()
    check(F, 'restore stats', isinstance(stats, dict) and stats, list(stats)[:3])
    if hist:
        det = admin_c.restore.get_restore_details(hist[0].get('restore_number'))
        check(F, 'restore details by number', det is not None)

    # ------------------------------------------------------------ db layer
    F = '16 Database layer'
    conn = sqlite3.connect(DB_PATH)
    mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
    conn.close()
    check(F, 'WAL mode active', str(mode).lower() == 'wal', mode)
    fk = admin_c.db.execute_with_retry('SELECT 1')
    check(F, 'execute_with_retry basic read', fk and fk[0][0] == 1, fk)
    return agent, admin_c


# ================================================================ PHASE 2
def phase2_stress():
    """10 concurrent users, mixed realistic workload."""
    F = '17 Concurrency stress (10 users)'
    print('\n--- STRESS PHASE: 10 concurrent users ---')

    # provision users: admin + 6 agents + 3 reporters
    boss = Client('boss'); boss.login('admin', 'Admin@1234')
    for i in range(2, 8):
        boss.auth.create_user(f'agent{i}', 'pass123', f'Agent {i}', 'agent')
    for i in range(2, 4):
        boss.auth.create_user(f'reporter{i}', 'pass123', f'Reporter {i}', 'reporter')

    errors = []
    err_lock = threading.Lock()
    created_ids = []
    created_lock = threading.Lock()
    submitted = []
    sub_lock = threading.Lock()
    op_counts = {'create': 0, 'update': 0, 'submit': 0, 'resubmit': 0, 'decide': 0, 'read': 0}
    op_lock = threading.Lock()
    latencies = []

    barrier = threading.Barrier(10)
    STOP = time.time() + 60          # ~1 minute of sustained load
    REPORTS_PER_AGENT = 12

    def record(kind):
        with op_lock:
            op_counts[kind] += 1

    def agent_worker(username):
        try:
            c = Client(username)
            ok, _, msg = c.login(username, 'pass123')
            if not ok:
                raise RuntimeError(f'login failed: {msg}')
            barrier.wait()
            for i in range(REPORTS_PER_AGENT):
                t0 = time.time()
                ok, rid, resv, msg = c.make_report()
                latencies.append(time.time() - t0)
                if not ok:
                    raise RuntimeError(f'create failed: {msg}')
                record('create')
                with created_lock:
                    created_ids.append(rid)
                # A fresh agent report is auto-submitted and therefore frozen
                # (BRD 04§4), so the realistic edit load is the rework loop:
                # fix up whatever a reviewer sent back, then resubmit it.
                # Reviewers are deciding concurrently, so only assert the freeze
                # while the report is genuinely still pending -- an approved
                # report is legitimately editable (it just stays approved).
                snap = c.reports.get_report(rid) or {}
                blocked, _ = c.reports.update_report(
                    rid, {'reported_entity_name': f'{username} frozen {i}'})
                if blocked and snap.get('approval_status') == 'pending_approval':
                    after = c.reports.get_report(rid) or {}
                    if after.get('approval_status') == 'pending_approval':
                        raise RuntimeError('a pending report was editable')
                rows, _ = c.reports.get_reports(created_by=username, limit=50)
                for r in [x for x in rows if x.get('approval_status') == 'rework'][:2]:
                    ok, msg = c.reports.update_report(
                        r['report_id'], {'reported_entity_name': f'{username} reworked {i}'})
                    if not ok:
                        raise RuntimeError(f'rework edit failed: {msg}')
                    record('update')
                    ok, _, msg = c.approvals.request_approval(r['report_id'], 'reworked')
                    if ok:
                        record('resubmit')
                # creation auto-submits; count it
                record('submit')
                with sub_lock:
                    submitted.append(rid)
        except Exception as e:
            with err_lock:
                errors.append(f'{username}: {e}\n{traceback.format_exc()}')

    def admin_worker():
        try:
            c = Client('boss-w')
            c.login('admin', 'Admin@1234')
            barrier.wait()
            flip = True
            while time.time() < STOP:
                pend = c.approvals.get_pending_approvals()
                for p in pend[:5]:
                    if flip:
                        ok, msg = c.approvals.approve_report(p['approval_id'], 'stress ok')
                    else:
                        ok, msg = c.approvals.reject_report(p['approval_id'], 'stress no',
                                                            request_rework=False)
                    if ok:
                        record('decide')
                    flip = not flip
                # admin also churns dropdowns + settings
                c.dropdowns.add_dropdown_value('fiu_feedback', f'stress {time.time()}', 'admin')
                c.settings.save_setting('rows_per_page', 25)
                time.sleep(0.05)
        except Exception as e:
            with err_lock:
                errors.append(f'admin: {e}\n{traceback.format_exc()}')

    def reporter_worker(username):
        try:
            c = Client(username)
            ok, _, msg = c.login(username, 'pass123')
            if not ok:
                raise RuntimeError(f'login failed: {msg}')
            barrier.wait()
            from utils.export import export_reports
            while time.time() < STOP:
                c.reports.get_reports(limit=20)
                c.dashboard.get_summary_statistics()
                c.dashboard.get_reports_by_status()
                c.activity.get_recent_activities(limit=20)
                record('read')
                if username == 'reporter1':
                    export_reports(c.db, output_dir=EXPORT_DIR)
                time.sleep(0.02)
        except Exception as e:
            with err_lock:
                errors.append(f'{username}: {e}\n{traceback.format_exc()}')

    threads = [threading.Thread(target=admin_worker)]
    threads += [threading.Thread(target=agent_worker, args=(f'agent{i}',)) for i in range(1, 8)][:6]
    threads += [threading.Thread(target=reporter_worker, args=(f'reporter{i}',)) for i in range(1, 4)]
    assert len(threads) == 10, len(threads)

    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=240)
    dur = time.time() - t0

    alive = [t for t in threads if t.is_alive()]
    check(F, 'all 10 workers finished (no deadlock)', not alive, f'{len(alive)} still alive')
    check(F, 'zero worker errors', not errors, errors[:2])

    # ---- invariants
    db = boss.db
    dup_sn = db.execute_with_retry(
        'SELECT sn, COUNT(*) c FROM reports GROUP BY sn HAVING c > 1')
    check(F, 'serial numbers unique under contention', not dup_sn, dup_sn[:3])
    dup_rn = db.execute_with_retry(
        'SELECT report_number, COUNT(*) c FROM reports GROUP BY report_number HAVING c > 1')
    check(F, 'report numbers unique under contention', not dup_rn, dup_rn[:3])
    n_created = db.execute_with_retry(
        "SELECT COUNT(*) FROM reports WHERE created_by LIKE 'agent%'")[0][0]
    check(F, f'all {6 * REPORTS_PER_AGENT} agent reports created', n_created >= 6 * REPORTS_PER_AGENT,
          n_created)
    orphans = db.execute_with_retry("""
        SELECT COUNT(*) FROM reports
        WHERE approval_status NOT IN ('draft','pending_approval','approved','rejected','rework')
    """)[0][0]
    check(F, 'no report in invalid approval state', orphans == 0, orphans)
    decided = db.execute_with_retry("""
        SELECT COUNT(*) FROM report_approvals WHERE approval_status IN ('approved','rejected')
    """)[0][0]
    check(F, 'admin decisions recorded', decided >= 1, decided)
    vcount = db.execute_with_retry('SELECT COUNT(*) FROM report_versions')[0][0]
    check(F, 'version snapshots persisted', vcount >= 6 * REPORTS_PER_AGENT, vcount)
    acount = db.execute_with_retry('SELECT COUNT(*) FROM activity_log')[0][0] \
        if db.execute_with_retry("SELECT name FROM sqlite_master WHERE name='activity_log'") else 0
    _c = sqlite3.connect(DB_PATH)
    integ = _c.execute('PRAGMA integrity_check').fetchone()[0]
    _c.close()
    check(F, 'sqlite integrity_check ok', integ == 'ok', integ)

    ops = sum(op_counts.values())
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    print(f'\nstress: {ops} ops in {dur:.1f}s ({ops / dur:.1f} ops/s), '
          f'creates p95 {p95 * 1000:.0f}ms, ops={op_counts}')
    check(F, 'throughput sane (>5 ops/s sustained)', ops / dur > 5, f'{ops / dur:.1f}')
    check(F, 'create p95 under 2s', p95 < 2.0, f'{p95:.2f}s')
    return op_counts, dur, p95


# ================================================================ report
def final_report():
    print('\n' + '=' * 72)
    print('FEATURE VIABILITY SCORECARD')
    print('=' * 72)
    total_pass = total_all = 0
    for feat in sorted(RESULTS):
        rows = RESULTS[feat]
        npass = sum(1 for _, ok, _ in rows if ok)
        total_pass += npass
        total_all += len(rows)
        score = round(10 * npass / len(rows), 1)
        flag = 'OK ' if npass == len(rows) else '!! '
        print(f'{flag}{feat:<38} {npass:>3}/{len(rows):<3} checks  -> {score}/10')
        for name, ok, detail in rows:
            if not ok:
                print(f'      FAIL: {name} — {detail}')
    print('-' * 72)
    print(f'TOTAL: {total_pass}/{total_all} checks passed')
    return total_pass, total_all


if __name__ == '__main__':
    print('building sandbox...')
    build_sandbox()
    print('phase 1: functional E2E...')
    phase1()
    print('phase 2: 10-user stress...')
    phase2_stress()
    p, t = final_report()
    sys.exit(0 if p == t else 1)
