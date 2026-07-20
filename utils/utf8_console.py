"""Force UTF-8 on stdout/stderr.

The workstation is Windows, whose console defaults to cp1252: printing any
Arabic (report data, field labels, log lines, test output) raises
UnicodeEncodeError and kills the writer. Importing this module fixes the
streams once, for the app and for the test suites alike.

Imported for its side effect by config.py, services/__init__.py and
flet_app/i18n/__init__.py — between them every entry point and test loads one.

A packaged --windowed app has NO console, so Python sets sys.stdout and
sys.stderr to None. Anything that touches them then dies: print() raises
AttributeError, and uvicorn's log formatter calls sys.stdout.isatty() and
brings the whole app down with "Unable to configure formatter 'default'".
That is a real crash on a real client PC, caused purely by logging. So when a
stream is missing, a black-hole stream is installed in its place -- writes go
nowhere, but nothing explodes for want of somewhere to write.
"""
import io
import sys


class _NullStream(io.TextIOBase):
    """Accepts everything, keeps nothing, answers the questions loggers ask."""

    encoding = "utf-8"
    errors = "replace"

    def write(self, s):
        return len(s)

    def flush(self):
        pass

    def isatty(self):
        return False

    def fileno(self):
        # Loggers ask for this; a windowed app genuinely has no descriptor.
        raise io.UnsupportedOperation("no file descriptor in a windowed app")

    def writable(self):
        return True


if sys.stdout is None:
    sys.stdout = _NullStream()
if sys.stderr is None:
    sys.stderr = _NullStream()

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass  # redirected/detached stream — nothing to reconfigure
