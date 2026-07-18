"""
STR UI-LAYER PROSECUTOR — drives REAL Flet views/dialogs with a faithful
fake Page, invokes actual event handlers with hostile input, asserts the
UI layer neither crashes nor lets bad data through.
"""
import os, sys, asyncio, sqlite3, shutil, traceback
from datetime import datetime
from pathlib import Path
import flet as ft

REPO = '/Users/engammar/Scripts/STR'
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'flet_app'))
SCRATCH = os.path.dirname(os.path.abspath(__file__))
BOX = os.path.join(SCRATCH, 'uibox'); DB = os.path.join(BOX, 'u.db')
LOGD = os.path.join(BOX, 'logs')

FINDINGS = []
def finding(area, name, bad, detail=''):
    FINDINGS.append((area, name, bool(bad), str(detail)[:200]))
    print(f"  [{'FAIL' if bad else 'ok'}] {area}: {name}" + (f" — {detail}" if bad else ''))

# ---- fake page faithful to the 4 attrs the views actually use
class FakePage:
    def __init__(self):
        self.overlay = []
        self.snack_bar = None
        self.updated = 0
        self._loop = asyncio.new_event_loop()
    def update(self): self.updated += 1
    def run_task(self, coro_fn, *args):
        # views pass a bare coroutine function; run to completion synchronously
        return self._loop.run_until_complete(coro_fn(*args))

def walk(control):
    """Yield every control in a Flet tree."""
    seen = set()
    stack = [control]
    while stack:
        c = stack.pop()
        if id(c) in seen or c is None: continue
        seen.add(id(c)); yield c
        for attr in ('controls', 'content', 'actions', 'title', 'leading', 'trailing', 'tabs'):
            v = getattr(c, attr, None)
            if isinstance(v, (list, tuple)): stack.extend(v)
            elif v is not None and hasattr(v, '__class__') and 'flet' in str(type(v)): stack.append(v)

def find_buttons(tree, text_sub=None):
    out = []
    for c in walk(tree):
        if isinstance(c, (ft.ElevatedButton, ft.TextButton, ft.FilledButton, ft.OutlinedButton, ft.IconButton)):
            if text_sub is None or (getattr(c, 'text', '') and text_sub.lower() in c.text.lower()):
                out.append(c)
        elif isinstance(c, ft.Container) and getattr(c, 'on_click', None) is not None:
            # app_button() flat Container: Row of [Icon?, Text] with on_click set
            label = ' '.join(sub.value for sub in walk(c) if isinstance(sub, ft.Text) and sub.value)
            if text_sub is None or text_sub.lower() in label.lower():
                out.append(c)
    return out

def build_db():
    if os.path.exists(BOX): shutil.rmtree(BOX)
    os.makedirs(LOGD)
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    initialize_database(DB); migrate_database(DB)
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
                 "VALUES ('admin','x','Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO NOTHING")
    conn.execute("UPDATE users SET password=?, role='admin', is_active=1 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    conn.commit(); conn.close()

def make_app_state():
    from flet_app.app_state import AppState
    st = AppState()
    st.initialize_services(DB)
    return st

def run():
    build_db()
    st = make_app_state()

    # ============================================== LOGIN VIEW (real handler, LIVE class)
    A = 'UI Login'
    from flet_app.views.login_view import LoginView
    page = FakePage()
    captured = {}
    def on_success(user): captured['user'] = user
    login_view = LoginView(page, st, on_success)
    view = login_view.build()
    # LoginView exposes the fields/button directly — use those, not tree-walking
    finding(A, 'login view builds with 2 fields',
            login_view.username_field is None or login_view.password_field is None)
    pass_f = login_view.password_field
    user_f = login_view.username_field
    login_btn = login_view.login_button

    def submit(u, p):
        """Click login; swallow the focus-on-unmounted AssertionError which is
        a Flet-runtime-only artifact (real app has fields mounted)."""
        user_f.value = u; pass_f.value = p
        try:
            login_btn.on_click(None)
        except AssertionError as e:
            if 'added to the page' not in str(e):
                raise

    # hostile: empty submit -> no auth
    try:
        submit('', ''); finding(A, 'empty-credential submit authenticated', 'user' in captured, captured.get('user'))
    except Exception:
        finding(A, 'empty submit CRASHED UI', True, traceback.format_exc().splitlines()[-1])
    # hostile: SQLi username -> no auth
    captured.clear()
    try:
        submit("admin' OR '1'='1", "x"); finding(A, 'SQLi username logged in', 'user' in captured, captured.get('user'))
    except Exception:
        finding(A, 'SQLi username CRASHED UI', True, traceback.format_exc().splitlines()[-1])
    # happy path: real creds -> success callback fires
    captured.clear()
    try:
        submit('admin', 'Admin@1234')
        finding(A, 'valid login did NOT fire success callback', 'user' not in captured,
                captured.get('user', {}).get('username') if captured else None)
    except Exception:
        finding(A, 'valid login CRASHED UI', True, traceback.format_exc().splitlines()[-1])

    # ============================================== REPORT DIALOG (validate + save)
    B = 'UI Report dialog'
    st.login(st.auth_service.authenticate('admin', 'Admin@1234')[1])
    # Add-report gate (Task 5) requires a reserved number to open the create form.
    st.report_number_service.reserve_block('admin', 5)
    from flet_app.dialogs.report_dialog import show_report_dialog
    page2 = FakePage()
    saved = {'called': False}
    try:
        show_report_dialog(page2, st, report_data=None, on_save=lambda: saved.__setitem__('called', True))
        finding(B, 'dialog failed to mount to overlay', len(page2.overlay) == 0, f"overlay={len(page2.overlay)}")
        dialog_tree = page2.overlay[-1] if page2.overlay else None
    except Exception as e:
        finding(B, 'opening report dialog CRASHED', True, traceback.format_exc().splitlines()[-1])
        dialog_tree = None

    if dialog_tree:
        # find the Save button and click with an EMPTY form -> must not save, must not crash
        save_btns = find_buttons(dialog_tree, 'save')
        try:
            if save_btns:
                save_btns[0].on_click(None)
                finding(B, 'empty-form Save wrote a report', saved['called'], 'on_save fired on empty form')
            else:
                finding(B, 'no Save button found in dialog', True)
        except Exception as e:
            finding(B, 'empty-form Save CRASHED', True, traceback.format_exc().splitlines()[-1])

        # inject hostile values into every text field then Save -> no crash
        try:
            for c in walk(dialog_tree):
                if isinstance(c, ft.TextField):
                    c.value = "x'; DROP TABLE reports;-- " + "A"*300
            if save_btns:
                save_btns[0].on_click(None)
            tbl = sqlite3.connect(DB).execute("SELECT name FROM sqlite_master WHERE name='reports'").fetchone()
            finding(B, 'hostile-input Save dropped table', tbl is None)
        except Exception as e:
            finding(B, 'hostile-input Save CRASHED', True, traceback.format_exc().splitlines()[-1])

    # ============================================== ADMIN PANEL delete path
    C = 'UI Admin panel'
    # the view must NOT contain a raw hard DELETE of users
    src = open(os.path.join(REPO, 'flet_app/views/admin_panel_view.py')).read()
    finding(C, 'admin panel view still contains raw "DELETE FROM users"',
            'DELETE FROM users' in src, 'raw hard-delete present')
    # and the service path it now uses must SOFT-delete (row remains, is_active=0)
    st.auth_service.create_user('victim', 'pass123', 'Victim', 'agent')
    vid = sqlite3.connect(DB).execute("SELECT user_id FROM users WHERE username='victim'").fetchone()[0]
    ok, msg = st.auth_service.delete_user(vid)
    row = sqlite3.connect(DB).execute("SELECT is_active FROM users WHERE user_id=?", (vid,)).fetchone()
    finding(C, 'delete_user hard-removes the row (should soft-delete)', row is None, 'row gone')
    finding(C, 'delete_user did not set is_active=0', not (row and row[0] == 0), f"is_active={row[0] if row else 'gone'}")

    # ============================================== other views build without crash
    D = 'UI View builds'
    from flet_app.views.reports_view import build_reports_view
    from flet_app.views.dashboard_view import build_dashboard_content
    from flet_app.views.export_view import build_export_view
    from flet_app.views.settings_view import build_settings_view
    from flet_app.views.dropdown_management_view import build_dropdown_management_view
    from flet_app.views.field_management_view import build_field_management_view
    from flet_app.views.admin_panel_view import build_admin_panel_view
    for name, fn in [('reports', build_reports_view), ('dashboard', build_dashboard_content),
                     ('export', build_export_view), ('settings', build_settings_view),
                     ('dropdowns', build_dropdown_management_view), ('fields', build_field_management_view),
                     ('admin', build_admin_panel_view)]:
        p = FakePage()
        try:
            fn(p, st)
            finding(D, f'{name} view build crashed', False)
        except Exception as e:
            finding(D, f'{name} view build CRASHED', True, traceback.format_exc().splitlines()[-1])

    # ---- new-feature UI wiring present
    E = 'UI Feature wiring'
    ap_src = open(os.path.join(REPO, 'flet_app/views/approval_panel_view.py')).read()
    finding(E, 'approval panel missing reassign dropdown wiring',
            'reassign_ref' not in ap_src or 'get_active_agents' not in ap_src)
    finding(E, 'reject_report not passed reassign_to from UI',
            'reassign_to=reassign_to' not in ap_src)
    set_src = open(os.path.join(REPO, 'flet_app/views/settings_view.py')).read()
    # #15: numbering is calendar-driven now — the manual Close-Month control is
    # GONE; settings shows the current numbering month instead.
    finding(E, 'settings still has the removed Close-Month control',
            'handle_close_month' in set_src or 'close_month(' in set_src)
    finding(E, 'settings lost the numbering-month display',
            'get_active_numbering_month' not in set_src)
    rd_src = open(os.path.join(REPO, 'flet_app/dialogs/report_dialog.py')).read()
    rv_src = open(os.path.join(REPO, 'flet_app/views/reports_view.py')).read()
    main_src2 = open(os.path.join(REPO, 'flet_app/main.py')).read()
    # #7: every Add-Report affordance must be gated on the add_report permission,
    # so a reporter never sees / can't trigger a create it can't do.
    finding(E, 'report dialog does not gate create on add_report permission',
            "has_permission('add_report')" not in rd_src)
    finding(E, 'reports view Add button not gated on add_report permission',
            "has_permission('add_report')" not in rv_src)
    finding(E, "Ctrl+N still gated on the bogus 'creator' role instead of add_report",
            "'creator'" in main_src2)
    finding(E, 'report dialog missing edit-lock acquire/release',
            'acquire_edit_lock' not in rd_src or 'release_edit_lock' not in rd_src)
    hdr_src = open(os.path.join(REPO, 'flet_app/components/header.py')).read()
    finding(E, 'header still has a theme toggle (dark mode removed)',
            'toggle_theme' in hdr_src or 'theme_button' in hdr_src)
    rsv = open(os.path.join(REPO, 'flet_app/dialogs/reservation_dialog.py')).read()
    finding(E, 'reservation dialog still runs raw SQL (must use service methods)',
            'execute_with_retry' in rsv or 'DELETE FROM' in rsv)
    finding(E, 'reservation dialog missing reserve_block wiring',
            'reserve_block' not in rsv)

    # ---- report
    print('\n' + '='*70); print('UI PROSECUTION — failures')
    fails = [f for f in FINDINGS if f[2]]
    for area, name, bad, det in FINDINGS:
        if bad: print(f"  ✗ {area}: {name} — {det}")
    print(f"\nUI failures: {len(fails)}/{len(FINDINGS)}")
    return len(fails)

if __name__ == '__main__':
    run()
