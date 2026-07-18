"""#6 — log export actually writes a file (xlsx per #16).
Run: python3.14 tests_log_export.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def test_export_logs_writes_file():
    from utils.export import export_logs
    d = tempfile.mkdtemp()
    logs = [
        {'timestamp': '2026-07-18 10:00:00', 'level': 'INFO', 'module': 'auth',
         'function': 'login', 'user': 'admin', 'message': 'User logged in'},
        {'timestamp': '2026-07-18 10:01:00', 'level': 'ERROR', 'module': 'reports',
         'function': 'save', 'user': 'ag1', 'message': 'فشل الحفظ'},  # Arabic
    ]
    from utils.xlsx_writer import read_xlsx_rows
    path = export_logs(logs, output_dir=d)
    check("file was created", os.path.exists(path), path)
    check("filename is a timestamped xlsx", str(path).endswith('.xlsx') and 'fiu_logs_' in str(path), path)

    rows = read_xlsx_rows(path)
    check("header + 2 data rows present", len(rows) == 3, len(rows))
    check("all columns exported", rows[0] == ['timestamp', 'level', 'module', 'function', 'user', 'message'], rows[0])
    check("first row content correct", rows[1][4] == 'admin' and rows[1][1] == 'INFO', rows[1])
    check("Arabic message preserved", rows[2][5] == 'فشل الحفظ', rows[2][5])


def test_ragged_keys_union():
    from utils.export import export_logs
    d = tempfile.mkdtemp()
    logs = [
        {'a': '1', 'b': '2'},
        {'a': '3', 'c': '4'},  # different key set
    ]
    from utils.xlsx_writer import read_xlsx_rows
    path = export_logs(logs, output_dir=d)
    rows = read_xlsx_rows(path)
    check("header is the union of all keys", rows[0] == ['a', 'b', 'c'], rows[0])
    check("missing keys become blank", rows[2] == ['3', '', '4'], rows[2])


def test_empty_raises():
    from utils.export import export_logs
    try:
        export_logs([], output_dir=tempfile.mkdtemp())
        check("empty logs raises", False, "no error raised")
    except ValueError:
        check("empty logs raises ValueError", True)


if __name__ == "__main__":
    test_export_logs_writes_file()
    test_ragged_keys_union()
    test_empty_raises()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
