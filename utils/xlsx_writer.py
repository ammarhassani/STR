"""Zero-dependency .xlsx writer (#16). An xlsx is a zip of XML parts; we emit
the minimal set Excel needs. Every cell is written as an inline string — the
domain has 16-digit CICs, account and report numbers that Excel would otherwise
mangle into scientific notation or strip leading zeros. No third-party library,
so it works on the locked, no-pip workstation.
"""
import re
import zipfile
from pathlib import Path
from typing import Any, List, Sequence
from xml.sax.saxutils import escape, unescape


def _col_ref(idx: int) -> str:
    """0-based column index -> Excel column letters (0->A, 26->AA)."""
    s = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


def _cell(col: int, row: int, value: Any) -> str:
    text = "" if value is None else str(value)
    # xlsx forbids most control chars; keep tab/newline/CR, drop the rest.
    text = "".join(c for c in text if c >= " " or c in "\t\n\r")
    return (f'<c r="{_col_ref(col)}{row}" t="inlineStr">'
            f'<is><t xml:space="preserve">{escape(text)}</t></is></c>')


def _sheet_xml(headers: Sequence[Any], rows: Sequence[Sequence[Any]]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<sheetData>']
    r = 1
    lines.append(f'<row r="{r}">' + "".join(_cell(c, r, h) for c, h in enumerate(headers)) + '</row>')
    for data_row in rows:
        r += 1
        lines.append(f'<row r="{r}">' + "".join(_cell(c, r, v) for c, v in enumerate(data_row)) + '</row>')
    lines.append('</sheetData></worksheet>')
    return "".join(lines)


_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '</Types>'
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)

_WORKBOOK = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="{name}" sheetId="1" r:id="rId1"/></sheets>'
    '</workbook>'
)

_WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '</Relationships>'
)


def _safe_sheet_name(name: str) -> str:
    # Excel sheet names: <=31 chars, none of : \ / ? * [ ]
    name = "".join(c for c in (name or "Sheet1") if c not in ':\\/?*[]')
    return (name[:31] or "Sheet1")


def write_xlsx(path: str, headers: Sequence[Any], rows: Sequence[Sequence[Any]],
               sheet_name: str = "Sheet1") -> Path:
    """Write a single-sheet .xlsx. Returns the Path."""
    filepath = Path(path)
    with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("xl/workbook.xml", _WORKBOOK.format(name=escape(_safe_sheet_name(sheet_name))))
        z.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        z.writestr("xl/worksheets/sheet1.xml", _sheet_xml(headers, rows))
    return filepath


_ROW_RE = re.compile(r"<row\b[^>]*>(.*?)</row>", re.DOTALL)
_T_RE = re.compile(r"<t\b[^>]*>(.*?)</t>", re.DOTALL)


def read_xlsx_rows(path: str) -> List[List[str]]:
    """Read back a sheet written by write_xlsx (all inline strings) into a list
    of rows. For verification/tests — not a general xlsx parser."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    rows = []
    for row_xml in _ROW_RE.findall(xml):
        rows.append([unescape(t) for t in _T_RE.findall(row_xml)])
    return rows
