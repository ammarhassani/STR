"""#16 — zero-dependency xlsx writer. Run: python3.14 tests_xlsx.py"""
import os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def test_roundtrip_and_validity():
    from utils.xlsx_writer import write_xlsx, read_xlsx_rows, _col_ref
    d = tempfile.mkdtemp(); path = os.path.join(d, "t.xlsx")
    headers = ['CIC', 'Entity', 'Amount']
    data = [
        ['0001234567890012', 'Acme <&> Co', '1000'],   # leading zeros + XML-special chars
        ['9999999999999999', 'شركة الاختبار', '2,500'],  # Arabic
    ]
    write_xlsx(path, headers, data, sheet_name="Reports")

    check("file exists", os.path.exists(path))
    check("is a valid zip (xlsx container)", zipfile.is_zipfile(path))
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    for part in ['[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml',
                 'xl/_rels/workbook.xml.rels', 'xl/worksheets/sheet1.xml']:
        check(f"contains {part}", part in names, names)

    rows = read_xlsx_rows(path)
    check("header + 2 rows", len(rows) == 3, len(rows))
    check("headers preserved", rows[0] == headers, rows[0])
    check("leading zeros preserved (stored as text)", rows[1][0] == '0001234567890012', rows[1][0])
    check("XML-special chars round-trip", rows[1][1] == 'Acme <&> Co', rows[1][1])
    check("Arabic preserved", rows[2][1] == 'شركة الاختبار', rows[2][1])

    check("col ref A", _col_ref(0) == 'A')
    check("col ref Z", _col_ref(25) == 'Z')
    check("col ref AA", _col_ref(26) == 'AA')
    check("col ref AB", _col_ref(27) == 'AB')


def test_empty_and_control_chars():
    from utils.xlsx_writer import write_xlsx, read_xlsx_rows
    d = tempfile.mkdtemp(); path = os.path.join(d, "e.xlsx")
    # a control char (bell) must be stripped, not corrupt the file
    write_xlsx(path, ['a'], [['x\x07y'], [None]], sheet_name="S")
    rows = read_xlsx_rows(path)
    check("control char stripped", rows[1][0] == 'xy', rows[1][0])
    check("None becomes blank", rows[2][0] == '', rows[2])


if __name__ == "__main__":
    test_roundtrip_and_validity()
    test_empty_and_control_chars()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
