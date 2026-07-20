"""Say why the host died, on a build that has nowhere to print.

STR.spec sets console=False, so the packaged executable is a windowed Windows
binary and `sys.stdout` is None. `print()` there returns silently -- it does not
raise, it does not buffer, the text simply does not exist.

That is how the host's own FATAL guard behaved: a host started from a Startup
shortcut with an unreadable database printed a careful explanation into nothing
and exited 2. What the operator saw at every login was no window, no error, no
log. The Control Panel then reported "No host is running" -- true, and useless.

MessageBoxW is the same ctypes mechanism host/sleep_guard.py already uses: no
COM, no spawned process, no new dependency, nothing extra for a security team
to look at. On anything that is not a windowed Windows build it falls back to
stderr, so running from source still behaves normally.
"""
import sys

MB_ICONERROR = 0x10
MB_SETFOREGROUND = 0x10000
MB_TOPMOST = 0x40000


def fatal_notice(message: str, title: str = "STR") -> None:
    """Put `message` somewhere a human will actually see it."""
    # stderr first and always: when a console DOES exist (running from source,
    # or a --panel-cli run) that is the useful channel, and it costs nothing.
    try:
        print(message, file=sys.stderr, flush=True)
    except Exception:
        pass  # windowed build: sys.stderr is None too

    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, message, title, MB_ICONERROR | MB_SETFOREGROUND | MB_TOPMOST)
    except Exception:
        pass  # never let the way we report a failure become another failure
