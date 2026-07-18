"""END-TO-END DEPLOYMENT SIMULATION (no VMs, no manual clicks).

Walks the ENTIRE deployment lifecycle the way it runs on real machines, but with
each "PC" as a directory and the "SMB share" as a temp folder, driving the REAL
code paths (HostService, QueueTransport, RemoteGateway, replica sync, outbox,
failover, updater, hard reset). One command proves the whole journey:

  host bring-up -> client join -> onboarding handshake -> client write via host
  -> second client sees it -> host offline (outbox queue) -> failover (become
  host) -> self-update from the share -> hard reset.

Run: python3.14 tests_e2e_deployment.py

This covers the machinery. The bits it CANNOT simulate (they need a real Windows
box) are called out at the end and in docs/E2E-TEST-PLAN.md: the GUI itself, the
windowless .vbs launch, the Windows taskbar icon, and a genuine SMB filesystem.
"""
import os, sys, time, shutil, tempfile, threading, uuid, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
_phase = ""
def phase(name):
    global _phase
    _phase = name
    print(f"\n=== {name} ===")
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("  PASS " if ok else "  FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


# ---------------------------------------------------------------- host builder
def _build_services(db, bus):
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.settings_service import SettingsService
    from services.report_service import ReportService
    from services.dashboard_service import DashboardService
    from services.dropdown_service import DropdownService
    from services.validation_service import ValidationService
    from services.report_number_service import ReportNumberService
    from services.activity_service import ActivityService
    from services.version_service import VersionService
    from services.approval_service import ApprovalService
    from services.queue_transport import QueueTransport
    from host.host_service import HostService
    from pathlib import Path
    dbm = DatabaseManager(db)
    log = LoggingService(dbm, Path(os.path.join(os.path.dirname(db), "logs")))
    auth = AuthService(dbm, log); settings = SettingsService(dbm, auth)
    reports = ReportService(dbm, log, auth); dash = DashboardService(dbm, log, auth)
    dd = DropdownService(dbm, log, auth); val = ValidationService(dbm, log)
    nums = ReportNumberService(dbm, log); act = ActivityService(dbm, log, auth)
    reports.set_activity_service(act); reports.set_report_number_service(nums)
    ver = VersionService(dbm, log, auth, reports, act)
    appr = ApprovalService(dbm, log, auth, ver, reports, act); ver.set_activity_service(act)
    services = {'auth_service': auth, 'settings_service': settings, 'report_service': reports,
                'dashboard_service': dash, 'dropdown_service': dd, 'validation_service': val,
                'report_number_service': nums, 'activity_service': act, 'version_service': ver,
                'approval_service': appr}
    host = HostService(services, dbm, QueueTransport(bus), bus, host_id="host-" + uuid.uuid4().hex[:6])
    return host, dbm


def _seed_admin(db):
    from services.security_service import SecurityService
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin','x','Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO NOTHING")
    c.execute("UPDATE users SET password=?, role='admin', is_active=1, onboarding_pending=0 WHERE username='admin'",
              (SecurityService.hash_password('Admin@1234'),))
    c.commit(); c.close()


class _Pump:
    """Runs a host's command loop in a background thread — like the host PC
    serving continuously. Pause() simulates the host going offline."""
    def __init__(self, host):
        self.host = host; self._run = True; self._paused = False
        self.t = threading.Thread(target=self._loop, daemon=True); self.t.start()
    def _loop(self):
        while self._run:
            if self._paused or not self.host.run_once():
                time.sleep(0.02)
    def pause(self): self._paused = True
    def resume(self): self._paused = False
    def stop(self): self._run = False; self.t.join(timeout=2)


def run():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, HostOfflineError
    from services.outbox import Outbox
    from services.replica_sync import bootstrap_replica

    root = tempfile.mkdtemp(prefix="str_deploy_")
    share = os.path.join(root, "share"); os.makedirs(share)          # the "SMB share"
    bus = os.path.join(share, "str_bus")
    host_db = os.path.join(root, "host", "local.db"); os.makedirs(os.path.dirname(host_db))

    # ---- P1 host bring-up (first PC designated Host)
    phase("P1 Host bring-up (init DB, publish replica + heartbeat)")
    initialize_database(host_db); migrate_database(host_db); _seed_admin(host_db)
    host, host_dbm = _build_services(host_db, bus)
    host.startup()
    pump = _Pump(host)
    check("replica published to the share", os.path.exists(os.path.join(bus, "replica", "fiu_ro.db")))
    check("heartbeat published", os.path.exists(os.path.join(bus, "host", "heartbeat.json")))

    # ---- P2 client A joins (bootstrap the read replica off the share)
    phase("P2 Client A joins (bootstrap replica, read shared data)")
    cA_db = os.path.join(root, "clientA", "replica.db"); os.makedirs(os.path.dirname(cA_db))
    ok = bootstrap_replica(bus, cA_db, timeout=10)
    check("client A bootstrapped a local replica", ok and os.path.exists(cA_db))
    from database.db_manager import DatabaseManager
    from services.dropdown_service import DropdownService
    cA_read = DropdownService(DatabaseManager(cA_db), None)
    gvals = dict(cA_read.get_active_options('gender', 'ar'))
    check("client reads localized dropdowns from the replica", gvals.get('Male') == 'ذكر', gvals)

    # ---- P3 onboarding handshake through the host (admin ID -> user self-registers)
    phase("P3 Two-way onboarding handshake via the host")
    gwA = RemoteGateway(QueueTransport(bus))
    ok, _u, _m = gwA.login('admin', 'Admin@1234')
    check("admin logs in via the host", ok, _m)
    r = host.handle_command({'id': uuid.uuid4().hex, 'command': 'auth_service.create_pending_user',
                             'args': ['agentA', 'agent'], 'kwargs': {}, 'token': gwA.token})
    check("admin creates a pending user ID via host", r['ok'] and r['result'][0], r)
    r2 = host.handle_command({'id': uuid.uuid4().hex, 'command': 'complete_onboarding',
                              'args': ['agentA', 'Agent A', 'StrongPass123'], 'kwargs': {}})
    check("user self-registers name+password (pre-auth)", r2['ok'] and r2['result'][0], r2)
    okA, uA, _ = gwA.login('agentA', 'StrongPass123')
    check("onboarded agent logs in via host", okA and uA['role'] == 'agent', uA)

    # ---- P4 client A writes through the host (reserve + create a report)
    phase("P4 Client A creates a report (write routed to the host)")
    rr = host.handle_command({'id': uuid.uuid4().hex, 'command': 'report_number_service.reserve_block',
                              'args': ['agentA', 2], 'kwargs': {}, 'token': gwA.token})
    check("agent reserves a number block via host", rr['ok'] and rr['result'][0], rr)
    cr = host.handle_command({'id': uuid.uuid4().hex, 'command': 'report_service.create_report',
                              'args': [{'report_date': '01/07/2026', 'reported_entity_name': 'Acme Co',
                                        'nationality': 'Saudi Arabian', 'total_transaction': '1000'}],
                              'kwargs': {}, 'token': gwA.token})
    check("agent creates a report via host", cr['ok'] and cr['result'][0], cr)
    host.publish_replica()
    bootstrap_replica(bus, cA_db, timeout=10)
    n = DatabaseManager(cA_db).execute_with_retry("SELECT COUNT(*) FROM reports WHERE reported_entity_name='Acme Co'")[0][0]
    check("client A sees the new report in the refreshed replica", n == 1, n)

    # ---- P5 second client sees the SAME shared data
    phase("P5 Client B joins and sees the shared report")
    cB_db = os.path.join(root, "clientB", "replica.db"); os.makedirs(os.path.dirname(cB_db))
    bootstrap_replica(bus, cB_db, timeout=10)
    n = DatabaseManager(cB_db).execute_with_retry("SELECT COUNT(*) FROM reports WHERE reported_entity_name='Acme Co'")[0][0]
    check("client B sees the report created by client A", n == 1, n)

    # ---- P6 host offline -> client queues the write in its outbox, drains later
    phase("P6 Host offline -> outbox queues the write, drains when host returns")
    pump.pause()
    outbox = Outbox(os.path.join(root, "clientA", "outbox"))
    gwA_ob = RemoteGateway(QueueTransport(bus), timeout=1.0, outbox=outbox)
    gwA_ob.token = gwA.token
    queued = False
    try:
        gwA_ob.call("report_number_service.reserve_block", ["agentA", 1], {})
    except HostOfflineError:
        queued = True
    check("write queued while host offline", queued and len(outbox.pending()) == 1, outbox.pending())
    pump.resume()
    time.sleep(0.1)
    drained, kept = gwA_ob.drain()
    check("outbox drained to the host when it returned", drained >= 1 and not outbox.pending(), (drained, outbox.pending()))

    # ---- P7 failover: host down -> client B becomes the new host (term bump)
    phase("P7 Failover — promote Client B to host")
    pump.stop()
    from host.failover import become_host
    from host.lease import read_lease
    old_term = read_lease(host_dbm)[1]
    newhost_db = os.path.join(root, "clientB", "promoted.db")
    # operator confirms the host is down, then promotes (force overrides the
    # fresh-heartbeat guard that otherwise prevents split-brain). Admin + all
    # data ride in the adopted replica — no re-seed needed.
    okp, msgp, _ = become_host(bus, newhost_db, host_id="hostB-" + uuid.uuid4().hex[:6], force=True)
    check("operator promotes client B to host", okp, msgp)
    host2, host2_dbm = _build_services(newhost_db, bus)
    new_term = read_lease(host2_dbm)[1]
    check("failover bumped the term (no split-brain)", new_term > old_term, (old_term, new_term))
    pump2 = _Pump(host2)
    host2.startup()
    gwC = RemoteGateway(QueueTransport(bus)); okc, _u, _m = gwC.login('admin', 'Admin@1234')
    check("clients log in against the NEW host", okc, _m)
    rc = host2.handle_command({'id': uuid.uuid4().hex, 'command': 'auth_service.create_pending_user',
                               'args': ['agentB', 'agent'], 'kwargs': {}, 'token': gwC.token})
    check("new host applies writes", rc['ok'] and rc['result'][0], rc)
    pump2.stop()

    # ---- P8 self-update from the share (host publishes, client copies)
    phase("P8 Self-update — host publishes a code snapshot, client copies it")
    from updater import publish_to_share, update_from_share, current_version
    repo = os.path.dirname(os.path.abspath(__file__))
    pub_ok, pmsg = publish_to_share(repo, share)
    ver = current_version(repo)
    check("host publishes a code snapshot to the share", pub_ok and os.path.isdir(os.path.join(share, "app", ver)), pmsg)
    client_app = os.path.join(root, "clientA_app"); os.makedirs(client_app)
    # a stale client app + its own local config that must survive
    open(os.path.join(client_app, "main.py"), "w").write("print('OLD')\n")
    os.makedirs(os.path.join(client_app, "config"))
    open(os.path.join(client_app, "config", "config.json"), "w").write('{"mode":"client"}')
    up_ok, umsg = update_from_share(client_app, share)
    check("client copies the new version from the share", up_ok, umsg)
    check("client code updated", "def " in open(os.path.join(client_app, "updater.py")).read() if os.path.exists(os.path.join(client_app, "updater.py")) else False)
    check("client's own config.json NOT clobbered by the update",
          '"mode":"client"' in open(os.path.join(client_app, "config", "config.json")).read())

    # ---- P9 hard reset (go-live: wipe test data, keep config, one fresh admin)
    phase("P9 Hard reset — test -> production")
    from reset_to_production import hard_reset
    cfg_before = DatabaseManager(newhost_db).execute_with_retry(
        "SELECT COUNT(*) FROM system_config WHERE config_type='dropdown'")[0][0]
    summary = hard_reset(newhost_db)
    conn = sqlite3.connect(newhost_db)
    reports_left = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    users = conn.execute("SELECT username, role FROM users").fetchall()
    cfg_after = conn.execute("SELECT COUNT(*) FROM system_config WHERE config_type='dropdown'").fetchone()[0]
    conn.close()
    check("hard reset wiped all reports", reports_left == 0, reports_left)
    check("hard reset kept the dropdown config", cfg_after == cfg_before, (cfg_before, cfg_after))
    check("hard reset left exactly one fresh admin", users == [('admin', 'admin')], users)

    shutil.rmtree(root, ignore_errors=True)

    print("\n" + "=" * 60)
    print(f"DEPLOYMENT SIMULATION: {'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    print("=" * 60)
    print("NOT simulated (need a real Windows box — see docs/E2E-TEST-PLAN.md):")
    print("  - the Flet GUI itself + windowless .vbs launch")
    print("  - Windows taskbar icon (page.window.icon)")
    print("  - a genuine SMB share (locking/latency) instead of a local folder")
    return _fail


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
