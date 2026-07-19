"""STR WARZONE — 1 real host process + 16 real client processes, every role,
hammering the app through the actual queue transport on the real filesystem.

This is NOT a happy-path test. Every persona deliberately attempts operations it
must NOT be allowed to do, feeds malformed data, races its peers for the same
report and the same reserved numbers, and asserts business rules from the BRD.
Anything that succeeds when it should have been refused (or is refused when it
should have worked) is recorded as a DEFECT, not a failure to paper over.

Run:  python tests_warzone.py [seconds]      (default 90)

Layout: <tmp>/warzone/{HOST,C00..C15,SHARE}. Each client is a separate OS
process talking to the host over the folder queue, exactly like a workstation.
"""
import os
import sys
import json
import time
import shutil
import sqlite3
import tempfile
import subprocess
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

_IS_CHILD = len(sys.argv) > 1 and sys.argv[1] == "--child"
DURATION = int(sys.argv[1]) if (len(sys.argv) > 1 and not _IS_CHILD) else 90
ADMIN_PW = "Warzone@1234"
USER_PW = "Warzone@5678"

# username, role  -- 16 clients: 2 admins, 3 supervisors, 8 agents, 3 reporters
CREW = (
    [("admin", "admin"), ("admin2", "admin")]
    + [(f"sup{i}", "supervisor") for i in range(1, 5)]
    + [(f"agent{i}", "agent") for i in range(1, 12)]
    + [(f"rep{i}", "reporter") for i in range(1, 5)]
)


# ---------------------------------------------------------------- child process
def child_main():
    """One client workstation. argv: --child <lab> <username> <role> <deadline>"""
    lab, username, role, deadline = sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
    repo = os.path.join(lab, "CLIENT_" + username)
    sys.path.insert(0, repo)
    sys.path.insert(0, os.path.join(repo, "flet_app"))
    os.chdir(repo)

    import random
    random.seed(hash(username) & 0xFFFF)

    from config import Config
    from app_state import app_state
    from services.replica_sync import bootstrap_replica, _atomic_copy
    from services.remote_gateway import HostOfflineError, RemoteError

    findings = []

    def defect(kind, what, detail=""):
        findings.append({"who": username, "role": role, "kind": kind,
                         "what": what, "detail": str(detail)[:400]})

    def note(what, detail=""):
        findings.append({"who": username, "role": role, "kind": "INFO",
                         "what": what, "detail": str(detail)[:400]})

    Config.load()
    bus = Config.get_bus_dir()
    local = Config.get_client_replica_path()
    if not bootstrap_replica(bus, local, timeout=60.0):
        defect("INFRA", "client could not bootstrap the replica")
        return dump(lab, username, findings)
    app_state.initialize_services(local, mode="client", bus_dir=bus)

    pw = ADMIN_PW if username == "admin" else USER_PW
    ok, user, msg = app_state.authenticate(username, pw)
    if not ok:
        defect("INFRA", "login failed", msg)
        return dump(lab, username, findings)
    app_state.login(user)
    if user.get("role") != role:
        defect("AUTH", "server returned the wrong role", f"expected {role}, got {user.get('role')}")

    R = app_state.report_service
    A = app_state.approval_service
    N = app_state.report_number_service
    AU = app_state.auth_service
    D = app_state.dropdown_service
    S = app_state.settings_service
    V = app_state.version_service

    def refresh():
        """Pull the host's latest replica so reads see other clients' writes."""
        try:
            _atomic_copy(os.path.join(bus, "replica", "fiu_ro.db"), local)
        except Exception:
            pass

    def host_truth(rid, *fields):
        """Read a report straight from the host DB.

        The replica is published on a delay, so a report created a moment ago
        can read back empty or stale on a client. A business invariant judged
        off that lag reports an app defect that never happened -- which is
        exactly how the phantom "submitted with no FIU details" arose. The host
        is the only authority, so assertions ask it directly.
        """
        db = os.path.join(lab, "HOST", "database", "fiu.db")
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
            row = conn.execute(
                f"SELECT {','.join(fields)} FROM reports WHERE report_id=?",
                (rid,)).fetchone()
            conn.close()
            return dict(zip(fields, row)) if row else {}
        except Exception:
            return {}

    def attempt(label, fn, *a, **k):
        """Run a call. Returns (outcome, value). outcome:
        'ok'      -> returned a success tuple/value
        'refused' -> returned a business refusal (False, msg)
        'error'   -> raised RemoteError (host refused / exception host-side)
        'offline' -> host unreachable
        'crash'   -> raised something unexpected (always a defect)"""
        try:
            res = fn(*a, **k)
        except HostOfflineError as e:
            return "offline", str(e)
        except RemoteError as e:
            return "error", str(e)
        except Exception as e:
            defect("CRASH", f"{label} raised {type(e).__name__}", e)
            return "crash", str(e)
        if isinstance(res, (tuple, list)) and res and isinstance(res[0], bool):
            return ("ok" if res[0] else "refused"), res
        return "ok", res

    def must_deny(label, fn, *a, **k):
        """This role must NOT be able to do this. Success = RBAC breach."""
        outcome, val = attempt(label, fn, *a, **k)
        if outcome == "ok":
            defect("RBAC", f"{role} was ALLOWED to {label}", val)
        return outcome

    # Several supervisors work the same queue, so losing a race to decide an
    # approval someone else just decided is the CORRECT outcome (first one
    # wins), not a permission gap.
    _RACE_LOST = ("already approved", "already rejected", "already rework",
                  "already being processed", "not found")

    def must_allow(label, fn, *a, **k):
        outcome, val = attempt(label, fn, *a, **k)
        if outcome in ("refused", "error"):
            msg = str(val).lower()
            if not any(r in msg for r in _RACE_LOST):
                defect("PERMISSION-GAP", f"{role} was DENIED {label} (should be allowed)", val)
        return outcome, val

    # ------------------------------------------------------- shared probes
    def probe_data_rules():
        """Malformed input must be refused, never stored, never crash."""
        if role == "reporter":
            return
        bad_payloads = [
            ("empty entity", {"report_date": "18/07/2026", "reported_entity_name": ""}),
            ("missing date", {"reported_entity_name": "No Date Co"}),
            ("garbage date", {"report_date": "31/31/2026", "reported_entity_name": "Bad Date Co"}),
            ("date as text", {"report_date": "yesterday", "reported_entity_name": "Text Date Co"}),
            ("future date", {"report_date": (datetime.now() + timedelta(days=3650)).strftime("%d/%m/%Y"),
                             "reported_entity_name": "Far Future Co"}),
            ("negative amount", {"report_date": "18/07/2026", "reported_entity_name": "Neg Co",
                                 "total_transaction": "-50000"}),
            ("amount as text", {"report_date": "18/07/2026", "reported_entity_name": "Txt Amt Co",
                                "total_transaction": "many riyals"}),

            ("cic too short", {"report_date": "18/07/2026", "reported_entity_name": "Short CIC Co",
                               "cic": "12"}),
            ("cic non numeric", {"report_date": "18/07/2026", "reported_entity_name": "Alpha CIC Co",
                                 "cic": "ABCDEFGHIJKLMNOP"}),

        ]
        for label, payload in bad_payloads:
            if N.get_available_count(username) < 1:
                attempt("reserve for probe", N.reserve_block, username, 3)
            outcome, val = attempt(f"create with {label}", R.create_report, payload)
            if outcome == "ok":
                defect("VALIDATION", f"create_report ACCEPTED {label}", payload)

    def probe_number_rules():
        if role == "reporter":
            must_deny("reserve report numbers", N.reserve_block, username, 2)
            return
        # absurd block sizes must be refused (settings cap)
        for n in (0, -5, 10 ** 6):
            outcome, val = attempt(f"reserve {n}", N.reserve_block, username, n)
            if outcome == "ok":
                defect("NUMBERING", f"reserve_block accepted an absurd count {n}", val)
        # transferring a number you do not own must fail
        outcome, val = attempt("transfer someone else's number",
                               N.transfer_numbers, "agent1", "agent2", ["2026/07/001"])
        if outcome == "ok" and username not in ("agent1",):
            defect("NUMBERING", "transferred a number the caller does not own", val)
        # transfer to a non-existent user must fail
        mine = N.get_available_numbers(username)
        if mine:
            outcome, val = attempt("transfer to ghost user", N.transfer_numbers,
                                   username, "nosuchuser_zzz", [mine[0]["report_number"]])
            if outcome == "ok":
                defect("NUMBERING", "transferred numbers to a non-existent user", val)

    def probe_admin_surface():
        """Only admins may manage users/dropdowns/settings."""
        allowed = (role == "admin")
        probe = must_allow if allowed else must_deny
        probe("create a user", AU.create_user, f"ghost_{username}", "Passw0rd!x", "Ghost", "agent")
        probe("delete a user", AU.delete_user, 99999)
        probe("reset another user's password", AU.reset_password, 2, "Newpass@123")
        probe("add a dropdown value", D.add_dropdown_value, "report_source",
              f"Injected by {username}", username)
        if not allowed:
            must_deny("hard delete a report", R.hard_delete_report, 1, "warzone")
            must_deny("restore a deleted report", R.restore_report, 1)

    def probe_privilege_escalation():
        """Nobody may promote themselves."""
        me = AU.get_current_user() or {}
        uid = me.get("user_id")
        if uid and role != "admin":
            outcome, val = attempt("promote self to admin", AU.update_user, uid,
                                   {"role": "admin"})
            if outcome == "ok":
                refresh()
                fresh = AU.get_user_by_id(uid) if hasattr(AU, "get_user_by_id") else None
                defect("PRIVESC", "non-admin changed their own role", fresh or val)

    def probe_identity_spoofing():
        """The host binds the SESSION user, but these services take the identity
        as an ARGUMENT. If they trust it, any client can act as anyone."""
        victim = "agent1" if username != "agent1" else "agent2"
        # 1. reserve numbers in someone else's name
        outcome, val = attempt("reserve numbers AS another user", N.reserve_block, victim, 2)
        # Concurrent clients reserve constantly, so counting the victim's pool
        # races. Check who owns the EXACT numbers this call produced.
        got = val[1] if (outcome == "ok" and isinstance(val, (list, tuple)) and len(val) > 1) else []
        if got:
            refresh()
            mine = {n["report_number"] for n in (N.get_available_numbers(username) or [])}
            theirs = {n["report_number"] for n in (N.get_available_numbers(victim) or [])}
            stolen = [n for n in got if n in theirs and n not in mine]
            if stolen:
                defect("IDENTITY",
                       f"{username} reserved numbers into {victim}'s pool", stolen)
        # 2. destroy another user's reserved numbers via release
        refresh()
        theirs_before = {n["report_number"] for n in (N.get_available_numbers(victim) or [])}
        if theirs_before:
            attempt("release ANOTHER user's numbers", N.release_numbers,
                    victim, sorted(theirs_before)[:2])
            refresh()
            theirs_after = {n["report_number"] for n in (N.get_available_numbers(victim) or [])}
            destroyed = theirs_before - theirs_after
            # the victim may legitimately have spent one on a report meanwhile,
            # so only count numbers that vanished from the reservations entirely
            gone = [rn for rn in destroyed
                    if not any(r.get("report_number") == rn
                               for r in (R.get_reports(None, rn, None, None, None, 5, 0)[0] or []))]
            if gone:
                defect("IDENTITY", f"{username} released {victim}'s reserved numbers", gone)

        # 3. steal another user's reserved numbers
        refresh()
        theirs = N.get_available_numbers(victim) or []
        if theirs:
            nums = [t["report_number"] for t in theirs[:2]]
            outcome, val = attempt("transfer ANOTHER user's numbers to myself",
                                   N.transfer_numbers, victim, username, nums)
            if outcome == "ok":
                defect("IDENTITY", f"stole reserved numbers {nums} from {victim}", val)

    def probe_status_forgery():
        """approval_status must never be settable by the report's own author."""
        if role not in ("agent", "supervisor"):
            return
        if N.get_available_count(username) < 1:
            attempt("reserve", N.reserve_block, username, 2)
        outcome, val = attempt("create for status forgery", R.create_report, {
            "report_date": datetime.now().strftime("%d/%m/%Y"),
            "reported_entity_name": f"{username} Forgery Probe"})
        if outcome != "ok":
            return
        rid = val[1]
        out2, val2 = attempt("self-approve via update_report",
                             R.update_report, rid, {"approval_status": "approved"})
        refresh()
        after = R.get_report(rid) or {}
        if after.get("approval_status") == "approved":
            defect("STATUS-FORGERY",
                   "author promoted their OWN report to approved via update_report",
                   f"report {rid} approval_status={after.get('approval_status')}")
        # and the reverse: un-reject a rejected report
        attempt("submit", A.request_approval, rid, "x")
        out3, _ = attempt("force status back to draft",
                          R.update_report, rid, {"approval_status": "draft"})
        refresh()
        after2 = R.get_report(rid) or {}
        if after2.get("approval_status") == "draft":
            defect("STATUS-FORGERY", "author rolled their report's status backwards to draft", rid)

    def probe_locked_status_edit():
        """BRD 04§4 / 06§14: pending_approval and rejected are not editable."""
        if role not in ("agent", "supervisor"):
            return
        if N.get_available_count(username) < 1:
            attempt("reserve", N.reserve_block, username, 2)
        outcome, val = attempt("create for lock probe", R.create_report, {
            "report_date": datetime.now().strftime("%d/%m/%Y"),
            "reported_entity_name": f"{username} Lock Probe"})
        if outcome != "ok":
            return
        rid = val[1]
        attempt("add FIU details", R.update_report, rid,
                {"fiu_number": f"FIU-{username}-lock",
                 "fiu_date": datetime.now().strftime("%d/%m/%Y")})
        sub, _ = attempt("submit for approval", A.request_approval, rid, "review please")
        refresh()
        rep = R.get_report(rid) or {}
        if rep.get("approval_status") == "pending_approval":
            out, v = attempt("edit while PENDING approval", R.update_report, rid,
                             {"reported_entity_name": "EDITED WHILE PENDING APPROVAL"})
            refresh()
            now = R.get_report(rid) or {}
            if now.get("reported_entity_name") == "EDITED WHILE PENDING APPROVAL":
                defect("WORKFLOW", "a report under approval was edited by its author", rid)

    def probe_version_trail():
        """BRD 01§2 / 05§5: every edit must be versioned and attributable."""
        if role not in ("agent", "supervisor", "admin"):
            return
        if N.get_available_count(username) < 1:
            attempt("reserve", N.reserve_block, username, 2)
        outcome, val = attempt("create for version probe", R.create_report, {
            "report_date": datetime.now().strftime("%d/%m/%Y"),
            "reported_entity_name": f"{username} Version Probe"})
        if outcome != "ok":
            return
        rid = val[1]
        refresh()
        before = len(R.get_report_history(rid) or [])
        e1, v1 = attempt("edit once", R.update_report, rid, {"reported_entity_name": "Version Probe v2"})
        e2, v2 = attempt("edit twice", R.update_report, rid, {"reported_entity_name": "Version Probe v3"})
        accepted = [o for o in (e1, e2) if o == "ok"]
        refresh()
        after = len(R.get_report_history(rid) or [])
        if accepted and after <= before:
            defect("AUDIT", "an accepted edit produced no new version history",
                   f"report {rid}: versions {before} -> {after}, edits accepted={len(accepted)}")
        if not accepted:
            note("edits refused (report frozen by workflow)", f"{v1} / {v2}")

    def probe_config_surface():
        """Field rules and settings must be admin-only (BRD 04§2)."""
        if role == "admin":
            return
        VS = app_state.validation_service
        if hasattr(VS, "update_validation_rules"):
            outcome, val = attempt("rewrite field validation rules",
                                   VS.update_validation_rules, "cic", {"pattern": ".*"})
            if outcome == "ok":
                defect("RBAC", f"{role} rewrote a FIELD VALIDATION RULE", val)
        if hasattr(VS, "update_required_status"):
            outcome, val = attempt("make a required field optional",
                                   VS.update_required_status, "reported_entity_name", False)
            if outcome == "ok":
                defect("RBAC", f"{role} changed a field's REQUIRED flag", val)
        LS = app_state.logging_service
        if hasattr(LS, "clear_logs"):
            outcome, val = attempt("wipe the system logs", LS.clear_logs)
            if outcome == "ok" and isinstance(val, int) and val > 0:
                defect("AUDIT", f"{role} CLEARED {val} SYSTEM LOG ROWS", val)

    def probe_search_filters():
        """A date-range filter that returns the wrong rows is a compliance defect:
        an analyst would report the wrong period to the regulator."""
        if role == "reporter" and username != "rep1":
            return          # one reporter is enough for a read-only probe
        refresh()
        allrows, total = R.get_reports(None, None, None, None, None, 500, 0)
        if not allrows:
            return
        wide, wtotal = R.get_reports(None, None, "01/01/1990", "31/12/2099", None, 500, 0)
        if wtotal < total:
            defect("FILTER", "a date range covering ALL time returned fewer rows than no filter",
                   f"unfiltered={total} widerange={wtotal}")
        none_, ntotal = R.get_reports(None, None, "01/01/1900", "31/12/1901", None, 500, 0)
        if ntotal:
            defect("FILTER", "a date range with no reports in it returned rows",
                   f"1900-1901 returned {ntotal}")

    def probe_rejected_is_final():
        """BRD 01§2: a rejected report can never be resubmitted."""
        if role not in ("agent", "supervisor"):
            return
        refresh()
        rows, _ = R.get_reports(None, None, None, None, username, 50, 0)
        rejected = [r for r in rows if (r.get("approval_status") or "") == "rejected"]
        for rep in rejected[:2]:
            outcome, val = attempt("resubmit a REJECTED report",
                                   A.request_approval, rep["report_id"], "trying again")
            if outcome == "ok":
                defect("WORKFLOW", "a rejected report was resubmitted for approval",
                       rep["report_id"])
            # A rejected report stays EDITABLE (owner's rule): only the
            # resubmission is barred. The author still has to be able to
            # complete the record -- FIU details arrive after the fact.
            out2, v2 = attempt("edit a REJECTED report", R.update_report,
                               rep["report_id"], {"reported_entity_name": "EDIT AFTER REJECT"})
            if out2 in ("refused", "error"):
                defect("WORKFLOW", "a rejected report could not be edited by its author", v2)

    def probe_cic_uniqueness():
        """BRD 01§2: one live report per CIC -- duplicates would split a
        customer's case history in two."""
        if role not in ("agent", "supervisor"):
            return
        cic = f"{9100000000000000 + (hash(username) % 10000):016d}"
        made = []
        for attempt_no in range(2):
            if N.get_available_count(username) < 1:
                attempt("reserve", N.reserve_block, username, 2)
            outcome, val = attempt(f"create with CIC {cic}", R.create_report, {
                "report_date": datetime.now().strftime("%d/%m/%Y"),
                "reported_entity_name": f"{username} CIC probe {attempt_no}",
                "cic": cic})
            if outcome == "ok":
                made.append(val[1])
        if len(made) > 1:
            defect("DATA", "two live reports were created for the same CIC",
                   f"cic={cic} reports={made}")

    def probe_lockout():
        """BRD 06§14: five bad passwords must lock the account. A client that
        can brute force is a straight security hole."""
        if username != "agent3":
            return                      # one persona is enough; don't lock everyone
        import copy
        for i in range(7):
            app_state.authenticate("rep4", "WrongPassword!" + str(i))
        ok, _u, msg = app_state.authenticate("rep4", USER_PW)
        if ok:
            defect("SECURITY", "account still logs in after 7 failed attempts",
                   "no lockout enforced")

    def probe_delete_rules():
        """A pending report must not be deletable by anyone (its approval row
        would dangle), and a soft-deleted report must vanish from the list."""
        if role != "admin":
            return
        refresh()
        rows, _ = R.get_reports(None, None, None, None, None, 50, 0)
        pending = [r for r in rows if (r.get("approval_status") or "") == "pending_approval"]
        if pending:
            outcome, val = attempt("delete a report that is pending approval",
                                   R.delete_report, pending[0]["report_id"])
            if outcome == "ok":
                defect("WORKFLOW", "a report pending approval was deleted",
                       pending[0]["report_id"])

    def probe_last_admin():
        """The system must never be left with no administrator."""
        if role != "admin":
            return
        me = AU.get_current_user() or {}
        outcome, val = attempt("demote myself out of admin",
                               AU.update_user, me.get("user_id"), {"role": "agent"})
        if outcome == "ok":
            defect("SECURITY", "an admin demoted themselves", val)
        outcome, val = attempt("deactivate my own account",
                               AU.update_user, me.get("user_id"), {"is_active": 0})
        if outcome == "ok":
            defect("SECURITY", "an admin deactivated their own account", val)

    # ------------------------------------------------------- role workflows
    def work_agent():
        """Create -> submit -> react to rework. Also try forbidden things."""
        made = []
        for i in range(60):
            if time.time() > deadline:
                break
            if N.get_available_count(username) < 1:
                attempt("reserve", N.reserve_block, username, 5)
            payload = {
                "report_date": datetime.now().strftime("%d/%m/%Y"),
                "reported_entity_name": f"{username} Entity {i}",
                "cic": str(1000000000000000 + random.randint(0, 10 ** 6)),
                "total_transaction": str(random.randint(10_000, 5_000_000)),
            }
            # half the reports are filed with the FIU up front, half are saved
            # and completed from the basket -- both are legal agent behaviour
            if i % 2 == 0:
                payload["fiu_number"] = f"FIU-{username}-{i}"
                payload["fiu_date"] = datetime.now().strftime("%d/%m/%Y")
            outcome, val = attempt("create own report", R.create_report, payload)
            if outcome == "ok":
                rid = val[1]
                made.append(rid)
                # a saved report must wait for its FIU details before it can go
                # anywhere near a supervisor
                sub, sval = attempt("submit own report", A.request_approval, rid, "please review")
                refresh()
                fresh = (host_truth(rid, "fiu_number", "fiu_date")
                         or R.get_report(rid) or {})
                has_fiu = bool(str(fresh.get("fiu_number") or "").strip()
                               and str(fresh.get("fiu_date") or "").strip())
                if sub == "ok" and not has_fiu:
                    defect("WORKFLOW",
                           "a report with NO FIU details was submitted for approval", rid)
                if sub == "refused" and has_fiu:
                    defect("WORKFLOW",
                           "a report WITH its FIU details could not be submitted", sval)
                if sub == "refused" and not has_fiu:
                    # expected: complete it the way the basket flow does
                    attempt("add FIU details", R.update_report, rid,
                            {"fiu_number": f"FIU-{username}-{i}b",
                             "fiu_date": datetime.now().strftime("%d/%m/%Y")})
                    attempt("submit after adding FIU details", A.request_approval, rid, "filed")
                # editing while pending approval — BRD: locked until decided
                # Only pending_approval is frozen. With 21 personas running, a
                # supervisor often decides the report between the submit above
                # and this edit -- and an approved or reworked report is
                # SUPPOSED to be editable, so a successful edit is only a
                # defect if the report was pending on BOTH sides of it.
                # Checking one side alone either invents defects (after only,
                # when the decision landed first) or hides them.
                def _pending():
                    return (host_truth(rid, "approval_status")
                            .get("approval_status") == "pending_approval")

                was_pending = _pending()
                edit, eval_ = attempt("edit while pending",
                                      R.update_report, rid, {"reported_entity_name": "EDITED WHILE PENDING"})
                if edit == "ok" and was_pending and _pending():
                    defect("WORKFLOW", "report was editable while pending approval", rid)
                # agents must never approve, not even their own
                refresh()
                pend = A.get_pending_approvals() or []
                mine = [p for p in pend if p.get("report_id") == rid]
                if mine:
                    must_deny("approve own report", A.approve_report,
                              mine[0]["approval_id"], "self-approved")
            elif outcome == "crash":
                break
            # steal another agent's report
            refresh()
            rows, _ = R.get_reports(None, None, None, None, None, 20, 0)
            others = [r for r in rows if r.get("created_by") and r["created_by"] != username]
            if others:
                victim = others[0]
                must_deny("edit another agent's report", R.update_report,
                          victim["report_id"], {"reported_entity_name": f"HIJACKED by {username}"})
                must_deny("delete another agent's report", R.delete_report, victim["report_id"])
            time.sleep(0.05)
        return made

    def work_supervisor():
        """Approve/reject/rework other people's work; never their own."""
        own = []
        while time.time() < deadline:
            refresh()
            pend = A.get_pending_approvals() or []
            for p in pend[:5]:
                if time.time() > deadline:
                    break
                rid = p.get("report_id")
                rep = R.get_report(rid) if rid else None
                owner = (rep or {}).get("created_by")
                if owner == username:
                    must_deny("approve their OWN report", A.approve_report,
                              p["approval_id"], "self approval")
                    continue
                roll = random.random()
                if roll < 0.5:
                    must_allow("approve another's report", A.approve_report,
                               p["approval_id"], "looks good")
                elif roll < 0.8:
                    # rework REQUIRES a comment per the BRD
                    outcome, val = attempt("rework with NO comment", A.reject_report,
                                           p["approval_id"], "", True)
                    if outcome == "ok":
                        defect("WORKFLOW", "rework accepted with an empty comment", val)
                    must_allow("rework with a comment", A.reject_report,
                               p["approval_id"], "fix the entity name", True)
                else:
                    outcome, val = attempt("reject with NO comment", A.reject_report,
                                           p["approval_id"], "")
                    if outcome == "ok":
                        defect("WORKFLOW", "reject accepted with an empty comment", val)
                    must_allow("reject with a comment", A.reject_report,
                               p["approval_id"], "invalid report")
                # deciding the SAME approval twice must be refused
                outcome, val = attempt("decide the same approval twice",
                                       A.approve_report, p["approval_id"], "double decision")
                if outcome == "ok":
                    defect("WORKFLOW", "an already-decided approval was decided again", p["approval_id"])
            # a supervisor is also an agent: make their own report too
            if N.get_available_count(username) < 1:
                attempt("reserve", N.reserve_block, username, 3)
            outcome, val = attempt("supervisor creates own report", R.create_report, {
                "report_date": datetime.now().strftime("%d/%m/%Y"),
                "reported_entity_name": f"{username} Supervised Entity"})
            if outcome == "ok":
                own.append(val[1])
                attempt("submit own", A.request_approval, val[1], "mine")
            # supervisors must not touch the admin surface
            must_deny("delete a report", R.delete_report, (own or [1])[0])
            time.sleep(0.1)
        return own

    def work_reporter():
        """Read-only role. Every write attempt below must be refused."""
        deadline_local = deadline
        while time.time() < deadline_local:
            refresh()
            must_deny("create a report", R.create_report, {
                "report_date": datetime.now().strftime("%d/%m/%Y"),
                "reported_entity_name": f"{username} SHOULD NOT EXIST"})
            rows, _ = R.get_reports(None, None, None, None, None, 10, 0)
            if rows:
                rid = rows[0]["report_id"]
                must_deny("edit a report", R.update_report, rid, {"reported_entity_name": "REPORTER EDIT"})
                must_deny("delete a report", R.delete_report, rid)
                must_deny("submit a report for approval", A.request_approval, rid, "x")
            pend = A.get_pending_approvals() or []
            if pend:
                must_deny("approve a report", A.approve_report, pend[0]["approval_id"], "reporter approved")
                must_deny("reject a report", A.reject_report, pend[0]["approval_id"], "reporter rejected")
            must_deny("reserve numbers", N.reserve_block, username, 1)
            # reads MUST work — this role exists to read
            outcome, val = attempt("read reports", R.get_reports, None, None, None, None, None, 10, 0)
            if outcome in ("refused", "error", "crash"):
                defect("PERMISSION-GAP", "reporter cannot READ reports", val)
            time.sleep(0.2)

    def work_admin():
        """Full authority — plus the destructive paths nobody else may touch."""
        while time.time() < deadline:
            refresh()
            must_allow("create a user", AU.create_user,
                       f"tmp_{username}_{int(time.time())%100000}", "Passw0rd!x", "Temp", "agent")
            must_allow("add a dropdown value", D.add_dropdown_value,
                       "report_source", f"Src {username} {int(time.time())%1000}", username)
            rows, _ = R.get_reports(None, None, None, None, None, 10, 0)
            if rows:
                rid = rows[-1]["report_id"]
                out, val = attempt("soft delete a report", R.delete_report, rid)
                if out == "ok":
                    refresh()
                    still, _ = R.get_reports(None, None, None, None, None, 50, 0)
                    if any(r["report_id"] == rid for r in still):
                        defect("WORKFLOW", "soft-deleted report still listed", rid)
                    must_allow("restore the deleted report", R.restore_report, rid)
            # an admin must not be able to erase the audit trail even locally:
            # the client holds a read-only replica, so this must fail, not wipe.
            try:
                _sql_write(app_state, "DELETE FROM activity_log")
                defect("AUDIT", "admin erased activity_log rows from a client")
            except Exception:
                pass  # refused by the read-only replica, as designed
            time.sleep(0.3)

    def _sql_write(state, sql):
        """Direct DB write attempt — must be impossible from a client (read-only
        replica). Returns truthy only if it actually wrote."""
        state.db_manager.execute_write(sql)
        return (True, "wrote")

    # ------------------------------------------------------------ run
    try:
        probe_number_rules()
        probe_admin_surface()
        probe_privilege_escalation()
        probe_identity_spoofing()
        probe_status_forgery()
        probe_locked_status_edit()
        probe_version_trail()
        probe_config_surface()
        probe_search_filters()
        probe_data_rules()
        probe_cic_uniqueness()
        probe_rejected_is_final()
        probe_delete_rules()
        probe_last_admin()
        probe_lockout()
        if role == "agent":
            work_agent()
        elif role == "supervisor":
            work_supervisor()
        elif role == "reporter":
            work_reporter()
        elif role == "admin":
            work_admin()
    except Exception as e:
        import traceback
        defect("CRASH", "persona died", traceback.format_exc()[-600:])

    note("persona finished")
    dump(lab, username, findings)


def dump(lab, username, findings):
    path = os.path.join(lab, "findings", f"{username}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- orchestrator
def build_lab():
    # one lab per process: a fixed path made two concurrent runs wipe each
    # other's HOST mid-test, which reads as a phantom app defect
    lab = os.path.join(tempfile.gettempdir(), f"str_warzone_{os.getpid()}")
    if os.path.exists(lab):
        shutil.rmtree(lab, ignore_errors=True)
    os.makedirs(os.path.join(lab, "SHARE"))
    share = os.path.join(lab, "SHARE")

    def install(name, mode):
        dst = os.path.join(lab, name)
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", "sandbox", "cbox", "pbox", "uibox",
            "nukebox", "logs", "vendor"))
        cfgdir = os.path.join(dst, "config")
        os.makedirs(cfgdir, exist_ok=True)
        db = os.path.join(dst, "database", "fiu.db")
        os.makedirs(os.path.dirname(db), exist_ok=True)
        json.dump({"database_path": db, "backup_path": os.path.join(dst, "backups"),
                   "session_timeout": 30, "max_login_attempts": 5,
                   "mode": mode, "share_path": share, "host_id": None},
                  open(os.path.join(cfgdir, "config.json"), "w", encoding="utf-8"), indent=2)
        return dst, db

    host_dir, host_db = install("HOST", "host")
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    initialize_database(host_db)
    migrate_database(host_db)

    conn = sqlite3.connect(host_db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password(ADMIN_PW),))
    for username, role in CREW:
        if username == "admin":
            continue
        conn.execute(
            "INSERT OR IGNORE INTO users (username,password,full_name,role,is_active,created_by,"
            "must_change_password) VALUES (?,?,?,?,1,'SYSTEM',0)",
            (username, SecurityService.hash_password(USER_PW), username.upper(), role))
    conn.commit()
    conn.close()

    for username, _role in CREW:
        install("CLIENT_" + username, "client")
    return lab, host_dir, host_db, share


def main():
    print(f"=== STR WARZONE: 1 host + {len(CREW)} clients, {DURATION}s ===")
    lab, host_dir, host_db, share = build_lab()
    print(f"lab: {lab}")

    host_log = open(os.path.join(lab, "host.log"), "w", encoding="utf-8")
    host = subprocess.Popen([sys.executable, os.path.join(host_dir, "flet_app", "main.py"), "--host"],
                            cwd=host_dir, stdout=host_log, stderr=subprocess.STDOUT)
    # wait for the first replica publish
    rep = os.path.join(share, "str_bus", "replica", "fiu_ro.db")
    for _ in range(120):
        if os.path.exists(rep):
            break
        time.sleep(0.5)
    if not os.path.exists(rep):
        host.kill()
        print("HOST NEVER PUBLISHED A REPLICA — aborting")
        print(open(os.path.join(lab, "host.log"), encoding="utf-8").read()[-2000:])
        return 1
    print("host up, replica published")

    deadline = time.time() + DURATION
    kids = []
    for username, role in CREW:
        p = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--child", lab, username, role, str(deadline)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        kids.append((username, p))
    print(f"{len(kids)} clients attacking...")

    for username, p in kids:
        try:
            p.wait(timeout=max(30, DURATION + 180))
        except subprocess.TimeoutExpired:
            p.kill()
            print(f"  client {username} HUNG — killed")

    time.sleep(3)
    host.terminate()
    try:
        host.wait(timeout=15)
    except subprocess.TimeoutExpired:
        host.kill()
    host_log.close()
    return report(lab, host_db)


def report(lab, host_db):
    findings = []
    fdir = os.path.join(lab, "findings")
    for name in sorted(os.listdir(fdir)) if os.path.isdir(fdir) else []:
        findings += json.load(open(os.path.join(fdir, name), encoding="utf-8"))

    print("\n" + "=" * 74)
    print("INVARIANTS (checked against the host DB after the storm)")
    print("=" * 74)
    inv_fail = 0
    conn = sqlite3.connect(host_db)

    def inv(label, sql, expect=0):
        nonlocal inv_fail
        got = conn.execute(sql).fetchone()[0]
        ok = (got == expect)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}")
        if not ok:
            inv_fail += 1
        return got

    inv("duplicate report_number", "SELECT COUNT(*)-COUNT(DISTINCT report_number) FROM reports")
    inv("duplicate serial_number", "SELECT COUNT(*)-COUNT(DISTINCT sn) FROM reports")
    inv("reserved number used by 2 reports",
        "SELECT COUNT(*) FROM (SELECT used_by_report_id FROM reserved_numbers "
        "WHERE used_by_report_id IS NOT NULL GROUP BY used_by_report_id HAVING COUNT(*)>1)")
    inv("number both used and available",
        "SELECT COUNT(*) FROM reserved_numbers WHERE status='available' AND used_by_report_id IS NOT NULL")
    inv("report_number in reports but its reservation still available",
        "SELECT COUNT(*) FROM reserved_numbers rn JOIN reports r ON r.report_number=rn.report_number "
        "WHERE rn.status='available'")
    inv("reports created by a reporter",
        "SELECT COUNT(*) FROM reports WHERE created_by IN (SELECT username FROM users WHERE role='reporter')")
    inv("approvals decided by the report's own author",
        "SELECT COUNT(*) FROM report_approvals a JOIN reports r ON r.report_id=a.report_id "
        "JOIN users u ON u.user_id=a.approver_id "
        "WHERE u.username=r.created_by AND a.approval_status!='pending'")
    inv("approvals decided by a non-approver role",
        "SELECT COUNT(*) FROM report_approvals a JOIN users u ON u.user_id=a.approver_id "
        "WHERE a.approval_status!='pending' AND u.role NOT IN ('admin','supervisor')")
    inv("users escalated to admin during the run",
        "SELECT COUNT(*) FROM users WHERE role='admin' AND username NOT IN ('admin','admin2')")
    total_reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    versions = conn.execute("SELECT COUNT(*) FROM report_versions").fetchone()[0]
    activity = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    approvals = conn.execute("SELECT COUNT(*) FROM report_approvals").fetchone()[0]
    print(f"\n  volume: {total_reports} reports, {versions} versions, "
          f"{approvals} approvals, {activity} activity rows")
    if total_reports and versions == 0:
        print("  FAIL every report must have an initial version")
        inv_fail += 1
    if total_reports and activity == 0:
        print("  FAIL report writes must leave an audit trail")
        inv_fail += 1
    conn.close()

    print("\n" + "=" * 74)
    print("DEFECTS")
    print("=" * 74)
    real = [f for f in findings if f["kind"] != "INFO"]
    by_kind = {}
    for f in real:
        by_kind.setdefault(f["kind"], []).append(f)
    if not real:
        print("  none reported by the personas")
    for kind in sorted(by_kind):
        print(f"\n[{kind}] {len(by_kind[kind])}")
        seen = set()
        for f in by_kind[kind]:
            key = (f["role"], f["what"])
            if key in seen:
                continue
            seen.add(key)
            print(f"  - ({f['role']}) {f['what']}")
            if f["detail"]:
                print(f"      {f['detail'][:220]}")

    print("\n" + "=" * 74)
    finished = len([f for f in findings if f["what"] == "persona finished"])
    if finished < len(CREW):
        print(f"  FAIL only {finished} of {len(CREW)} personas finished — the rest died "
              f"before reporting, so the invariants above ran on partial data")
        inv_fail += 1
    if total_reports == 0:
        print("  FAIL no reports were created at all — every invariant below is "
              "vacuously true on an empty database")
        inv_fail += 1
    print(f"personas finished: {finished}/{len(CREW)}   "
          f"distinct defects: {len({(f['role'], f['what']) for f in real})}   "
          f"invariant failures: {inv_fail}")
    print("=" * 74)
    return 1 if (real or inv_fail) else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child_main()
    else:
        sys.exit(main())
