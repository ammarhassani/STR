"""Force UTF-8 on stdout/stderr.

The workstation is Windows, whose console defaults to cp1252: printing any
Arabic (report data, field labels, log lines, test output) raises
UnicodeEncodeError and kills the writer. Importing this module fixes the
streams once, for the app and for the test suites alike.

Imported for its side effect by config.py, services/__init__.py and
flet_app/i18n/__init__.py — between them every entry point and test loads one.
"""
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass  # redirected/detached stream — nothing to reconfigure
