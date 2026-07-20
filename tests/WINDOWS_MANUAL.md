# Windows checks a human has to run

The bug-hunt loop runs on macOS. When a root cause lands on `sys.frozen`,
`_MEIPASS`, `os.name == 'nt'`, `ctypes.windll`, PyInstaller, or real SMB, the
loop is required to STOP, append a row here, and mark the ledger line `park `.
It must not edit the code — it cannot falsify the claim on this machine.

Tick these off on the workstation after a `build.bat`.

| # | What to do | What should happen | Result |
|---|---|---|---|
| W1 | Run `FIU_System.exe`, log in, close it. **Do not open the Control Panel.** Wait ~15s. | No "Failed to remove temporary directory" dialog. If one appears, `flet.exe` is an independent holder of the `_MEI` directory and commit 1608b19 did not close it. | |
| W2 | Task Manager after W1: look for a surviving `flet.exe` with an image path under `%TEMP%\_MEI*`. | None. `flet_desktop.close_flet_view` calls `signal.SIGKILL`, which does not exist on Windows, inside a bare `except`. | |
| W3 | Control Panel → "Start host on this PC". | The **app** starts, or a plain `could not start host: ... Is FIU_System.exe in the same folder as this Control Panel?`. Never silence, never a second Control Panel window. | |
| W4 | Move `FIU_Control_Panel.exe` to a different folder from the app, then press the same button. | The refusal message above. Co-location is load-bearing. | |
| W5 | Log in as an account still on the default password. | Forced dialog, **no Cancel button**, Escape does nothing. | |
| W6 | Complete W5's password change. | Dashboard live and clickable — not dimmed. This is the bug that survived one claimed fix; a green web run proves nothing. | |
| W7 | Control Panel → "Build client folder", then inspect the output folder. | Contains `FIU_System.exe`, does **not** contain `FIU_Control_Panel.exe`, and `READ ME FIRST.txt` says to double-click the app. | |
| W8 | Open a dialog from the report list, save, and watch for the success toast. | Toast appears and the screen stays clickable. Six code paths dismiss-then-toast; this exercises the shared fix. | |

## Parked by the loop

The loop appends rows below. Each must name the ledger ID, the file:line it
could not falsify, and what a human should look at.

<!-- loop appends here -->
