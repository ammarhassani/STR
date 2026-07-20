# STR — Full End-to-End Test Plan (Run → Distribute → Operate)

Two layers:

- **Layer 1 — Automated simulation** (no VMs, no clicks): one command proves the
  whole deployment *machinery* — host bring-up, client join, onboarding, writes
  through the host, shared data, offline outbox, failover, self-update, hard
  reset. Run it on any machine (incl. this repo's CI).
- **Layer 2 — Real-VM validation**: a small VM lab (1 host + 2 clients) for the
  things a simulation *cannot* prove — the Flet GUI, the windowless `.vbs`
  launch, the Windows taskbar icon, and a genuine SMB share. Every step has an
  expected result and a pass box; an operator (or an agent driving the VMs) ticks
  them.

Layer 1 covers ~80% of the risk in seconds. Layer 2 is the final Windows sign-off.

---

## Layer 1 — Automated simulation (run these first)

From the repo root, with `python3.14` (the interpreter that has flet 0.28.3 +
bcrypt):

```bash
python3.14 tests_e2e_deployment.py     # the full deployment story (9 phases)
python3.14 tests_e2e_harness.py        # 184 business/RBAC/concurrency checks
python3.14 tests_host_cluster.py       # host/queue/command-RPC + onboarding-via-host
python3.14 tests_updater.py            # host-publish → client-consume, rollback, offline
python3.14 tests_hard_reset.py         # wipe vs preserve, single fresh admin
python3.14 tests_i18n.py               # language machinery + persistence
python3.14 tests_dropdown_i18n.py      # bilingual values, arb_staff/second-reason cleanup
python3.14 tests_onboarding.py         # two-way handshake
python3.14 tests_dashboard_config.py   # config-driven BI, read-only widget SQL
python3.14 tests_prosecutor.py         # adversarial security (must be 0 vulns)
python3.14 tests_conformance.py tests_ui_driver.py tests_review_screen.py \
           tests_field_labels.py tests_gender_normalization.py tests_intelligence.py \
           tests_xlsx.py tests_log_export.py tests_numbering.py tests_roles.py \
           tests_security.py tests_setup_screens.py tests_dropdown.py
```

**Pass gate (Layer 1):** every suite prints `ALL PASS` / `0 FAILED`; e2e
`184/184`; prosecutor `0 / 35`; conformance `48/48`; ui_driver `0/…`; cluster
`CLUSTER FAILURES: 0`; deployment sim `DEPLOYMENT SIMULATION: ALL PASS`.

### What `tests_e2e_deployment.py` simulates (each "PC" = a dir, the "SMB share"
### = a temp folder, driving the REAL host/queue/replica/failover/updater code)

| Phase | Proves |
|-------|--------|
| P1 Host bring-up | init DB → migrate → publish replica + heartbeat to the share |
| P2 Client join | bootstrap the read replica; client reads localized dropdowns |
| P3 Onboarding | admin creates a user ID → user self-registers name+password → logs in — all via the host |
| P4 Client write | reserve + create a report through the host; refreshed replica shows it |
| P5 Second client | client B sees the report client A created (shared data) |
| P6 Host offline | write queues in the client outbox → drains to the host on return |
| P7 Failover | operator promotes client B; term bumps (no split-brain); clients hit the new host |
| P8 Self-update | host publishes a code snapshot to the share; client copies it; local config survives |
| P9 Hard reset | wipe reports, keep config, one fresh admin |

**Cannot be simulated (→ Layer 2):** the GUI itself, the windowless `.vbs`
launch, the Windows taskbar/dock icon, and a real SMB filesystem's locking/latency.

---

## Layer 2 — Real-VM validation lab

### Lab topology (smallest that proves distribution)

- **VM-HOST** — Windows, the designated host workstation.
- **VM-C1**, **VM-C2** — Windows clients.
- **SHARE** — one folder reachable by all three as the same UNC/mapped path
  (e.g. `\\VM-HOST\STR_data` or a mapped `Z:\STR_data`). A real SMB share, not a
  local folder — this is the point of the lab.

Each VM: Python 3 on PATH (so `python` / `pythonw` exist), git configured with
read access to the repo, the repo cloned to the same folder (e.g. `C:\STR`).

> An agent can drive this: provision 3 VMs, run the numbered commands, capture
> screenshots at the 👁 steps, and diff against expected. The 👁 steps are the
> only ones needing a human/vision check.

### Phase 0 — Prove the share is real (do this before A)

`deploy\smb_lab.ps1` sets the share up and then checks it. Run it elevated on
the host, and as a normal user on each client:

```powershell
# on the HOST pc, as administrator
.\deploy\smb_lab.ps1 -Role Host
# on EACH client pc
.\deploy\smb_lab.ps1 -Role Client -HostName VM-HOST
```

It verifies the client can write to the share root (STR needs that for
`str_bus`), that a rename lands atomically, what the share does when you replace
a file another PC holds open, how slow it really is, and that each PC can see
the markers the others left.

> **A loopback UNC path is not a share.** Measured on the dev machine,
> `\localhost\C$`, `\<own-LAN-IP>\C$` and `\<own-hostname>\C$` all run at
> **1.0x local-disk speed** - Windows short-circuits a connection to itself. Any
> run where the client and the share are the same PC proves nothing about
> locking, latency or a dropped session, and the script warns when it detects
> that. Phases A-K need two machines.

The failure modes a real share produces are covered deterministically by
`tests_smb_faults.py`, which injects the actual Windows error codes
(ERROR_SHARING_VIOLATION, ERROR_ACCESS_DENIED, ERROR_NETNAME_DELETED,
ERROR_UNEXP_NET_ERR) into the file operations STR performs against the share.
That suite found a real defect: the host's replica publish survived a locked
file but **crashed when the share dropped**, because only `PermissionError` was
being retried.

### Phase A - First install on the HOST (once per site)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| A1 | On VM-HOST: `git clone <repo> C:\STR` | repo present | ☐ |
| A2 | `cd C:\STR && python flet_app\main.py` | 👁 setup **wizard** appears (first run, no config yet) | ☐ |
| A3 | Wizard → choose **Host**, set DB path (local), set SHARE = the UNC path | wizard completes, no error | ☐ |
| A4 | Double-click `deploy\start_host.vbs` | 👁 **no** CMD window appears; `logs\host.log` is written and grows | ☐ |
| A5 | Check the share | `<SHARE>\str_bus\replica\fiu_ro.db` and `\host\heartbeat.json` exist | ☐ |
| A6 | Add `start_host.vbs` to Startup (shortcut in `shell:startup`) | shortcut present | ☐ |

### Phase B — First login + go-live reset

| # | Step | Expected | ✅ |
|---|------|----------|----|
| B1 | `python flet_app\main.py` on VM-HOST, log in `admin` / `admin123` | 👁 forced password-change dialog | ☐ |
| B2 | Set a new admin password | login proceeds to the dashboard | ☐ |
| B3 | (Optional, if test data exists) stop the host, run `python reset_to_production.py`, type `RESET` | backup written; reports wiped; config kept; single admin | ☐ |
| B4 | Restart `start_host.vbs` | host republishes; clients will see the clean DB | ☐ |

### Phase C — Client setup (each client PC)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| C1 | On VM-C1: `git clone <repo> C:\STR` | repo present | ☐ |
| C2 | `python flet_app\main.py` → wizard → **Client**, SHARE = same UNC path | wizard completes | ☐ |
| C3 | Launch `deploy\start_client.vbs` | 👁 app window opens; **no** CMD window | ☐ |
| C4 | If the host is up | 👁 no "host offline" banner; data loads | ☐ |
| C5 | Repeat C1–C4 on VM-C2 | second client online | ☐ |

### Phase D — Two-way onboarding handshake (admin never sets passwords)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| D1 | On VM-HOST (admin): Users → Add User → set **User ID + role only** (e.g. `reporter7`) | saved; list shows **"Pending registration"** badge | ☐ |
| D2 | On VM-C1: at login, enter `reporter7` | 👁 **"complete your registration"** dialog (name + password) | ☐ |
| D3 | Set full name + password, submit | auto-logs-in as reporter7 | ☐ |
| D4 | On VM-HOST: Users list | reporter7 now shows **Active**, full name populated | ☐ |
| D5 | Admin → edit reporter7 → **Reset password** | reporter7 flips back to "Pending"; re-register works at next login | ☐ |

### Phase E — Multi-PC data sharing (the core promise)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| E1 | On VM-C1 (an agent): reserve numbers, create a report, submit for approval | success; report appears in "My Work" → Pending | ☐ |
| E2 | On VM-C2 (a supervisor): open Approvals within a few seconds | 👁 the C1 report is in the queue | ☐ |
| E3 | C2 approves it | approval succeeds | ☐ |
| E4 | Back on VM-C1: refresh My Work | the report moved to **Approved**; if reworked, the reviewer's message shows | ☐ |
| E5 | Any client: open Reports list | 👁 all clients show the same rows | ☐ |

### Phase F — Bilingual + RTL (per-user)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| F1 | On any client, click the **globe** in the header → العربية | 👁 the whole shell flips to Arabic, **right-to-left** | ☐ |
| F2 | Open a report form | 👁 field labels, tabs, buttons, dropdown values in Arabic (gender = ذكر/أنثى, etc.) | ☐ |
| F3 | Second reason of suspicion | 👁 dropdown of the **Arabic** formal typologies (Arabic in both languages) | ☐ |
| F4 | Admin → Dropdowns → add a value | 👁 **two** fields: Value (English) + Value (Arabic) | ☐ |
| F5 | Switch back to English | 👁 everything English again; a report entered in Arabic still reads correctly (English-canonical storage) | ☐ |
| F6 | Log out / in as a different user with the other language | each user keeps their own language | ☐ |

### Phase G — Host offline / queued writes

| # | Step | Expected | ✅ |
|---|------|----------|----|
| G1 | Stop `start_host.vbs` on VM-HOST | host down | ☐ |
| G2 | On VM-C1, try to create/submit a report | 👁 host-down banner; a "queued" toast; the app stays usable read-only | ☐ |
| G3 | Restart `start_host.vbs` | within seconds the banner clears and the queued write applies (visible on refresh) | ☐ |

### Phase H — Failover drill (host PC dies)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| H1 | Hard-stop VM-HOST (power off) | clients show host OFFLINE/STALE | ☐ |
| H2 | On VM-C2: `deploy\start_panel.bat` → confirm Host = OFFLINE | panel shows offline | ☐ |
| H3 | Panel → **Become Host Now** (single operator only) | promotes; term bumps | ☐ |
| H4 | `deploy\start_host.vbs` on VM-C2 | VM-C2 now serves; other clients reconnect + drain their outbox | ☐ |
| H5 | Power VM-HOST back on, start it as a **client** | it detects the newer term and does NOT serve (no split-brain) | ☐ |

### Phase I — Self-update rollout (push once, clients follow)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| I1 | Push a small visible change to the repo | remote updated | ☐ |
| I2 | On the HOST: relaunch `start_host.vbs` (runs `updater.py`) | host `git pull`s + publishes `<SHARE>\app\<version>\` + `latest.txt` | ☐ |
| I3 | On VM-C1/C2: relaunch `start_client.vbs` | client copies the new snapshot from the share; the change is visible; local config/db untouched | ☐ |
| I4 | Confirm offline safety: cut a client's share access, relaunch | it logs the skip and runs its current code (never blocks) | ☐ |

### Phase J — Windowless + icon (cosmetic but required)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| J1 | While host + clients run via `.vbs` | 👁 **no** black CMD windows anywhere; only the app window + logs | ☐ |
| J2 | Taskbar / title bar of the app | 👁 shows the **bank logo**, not the Flet bird | ☐ |
| J3 | Login screen + sidebar + Help→About | 👁 the bank logo renders | ☐ |

### Phase K — Backups / integrity / restore (ops)

| # | Step | Expected | ✅ |
|---|------|----------|----|
| K1 | On HOST: `start_panel.bat` → Backup | backup written to `<SHARE>\...\backups\` | ☐ |
| K2 | Panel → Integrity Check | "Integrity OK" | ☐ |
| K3 | Stop host → Panel → Restore (a known-good backup) → restart host | data reverts; clients see restored data | ☐ |

---

## Roles for the agent-driven run

- **Automatable by an agent (no vision):** all Layer-1 suites; on VMs — the git
  clone, wizard driven via config injection (`config\config.json`) instead of
  clicking, starting `.vbs`, checking files on the share, the failover/panel CLI,
  the updater publish/consume, log assertions, hard reset.
- **Needs a vision check (👁):** wizard appearance, no-CMD-window, the logo,
  RTL layout, the bilingual field/dropdown text, the onboarding dialog, the
  host-down banner. An agent captures a screenshot at each 👁 and diffs/OCRs it.

---

## Layer 1.6 — Warzone (`tests_warzone.py`)

`python tests_warzone.py [seconds]` builds one host process plus **21 client
processes** (2 admins, 4 supervisors, 11 agents, 4 reporters), each a separate
install talking over the real folder queue, and has every persona attack the
rules of its own role: reporters try to write, agents try to approve, everyone
tries to act as somebody else, and malformed data is pushed at every entry
point. A defect is anything that succeeded when the BRD says it must not (or
was refused when it must be allowed), plus nine post-run DB invariants.

It found, and the same run now proves fixed:

| Class | Defect |
|-------|--------|
| IDENTITY | `reserve_block(username)` / `transfer_numbers(from_user)` took the acting user as an argument the host never checked — an agent transferred another agent's reserved numbers to itself |
| RBAC | `reserve_block` had no permission check at all: a **reporter** could burn official FIU report numbers, punching permanent gaps in the regulator-facing sequence |
| STATUS-FORGERY | `approval_status` was writable through `update_report`, so an author could mark their **own** report `approved` with no approver, or roll a decided report back to `draft` |
| WORKFLOW | a report under approval could be edited by its author, so the approver decided on text they never saw; a rejected report was equally editable |
| WORKFLOW | `reject_report` accepted an **empty comment** — work came back to an agent with no reason given (the requirement was enforced only in the UI) |
| VALIDATION | `31/31/2026`, `yesterday`, a far-future date, a negative amount and a 2-digit CIC all reached the database |
| FILTER | the date-range filter compared `DD/MM/YYYY` text against `YYYY-MM-DD` bounds, so a period filter returned the wrong reports — a 1900–1901 range returned 36 live reports |
| AUDIT | `update_report` created no version, so any edit not made through a dialog left no history; `clear_logs` was ungated and unaudited |

**Pass gate:** `distinct defects: 0`, `invariant failures: 0`, and all personas
finished.

---

## Layer 1.5 — Single-Windows-PC lab (run 2026-07-18)

Between the two layers there is a middle run that needs no VMs: three clones of
the repo on ONE Windows PC (HOST, C1, C2) plus a local folder standing in for the
share, each started through its REAL launcher. It cannot prove SMB or the GUI,
but it exercises the actual multi-process launch path — and it found four
Windows-only defects the headless suites could not:

| Found | Defect |
|-------|--------|
| A4 | `deploy\*.vbs` launched the app **exactly once per PC**: in a cmd chain `if not exist logs mkdir logs & <rest>` swallows `<rest>`, so once `logs\` existed nothing ran and the host silently never started again |
| E/G | `QueueTransport._atomic_write` raised `PermissionError` (WinError 5) publishing a response while the client polled that path — the response was dropped and the client waited out its full timeout |
| G3 | a queued write never drained: it carried the token of the session that died with the old host, and the client then read the **stale response file** from that failed attempt on every later attempt |
| A4 | `--host` with a missing DB died on `AttributeError` deep in `read_lease` instead of saying the database is missing |

Proven on that lab after the fixes: A4, A5, C-equivalent client bring-up, D/E
data sharing across two client installs, G1–G3 offline→queue→drain, I2 updater
publish to the share, K1 backups — plus exactly-once apply across a real host
restart (2 reports, 1 duplicate-free resubmit).

Still Layer-2-only: real SMB locking/latency, the GUI, the taskbar icon, RTL
rendering, and the 👁 checks below.

> Note: `tests_e2e_harness.py` check 17 asserts create p95 < 2s. On a busy
> workstation this fails on load alone (measured 1.3s idle, 3.0s under load on
> the same commit) — re-run it on an otherwise idle machine before treating it
> as a regression.

---

## Sign-off

- [ ] Layer 1: every suite green (paste the summary lines).
- [ ] Layer 2: every ✅ box ticked, 👁 screenshots attached.
- [ ] Known residuals accepted: Arabic FIU-term review (catalogs + `help.body.*`),
      macOS dock icon (irrelevant on Windows).
