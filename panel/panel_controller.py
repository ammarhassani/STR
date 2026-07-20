"""Operator-plane logic (UI-free, fully testable). Reads the shared heartbeat/
queue/backups and drives the Phase-3a primitives."""
import json
import os
import signal
import sys
import glob
import time
import uuid
import shutil
import sqlite3
import subprocess

from host.heartbeat import read_heartbeat, is_stale
from host.integrity import check_and_restore
from host.failover import become_host


_CLIENT_KIT_README = """SET UP STR ON THIS PC
=====================

Do these 3 things. Nothing else.


1. COPY THIS WHOLE FOLDER to the C: drive.

   Put it at:   C:\\STR
   NOT in Program Files. The app writes next to itself and cannot write there.


2. DOUBLE-CLICK {exe}

   First time only, Windows may ask about the network. Say yes.


3. LOG IN with the username your admin gave you.


-----------------------------------------------------------------
IF SOMETHING SEEMS WRONG
-----------------------------------------------------------------

On the login screen, bottom right: "Control Panel"

It opens a window that says what the problem is in plain words.
You do not need it for normal work.


-----------------------------------------------------------------
IF SOMETHING GOES WRONG
-----------------------------------------------------------------

It asks me to set up a database
   -> It cannot see the shared folder.
      Open this in File Explorer:  {share}
      If that fails, the problem is the network or your permissions,
      not the app. Tell your admin.

It says access denied
   -> Your PC needs the share account. Tell your admin:
      "this PC needs the STR share credentials"

It opens but there are no reports
   -> The host PC is not running. Someone must start it there.

Nothing happens when I double-click
   -> Check you copied the WHOLE folder, including the config folder.
"""


class PanelController:
    # The app executable, which is NOT necessarily the one this code runs in.
    APP_EXE = "FIU_System.exe"

    def __init__(self, bus_dir, local_db_path, host_id):
        self.bus = bus_dir
        self.db_path = local_db_path
        self.host_id = host_id
        self.backups_dir = os.path.join(bus_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)
        os.makedirs(os.path.join(bus_dir, ".tmp"), exist_ok=True)  # manual_backup temp dir

    def status(self):
        hb = read_heartbeat(self.bus)
        pend = os.path.join(self.bus, "queue", "pending")
        proc = os.path.join(self.bus, "queue", "processing")
        ver_path = os.path.join(self.bus, "replica", "version.txt")
        version = None
        try:
            with open(ver_path, encoding="utf-8") as f:
                version = f.read().strip()
        except OSError:
            pass
        return {
            "heartbeat": hb,
            "host_online": not is_stale(hb),
            "host_id": hb.get("host_id") if hb else None,
            "term": hb.get("term", 0) if hb else 0,
            "queue_pending": len([n for n in os.listdir(pend) if n.endswith(".json")]) if os.path.isdir(pend) else 0,
            "queue_processing": len([n for n in os.listdir(proc) if n.endswith(".json")]) if os.path.isdir(proc) else 0,
            "replica_version": version,
            "backups": self.list_backups(),
        }

    def health(self, share_path=None):
        """Everything an operator needs to answer 'is it working?' in one look.

        status() answers 'what is the state'. This answers 'is anything wrong',
        which is a different question -- it is the one asked when a user says
        the app is slow, and the answer is usually 'the share went away' or
        'this client is reading an hour-old replica'.
        """
        import socket
        st = self.status()
        hb = st["heartbeat"] or {}

        now_ms = time.time() * 1000
        hb_age = (now_ms - hb["epoch_ms"]) / 1000.0 if hb.get("epoch_ms") else None

        # How stale is the copy this PC actually reads from?
        replica = os.path.join(self.bus, "replica", "fiu_ro.db")
        replica_age = None
        if os.path.exists(replica):
            replica_age = max(0.0, time.time() - os.path.getmtime(replica))

        share_ok, share_msg = self.check_share(share_path or os.path.dirname(self.bus))

        problems = []
        if not st["host_online"]:
            problems.append("No host is running. Nobody can save changes.")
        if not share_ok:
            problems.append(f"Shared folder problem: {share_msg}")
        if replica_age is not None and replica_age > 300:
            # "908 minutes" makes an operator do arithmetic to find out whether
            # to worry; say it in the largest unit that still means something.
            if replica_age >= 86400:
                howold = f"{int(replica_age // 86400)} day(s)"
            elif replica_age >= 3600:
                howold = f"{int(replica_age // 3600)} hour(s)"
            else:
                howold = f"{int(replica_age // 60)} minute(s)"
            problems.append(f"This PC's copy of the data is {howold} old. "
                            f"It is not seeing recent changes.")
        if st["queue_pending"] > 25:
            problems.append(f"{st['queue_pending']} changes are waiting to be saved. "
                            f"The host may be struggling or stopped.")
        if not st["backups"]:
            problems.append("There are no backups yet.")

        return {
            **st,
            "this_pc": socket.gethostname(),
            "host_pc": hb.get("hostname"),
            "heartbeat_age_seconds": hb_age,
            "replica_age_seconds": replica_age,
            "share_ok": share_ok,
            "share_message": share_msg,
            "problems": problems,
            "healthy": not problems,
        }

    def check_share(self, share_path):
        """Is the shared folder actually reachable AND writable from this PC?

        Readable is not enough: a client that cannot WRITE cannot queue a single
        change, and read-only access is a normal way for share permissions to be
        misconfigured. So this writes a probe file and removes it.
        """
        if not share_path:
            return False, "no shared folder is configured"
        try:
            if not os.path.isdir(share_path):
                return False, f"cannot reach {share_path}"
            probe = os.path.join(share_path, f".str_probe_{uuid.uuid4().hex[:8]}")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("probe")
            os.remove(probe)
            return True, f"{share_path} is reachable and writable"
        except PermissionError:
            return False, (f"{share_path} is reachable but this PC may not write to it "
                           f"-- check the share permissions for this account")
        except OSError as e:
            return False, f"{share_path}: {e}"

    def designate_host(self, config):
        config.MODE = "host"
        config.ensure_host_id()
        config.save()
        return True, f"This PC designated as host (mode=host, id={config.HOST_ID})"

    @staticmethod
    def _app_exe():
        """Where FIU_System.exe is, seen from whichever exe is running this.

        NOT sys.executable. This code runs inside TWO different executables:
        in-process under FIU_System.exe --panel, and standalone as
        FIU_Control_Panel.exe. Assuming sys.executable is the app is only true
        in the first case; in the second, "Start host on this PC" launched a
        SECOND control panel. Both processes then shared one PyInstaller
        _MEIxxxxx extraction directory, and the one that exited first deleted
        it out from under the other -- "Failed to remove temporary directory"
        followed by a missing base_library.zip in the survivor.

        ponytail: sibling lookup, because build.bat ships both exes to the same
        folder and config.app_base_dir() already depends on that. Deliberately
        no fallback to sys.executable: that fallback IS the bug above. A
        missing app exe must surface as a plain "could not start" error.
        """
        return os.path.join(os.path.dirname(os.path.abspath(sys.executable)),
                            PanelController.APP_EXE)

    @staticmethod
    def _launch_cmd(*args):
        """How to start the app.

        From source that is `python flet_app/main.py <args>`. Packaged, there is
        no python.exe and no main.py on the machine at all, so the app exe is
        launched directly -- see _app_exe for why that is not sys.executable.
        Getting this wrong means the panel's start buttons do nothing on every
        client PC, which is exactly where they matter most.
        """
        if getattr(sys, "frozen", False):
            return [PanelController._app_exe(), *args]
        main_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "flet_app", "main.py")
        return [sys.executable, main_py, *args]

    @staticmethod
    def _survived(p, what):
        """Did the process we just spawned still exist a moment later?

        Popen returning without raising only proves Windows found the file. The
        app exits within a second on a PC with no database configured, and it
        is a windowed exe with nowhere to print why -- so the panel used to
        report "host started (pid N)" for a process that was already gone, and
        the operator went looking for a network problem that did not exist.
        """
        wait = getattr(p, "wait", None)
        if not callable(wait):
            return True, None          # injected test double with no lifecycle
        try:
            rc = wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            return True, None          # still running after 1.5s: it started
        return False, f"{what} exited immediately (code {rc})"

    def start_host(self, spawn=subprocess.Popen):
        try:
            p = spawn(self._launch_cmd("--host"),
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            return False, (f"could not start host: {e}. Is {self.APP_EXE} in the "
                           f"same folder as this Control Panel?")
        except Exception as e:
            return False, f"could not start host: {e}"
        alive, why = self._survived(p, "the host")
        if not alive:
            return False, why
        return True, f"host started (pid {getattr(p, 'pid', '?')})"

    def start_client(self, spawn=subprocess.Popen):
        """Launch the app normally (client/local mode)."""
        try:
            p = spawn(self._launch_cmd(),
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            return False, (f"could not start the app: {e}. Is {self.APP_EXE} in "
                           f"the same folder as this Control Panel?")
        except Exception as e:
            return False, f"could not start the app: {e}"
        alive, why = self._survived(p, "the app")
        if not alive:
            return False, why
        return True, f"app started (pid {getattr(p, 'pid', '?')})"

    def stop_host(self, killer=None):
        """Stop the host running on THIS PC.

        The pid comes from the heartbeat, but a pid alone is not enough: the
        heartbeat is on a shared folder, so it may well describe a host on a
        different PC. Killing by that pid would take out whatever unrelated
        process happens to hold that number here. The hostname must match.
        """
        hb = read_heartbeat(self.bus)
        if not hb:
            return False, "no host is publishing a heartbeat"
        import socket
        if (hb.get("hostname") or "").lower() != socket.gethostname().lower():
            return False, (f"the host is running on {hb.get('hostname')}, not this PC "
                           f"-- stop it there")
        pid = hb.get("pid")
        if not pid:
            return False, "the heartbeat carries no pid"
        try:
            if killer is not None:
                killer(pid)
            else:
                os.kill(int(pid), signal.SIGTERM)
            return True, f"asked the host (pid {pid}) to stop"
        except ProcessLookupError:
            return False, f"no process with pid {pid} -- the host is already gone"
        except Exception as e:
            return False, f"could not stop the host: {e}"

    def make_client_kit(self, dest_dir, share_path, exe_path=None):
        """Build a ready-to-copy folder for a client PC.

        Deploying a client used to mean: copy an exe, hand-write a config.json,
        get the UNC path and the JSON escaping right, and hope. Every one of
        those is a chance to produce a client that silently opens the setup
        wizard instead of connecting. This writes the folder so the operator's
        only job is copy and double-click.

        config.json is written WITHOUT a byte-order mark on purpose -- see
        Config.load; a BOM used to send the client back to the setup wizard.
        """
        if not share_path:
            return False, "no shared folder configured -- set that first"

        exe = exe_path
        if exe is None:
            # _app_exe, not sys.executable: run from FIU_Control_Panel.exe the
            # latter is the PANEL, and the kit shipped a folder whose README
            # told the user to double-click a diagnostic tool. No app in it.
            exe = self._app_exe() if getattr(sys, "frozen", False) else None
        if not exe or not os.path.isfile(exe):
            return False, (f"no {self.APP_EXE} to copy. Run build.bat first, then "
                           f"point at dist\\{self.APP_EXE}")

        try:
            os.makedirs(dest_dir, exist_ok=True)
            os.makedirs(os.path.join(dest_dir, "config"), exist_ok=True)
            shutil.copyfile(exe, os.path.join(dest_dir, os.path.basename(exe)))

            cfg = {
                "database_path": None,
                "backup_path": None,
                "session_timeout": 30,
                "max_login_attempts": 5,
                "mode": "client",
                "share_path": share_path,
                "host_id": None,
            }
            # encoding="utf-8" (no -sig): never write the BOM we had to teach
            # the loader to tolerate.
            with open(os.path.join(dest_dir, "config", "config.json"),
                      "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)

            with open(os.path.join(dest_dir, "READ ME FIRST.txt"),
                      "w", encoding="utf-8") as f:
                f.write(_CLIENT_KIT_README.format(share=share_path,
                                                  exe=os.path.basename(exe)))

            return True, f"client kit ready: {dest_dir}"
        except OSError as e:
            return False, f"could not build the client kit: {e}"

    # Deliberately NO shortcut-creation code here.
    #
    # Creating a .lnk normally means the WScript.Shell COM object, usually via
    # PowerShell -- which would put back the exact process-spawn pattern the
    # bank's EDR flagged, and the approval covering this work is for Python
    # only. Writing the .lnk format by hand instead was tried and REJECTED by
    # Windows (ShellExecute: "no application is associated"), so it is not
    # shipped: a shortcut that silently fails to open is worse than none.
    #
    # Instead: the app opens its own Control Panel from the login screen, and
    # starting at login is a documented drag-and-drop step (docs/SETUP.md).
    # Both are things Windows already does, with no code and no new file
    # format to get wrong.

    def startup_folder(self):
        """Where the operator drops a shortcut to start STR at login."""
        return os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                            "Windows", "Start Menu", "Programs", "Startup")

    def become_host_now(self, stale_seconds=60, force=False):
        return become_host(self.bus, self.db_path, self.host_id, stale_seconds, force)

    def run_integrity(self):
        return check_and_restore(self.db_path, self.backups_dir)

    def manual_backup(self):
        try:
            import time
            dest = os.path.join(self.backups_dir, f"fiu_{int(time.time() * 1000)}.db")
            tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".bak")
            src = sqlite3.connect(self.db_path); dst = sqlite3.connect(tmp)
            try:
                with dst:
                    src.backup(dst)
                dst.execute("PRAGMA journal_mode=DELETE")
            finally:
                dst.close(); src.close()
            os.replace(tmp, dest)
            return True, f"backup written: {os.path.basename(dest)}"
        except Exception as e:
            return False, f"backup failed: {e}"

    def list_backups(self):
        files = sorted(glob.glob(os.path.join(self.backups_dir, "*.db")), key=os.path.getmtime, reverse=True)
        return [os.path.basename(f) for f in files]

    def restore_backup(self, name, force=False):
        # Never restore over a DB a live host is actively serving: the host
        # reopens per command, so a swap landing between commands is clean, but a
        # command arriving mid-swap could read a half-written file (corruption on
        # a corruption-fatal app). Refuse unless the host is stale or force=True.
        if not force and not is_stale(read_heartbeat(self.bus)):
            return False, ("a live host holds the lease — stop the host (or promote "
                           "this PC with 'become host') before restoring")
        src = os.path.join(self.backups_dir, name)
        if not os.path.exists(src):
            return False, f"backup not found: {name}"
        try:
            tmp = self.db_path + ".restore-" + uuid.uuid4().hex
            shutil.copyfile(src, tmp)
            os.replace(tmp, self.db_path)
            for sfx in ("-wal", "-shm"):
                try:
                    os.remove(self.db_path + sfx)
                except OSError:
                    pass
            return True, f"restored from {name}"
        except OSError as e:
            return False, f"restore failed: {e}"
