# STR Host & Operator Runbook

## Overview

The STR (Suspicious Transaction Reports — FIU / AML compliance) system operates with a **single designated host workstation** that owns the primary database and publishes replicas to a shared folder. All other workstations operate as clients, reading from the replica and queuing writes through the shared transport.

This runbook covers setup, daily operations, failover procedures, and known limitations for operators responsible for STR deployment and maintenance.

---

## ⭐ Do This First — Golden Path

If you read nothing else, do these steps in order. Everything below this section is detail and edge cases.

### One-time, once per site

1. **Pick the host PC.** One workstation that stays on during business hours. It owns the database.
2. **Pick the shared folder.** A network path every PC can reach (e.g. `Z:\STR_data` or `\\server\STR_data`). The host writes a read-only replica there; clients read it.
3. **On the host PC:**
   1. `git pull` the latest code into the STR folder.
   2. Run `python flet_app\main.py` once → the setup wizard opens → choose **Host**, enter the shared folder path.
   3. Double-click `deploy\start_host.bat` → the host starts publishing. Leave it running.
   4. Add `start_host.bat` to Startup (see *Initial Setup → Enable automatic startup*) so it relaunches after login.
4. **On each client PC:**
   1. `git pull` the latest code.
   2. Run `python flet_app\main.py` once → wizard → choose **Client**, enter the **same** shared folder path.
   3. Launch normally from then on — no scripts needed.
5. **First login (any PC):** username `admin`, password `admin123`. You are forced to change it immediately. Then create the real users (Users screen).

### Every business day

- **Host PC:** confirm `start_host.bat` is running (a console window titled host). If the PC rebooted, log in once — Startup relaunches it.
- **Anyone:** if writes seem stuck, open the panel (`deploy\start_panel.bat`) → check **Host = ONLINE** and **queue near 0**.

### When you change the code (new feature / fix)

- `git pull` on the host **and** each client. Restart the app (and `start_host.bat` on the host). Config-driven dashboard widgets and dropdowns update automatically from the shared database — no per-PC editing.

### If the host PC dies

- On a backup PC: `deploy\start_panel.bat` → confirm **Host = OFFLINE/STALE** → **Become Host Now** → `start_host.bat`. (Only one operator does this — see *Failover*.)

### Going from testing to real use

- Run **Hard Reset** (see that section) on the host to wipe all test reports/users and start clean, keeping your dropdowns, fields, and dashboard widgets.

---

## What Runs Where

### Host Workstation (One Per Deployment)

- **Role:** Exclusive database owner and publisher
- **Process:** Runs `python flet_app\main.py --host` (headless, no UI)
- **Data Responsibility:**
  - Maintains the authoritative SQLite database on local disk (`local.db`)
  - Publishes a read-only replica to the shared folder (`replica/fiu_ro.db`) after each transaction
  - Publishes a heartbeat signal to the shared folder (`host/heartbeat.json`) continuously — after each command and on every idle poll (sub-second)
- **Availability:** Must remain online during business hours; gracefully handles client requests even if temporarily unreachable (clients queue writes locally)

### Client Workstations (All Others)

- **Role:** Read-only viewers and write requesters
- **Process:** Runs the normal STR UI (`python flet_app\main.py` with no flags)
- **Data Access:**
  - Reads the replica from the shared folder (updated by the host after every transaction)
  - Sends write requests to a queue on the shared folder, consumed by the host in order
- **Queuing:** If the host is unreachable, writes are queued locally and automatically sent when the host returns online

---

## Initial Setup

### Setup on the Host PC (First Time Only)

1. **Launch the setup wizard:**
   - Run the STR application: `python flet_app\main.py`
   - The wizard will prompt you to designate this PC as the Host

2. **Configure the shared folder path:**
   - When prompted, provide the full path to a shared network folder accessible from all workstations (e.g., `\\shared-server\STR_data` or `Z:\STR_data`)
   - Ensure the operator account has read/write access to this folder

3. **Launch the host service:**
   - Run `deploy\start_host.bat` to start the host process
   - The host will begin publishing the replica and heartbeat to the shared folder
   - You should see console output confirming the database is initialized

4. **Enable automatic startup:**
   - Right-click on `deploy\start_host.bat` → Create Shortcut
   - Press `Win+R`, type `shell:startup`, and press Enter to open the Startup folder
   - Move the shortcut into the Startup folder
   - On the next Windows login, the host will automatically start (see Limits: Cold Reboot Login Requirement)

### Setup on Each Client PC

1. **Launch the setup wizard:**
   - Run the STR application: `python flet_app\main.py`
   - The wizard will prompt you to configure this PC as a Client

2. **Configure the shared folder path:**
   - Provide the same shared folder path used on the host PC (e.g., `\\shared-server\STR_data`)
   - Verify you have read access to the folder

3. **Start the application normally:**
   - Launch STR normally; no additional startup scripts are needed
   - The app will connect to the replica and begin queuing writes if offline

---

## Daily & Weekly Operational Checks

### Opening the Operator Panel

The operator panel provides visibility and control over the STR deployment. `status`, `become host`, and failover can be run from any workstation, but **maintenance actions (backup, integrity check, restore) must be run on the HOST PC** — on a client PC they act on that PC's local replica copy, not the authoritative database. Launch the panel:

```
deploy\start_panel.bat
```

Or run directly:

```
python flet_app\main.py --panel
```

### Daily Checks (Via Panel)

After the host PC starts each morning, perform these checks:

1. **Verify Host Status:**
   - Open the panel → View "Host Status"
   - Confirm it shows: **Host ONLINE**
   - If OFFLINE or STALE: Investigate the host PC; restart if needed (see Failover)

2. **Check Queue Depth:**
   - In the panel → View "Queue Status"
   - Queue should show **near 0** (a few pending writes is normal after startup; it clears within seconds)
   - If queue grows continuously: The host may not be consuming writes; restart the host service

3. **Inspect Recent Activity:**
   - Review the last few transactions in the panel to ensure writes are flowing normally

### Weekly Maintenance (Via Panel)

1. **Run a Manual Backup:**
   - Open the panel → Select "Backup"
   - Confirm: **Backup completed successfully**
   - This snapshot can be restored if data corruption is discovered

2. **Verify Backup Location:**
   - Backups are stored alongside the replica (check the shared folder's `backups/` subfolder)
   - Ensure disk space is sufficient for at least 4 weekly backups

### Monthly Maintenance (Via Panel)

1. **Run an Integrity Check:**
   - Open the panel → Select "Integrity Check"
   - Wait for completion; it scans the replica for corruption
   - Expected result: **Integrity OK** or **Ready for restore** (if corruption found)
   - If corruption is detected, follow the Restore from Backup procedure (next section)

---

## Failover: Become Host (When Host PC Is Down)

When the host PC is unavailable or unresponsive, another workstation must become the new host. This procedure is safe and automatic for the old host if it returns later.

### When to Failover

- Host PC is physically offline or locked
- Heartbeat in panel shows OFFLINE or STALE (the client treats a heartbeat older than ~60 seconds as stale)
- Queue is growing and not being consumed (no replica updates for >5 minutes)

### Procedure: Promote a Backup PC to Host

1. **On the Backup PC (nominated second workstation):**

2. **Open the operator panel:**
   ```
   deploy\start_panel.bat
   ```

3. **Confirm the current host is unreachable:**
   - In the panel, verify: Host Status = OFFLINE or STALE
   - Do NOT proceed if Host Status = ONLINE (to avoid split-brain)

4. **Initiate failover:**
   - In the panel, select "Become Host Now"
   - Confirm the operation; the system will:
     - Adopt the latest replica as the new authoritative database
     - Increment the term (a version number) to ensure the old host recognizes it is no longer primary
     - Redirect all future writes to this PC

5. **Start the host service on this PC:**
   - Run `deploy\start_host.bat` (or add it to Startup for next time)
   - Console output should confirm the host is online and publishing the replica

6. **Verify recovery:**
   - Open the panel again
   - Confirm: Host Status = ONLINE and this PC's hostname is shown as the host
   - Clients will automatically begin draining their queued writes to the new host

### What Happens If the Old Host Comes Back Online

- The old host will detect the newer term in the heartbeat
- It will automatically **step down and stop** — the headless `--host` process exits (it does not keep serving), so there is never a second writer
- That PC can then be used normally as a client (run the app with no flags); no manual "demotion" step is needed

### IMPORTANT: Single-Operator Promotion

**Only ONE operator should promote ONE backup to host.** Simultaneous promotion by multiple operators (e.g., two people running "Become Host Now" at the same time) is **not supported** and may cause data inconsistency. Always coordinate:

- Designate a secondary operator and agree on the failover process
- Only the designated operator runs "Become Host Now"
- The new host is stable and safe; all clients will reconnect

---

## Restore from Backup

Backups are snapshots of the replica taken at a point in time. Use restoration to roll back from corruption or bad data.

### When to Restore

- Monthly integrity check detects corruption
- A client reports incorrect data that needs reversal
- A recent backup is known to have good data

### Procedure: Restore a Backup

1. **Open the operator panel:**
   ```
   deploy\start_panel.bat
   ```

2. **List available backups:**
   - In the panel, select "List Backups"
   - Backups are listed with timestamps; choose the newest one known to be good

3. **Restore the selected backup (on the HOST PC):**
   - **First stop the host:** close the `--host` window (or end the process) on the host PC. Restoring while the host is actively serving is refused by the panel — the host must be stopped so nothing reads the database mid-swap.
   - In the panel, select the backup and choose "Restore" — it atomically replaces this PC's local database with the backup snapshot.
   - **Restart the host:** run `deploy\start_host.bat` again. It republishes the restored database as the replica, and clients see the restored data on their next refresh.
   - Note: restore only swaps the data; it does not change the host term. Always run it on the host PC (or promote this PC first with "Become Host Now", then stop/restore/restart).

4. **Verify the host is online:**
   - After restoration, confirm in the panel: Host Status = ONLINE
   - The host should be publishing writes to clients normally

### Automatic Restoration on Startup

- If the host detects corruption during initialization, it will automatically restore the newest backup
- Manual restore is needed only if the operator explicitly chooses to roll back to a specific point in time

---

## Session Timeout & Re-Login

### Idle Session Behavior

- Operator logins on the host expire after **30 minutes** of inactivity
- When a session expires, the user is logged out and must re-login

### What Remains Unaffected

- Queued writes in the outbox are **not** affected by session timeout
- When the operator logs back in, the host continues processing queued writes
- No data loss occurs; it is purely a UI-level session refresh

### Procedure: Re-Login After Timeout

- If prompted to login again after 30 minutes of inactivity, simply enter credentials again
- All queued operations continue to be processed by the host

---

## Hard Reset (Test → Production)

After you finish testing with sample data, wipe everything transactional and
hand the system a clean slate — **without** losing the configuration you set up
(dropdown values, custom fields, dashboard widgets, system settings).

### What it does

- **Deletes:** all reports, approvals, versions, reserved/queued numbers, record
  locks, activity/audit/session logs, notifications, saved filters, and the
  write queue.
- **Resets users** to a single fresh `admin` (temporary password `admin123`,
  forced change at first login) — all test users are removed.
- **Resets the host lease** to an unclaimed state.
- **Keeps:** dropdowns, fields, dashboard widgets, and all system settings.
- **Backs up first:** writes `<database>.pre-reset-<timestamp>.bak` next to the
  database before touching anything.

### Procedure

1. **On the HOST PC**, stop the host: close the `start_host.bat` window (nothing
   should be reading or writing the database during a reset).
2. From the STR folder, run:
   ```
   python reset_to_production.py
   ```
   It shows the target database, asks you to type `RESET` to confirm, backs the
   database up, then wipes it.
   - Add `--yes` to skip the typed confirmation (for scripted use).
   - Add `--db PATH` to target a specific database file.
3. **Restart the host:** run `deploy\start_host.bat` again so it republishes the
   clean database to clients.
4. **Log in** as `admin` / `admin123`, change the password, and create the real
   users. You are now in production.

> ⚠️ This is irreversible for the wiped data (the pre-reset backup is your only
> undo). Only run it on the host, against the authoritative database, when you
> genuinely mean to discard all reports.

---

## Known Limitations

### Cold Reboot Requires Manual Login

- **Issue:** Windows Startup tasks run *after* user login, not at boot time.
- **Scenario:** After a cold power-on, the host PC is booting for the first time since the designated operator set it up.
- **Behavior:** The start_host.bat shortcut in the Startup folder will only trigger once the operator logs in.
- **Mitigation:** After a cold reboot, an operator must manually log in once; the host will then auto-start. For fully unattended operation, deploy the host on a workstation that never reboots or use a scheduled task (advanced setup, not covered here).
- **Impact:** The first client attempting to write after a cold reboot will briefly queue the write until the operator logs in and the host starts.

### Simultaneous Promotion Is Out of Operational Model

- **Issue:** Two operators cannot simultaneously promote two different backup PCs without risk of inconsistency.
- **Scenario:** Host is down; two operators each run "Become Host Now" on different workstations at the same time.
- **Behavior:** Both will try to become the host; the term-based protocol resolves one as primary, but the system is bounded and self-reconciling (no data corruption), though it is not ideal.
- **Mitigation:** Coordinate failover. Designate one secondary operator; only they run "Become Host Now". The process is fast (< 30 seconds); a single operator can handle it.
- **Impact:** Avoid this scenario through operational discipline.

### Host PC Must Have Persistent Database & Share Access

- **Issue:** If the host PC loses access to its local database or the shared folder, it cannot operate.
- **Scenario:** Host storage fails; shared folder becomes unreachable (network/credentials/permissions).
- **Behavior:** The host stops publishing updates; clients will see a stale heartbeat and should failover.
- **Mitigation:**
  - Ensure the host PC has reliable storage (SSD or redundant disk).
  - Ensure share access is stable (test with `net use` or File Explorer before deployment).
  - Set up periodic backups to a separate location (USB drive, cloud storage) for disaster recovery.
- **Impact:** Treat the host PC's hardware and network connectivity as critical infrastructure.

---

## Troubleshooting Quick Reference

| Symptom | Check | Action |
|---------|-------|--------|
| Host shows OFFLINE in panel | Is host PC powered on? Can you ping it? | Power on host; run `start_host.bat` manually |
| Queue grows but never decreases | Is host consuming writes? | Restart `start_host.bat` on host PC |
| Integrity check fails | Is corruption present? | Run "Restore" to recover the newest good backup |
| Client gets "Connection Timeout" | Is shared folder accessible? | Verify network path and credentials; check firewall |
| Host stepped down unexpectedly | Did another PC become host? | Check panel; if yes, that PC is now primary (expected after failover) |

---

## Summary for Daily Operator

1. **Morning:** Open panel, verify Host = ONLINE, queue near 0.
2. **Weekly:** Run manual backup and verify completion.
3. **Monthly:** Run integrity check; if fails, restore a known-good backup.
4. **If host down:** Open panel on a backup PC, run "Become Host Now", then `start_host.bat`.
5. **Cold reboot:** Log in once to trigger Startup folder items.

All procedures are accessible through the operator panel (`deploy\start_panel.bat`) and can be completed in minutes with no special tools or command-line expertise required.
