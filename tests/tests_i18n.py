"""#3 Phase 0 — i18n infrastructure. Run: python3.14 tests_i18n.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'flet_app'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def test_catalog_parity():
    from i18n import catalog_en, catalog_ar
    en, ar = set(catalog_en.STRINGS), set(catalog_ar.STRINGS)
    check("every English key has an Arabic draft", en <= ar, en - ar)
    check("no stray Arabic-only keys", ar <= en, ar - en)
    # Arabic values should not accidentally equal the English (untranslated)
    same = [k for k in en if catalog_en.STRINGS[k] == catalog_ar.STRINGS.get(k)]
    # a few (like format-only) may legitimately match; just ensure most differ
    check("most strings are actually translated", len(same) <= 2, same)


def test_t_and_fallback():
    import i18n
    from i18n import t, set_language, get_language, is_rtl
    set_language('en')
    check("English active", get_language() == 'en' and not is_rtl())
    check("t returns English", t('login.button') == 'Login', t('login.button'))
    set_language('ar')
    check("Arabic active + RTL", get_language() == 'ar' and is_rtl())
    check("t returns Arabic", t('login.button') == 'دخول', t('login.button'))
    check("unknown language falls back to en", (set_language('zz'), get_language())[1] == 'en')
    check("missing key returns the key itself", t('no.such.key') == 'no.such.key')
    set_language('en')
    check("format args applied", t('onboard.user_id', username='bob') == 'User ID: bob',
          t('onboard.user_id', username='bob'))


def test_help_prose_is_localized():
    """The help tabs render catalog prose, not hardcoded English."""
    from i18n import t, set_language
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'flet_app', 'dialogs', 'help_dialog.py'), encoding='utf-8').read()
    check("help dialog pulls its prose from the catalog",
          't("help.body.getting_started")' in src and 'Welcome to FIU' not in src)
    set_language('en'); en = t('help.body.faq')
    set_language('ar'); ar = t('help.body.faq')
    set_language('en')
    check("FAQ prose differs per language", en != ar and 'Frequently Asked' in en)
    check("Arabic FAQ is actually Arabic", any('؀' <= c <= 'ۿ' for c in ar))


def test_language_persists_and_logs_in():
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
    auth = AuthService(dbm, log)

    ok, user, _ = auth.authenticate('admin', 'Admin@1234')
    check("new admin defaults to English", ok and user.get('language') == 'en', user)

    # user sets their own language
    oklang, msg = auth.set_user_language('ar')
    check("user sets own language", oklang, msg)
    check("current_user language updated in memory", auth.current_user['language'] == 'ar')

    # bad language rejected
    okbad, _ = auth.set_user_language('fr')
    check("unsupported language rejected", not okbad)

    # persists across a fresh login
    auth2 = AuthService(dbm, log)
    ok2, user2, _ = auth2.authenticate('admin', 'Admin@1234')
    check("language persisted to next login", user2.get('language') == 'ar', user2)


def test_set_language_is_a_write_command():
    from services import command_registry as cr
    check("set_user_language routes to the host in client mode",
          cr.is_write_command('auth_service.set_user_language'))


if __name__ == "__main__":
    test_catalog_parity()
    test_t_and_fallback()
    test_help_prose_is_localized()
    test_language_persists_and_logs_in()
    test_set_language_is_a_write_command()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
