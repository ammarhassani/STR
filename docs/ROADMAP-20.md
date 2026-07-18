# STR — The 20 (plan of record)

Ground rules: **one item at a time, to 100% — domain-correct AND technically
tested — before the next.** UI items also need a visual confirm from the owner.
Nothing here is "done" until it is proven end to end.

Cross-cutting facts already settled:
- **Platform = native desktop** (flet client vendored in-repo, seeds offline;
  `STR_VIEW=web` fallback). Shortcuts work again.
- **Reservation stays** ("$100-bill": a number is owned, never deleted,
  non-expiring, tied to its assignee until acted on — create a report or
  transfer it).
- **Roles (target):** reporter = read/export only · agent = create/reserve/
  submit/own-queue · supervisor = agent + approve/reject/rework + message ·
  admin = everything.
- **BI is config-driven:** widgets are admin-authored read-only SQL stored as
  rows in the shared DB → reach every client on refresh → no app reship.

Status legend: ☐ not started · ◐ in progress · ☑ done+tested

---

1. **Select-all in reservation management** — ☑ (header "Select all" checkbox toggles every listed number for transfer; two-way sync — checking all individually turns the header on, and it reflects partial selection; ui_driver guards)
   *Ask:* bulk-select numbers in the reservation dialog.
   *Do:* add "Select all / Clear all" to the number list used for transfer.
   Small UI on top of the existing owned-block reservation.

2. **Agent work queues (find my reworked/returned reports)** — ☑ (My Work view: Returned-for-Rework / Draft / Pending / Approved lanes, own reports only, counts, click-to-edit; nav gated on add_report; route+title wired; lane grouping + cross-user isolation tested)
   *Ask:* reworked reports are unfindable.
   *Do:* build an agent **"My Work"** view with clear lanes — Draft, Returned/
   Rework, Pending Approval, Approved — with counts. Rework lane is front and
   center. (Depends on #8 roles + #11 messages.)

3. **Submit-for-approval auto-saves (no extra friction)** — ☑ (Submit validates+saves+snapshots then submits, one click; edit persists through rework->resubmit; tested)
   *Ask:* submitting shouldn't need a separate Save.
   *Do:* the Submit action saves the current form first, then submits, as one
   step.

4. **Productivity chart on the dashboard** — ☑ (delivered via the config-BI engine #17: seeded rework rate, approvals-per-month, top entities, classification split, repeat-CIC/account tables; admin can add per-agent/throughput widgets with no reship)

5. **Duplicate-CIC is an INFORMATION banner, never a blocker** — ☑ (new IntelligenceService.cic_history + on-blur non-blocking info banner under CIC; shows count, distinct entities, total_transaction sum + min–max, days since last, pending count, classifications, then the recent reports; never touches validate_form; tests_intelligence.py)

6. **Log export is broken ("logs ready for export", nothing happens)** — ☑ (was a TODO stub; now writes a timestamped UTF-8-BOM CSV via new utils.export.export_logs — all columns, Arabic-safe, union of keys — to Downloads/home, then offers to open the folder like the reports export; tests_log_export.py + ui_driver guards)
   *Ask:* fix it.
   *Do:* diagnose + fix the log-export handler so it actually writes the file.

7. **Reporter sees an Add-Report button it can't use (misleading)** — ☑ (dialog refuses on add_report; Ctrl+N + reports-view + header all gated; reporter gets a clean message, not the form)
   *Ask:* honest affordances.
   *Do:* with the role rework (#8), reporter = read/export only; hide Add-Report
   and any action a reporter can't perform.

8. **Agents reserve their own numbers + new `supervisor` role** — ☑ (role+RBAC+approval routing+SoD+migration all tested in tests_roles.py; nav+role-picker wired)
   *Ask:* agent keeps reservation; move approvals to a supervisor = agent +
   approval.
   *Do:* add the `supervisor` role (migration + RBAC), route approvals/rework to
   supervisors, keep agents reserving their own numbers. Foundational for
   #2/#3/#7/#11.

9. **Review screen: gender greyed out, value not printed** — ☑ (locked review shows gender as a readable read-only field like every other field; edit mode swaps to a constrained dropdown sourced from live gender values UNIONED with the stored value, so a review never blanks recorded data even across language/config changes; `review_field_options` pure helper + tests_review_screen.py)
   *Note:* uncovered a systemic gender-values inconsistency (schema CHECK + dropdown_config seed Arabic ذكر/أنثى, seed_dropdowns.py seeds English Male/Female, form sources from dropdown_service) — the review fix is robust to it, but the three-way source mismatch is a separate landmine to reconcile (own item, TBD).

10. **Bigger review screen** — ☑ (review dialog 650x520 -> 920x760, form viewport 280 -> 480, fields 280 -> 300; 31 fields now reviewable without cramped scrolling; ui_driver guards)
    *Ask:* more content visible.
    *Do:* enlarge the review/report dialog (width/height + layout).

11. **Agent sees the supervisor's message on a reworked report** — ☑ (get_review_comment surfaces the latest rework/reject comment + reviewer; shown as a red banner atop the edit dialog AND on each My Work rework card; tested)
    *Ask:* read the reviewer's note.
    *Do:* surface the rework comment on the report inside the agent's queue (#2)
    and on the report view.

12. **Kill the "-- Select --" placeholder trap** — ☑ (baked into SD: empty-key options dropped, hint instead)
    *Ask:* users pick the empty placeholder; app then reads a bad value.
    *Do:* no selectable empty option — use non-committable hint text; required
    dropdowns enforce a real choice; edit-mode defaults to the current value
    ("keep current"). Baked into the custom searchable dropdown (#SD).

13. **Second reason of suspicion not editable** — ☑ (root cause: rendered as a constrained dropdown while the schema declares it TEXT and the column is TEXT — a narrative like the first reason; now a free-text multiline field identical to the first reason, saved via get_value; dead second_reasons fetch removed; ui_driver structural guards)

14. **Rapid-repeat account banner (multiple entries on one account, 0–2 days)** — ☑ (IntelligenceService.account_rapid_repeat windows same-account reports on report_date ±2 days; on-blur non-blocking warning banner listing the repeats; ≥1 other report in window = structuring signal; shares the #5 layer; tests_intelligence.py)

15. **Numbering: drop the grace period; clean month rollover** — ☑ (calendar-driven; grace + manual close removed everywhere; rollover + $100-bill persistence proven in tests_numbering.py)
    *Ask:* month closes → new sequence from 1; reserved numbers stay with owners.
    *Do:* remove the grace-period logic in `report_number_service`; `_active_month`
    = true current calendar month; new reservations start `YYYY/MM/001`;
    already-reserved numbers keep their reservation-month prefix + owner until
    acted on. Reservation itself untouched.

16. **Export must be xlsx** — ☑ (zero-dependency stdlib xlsx writer utils/xlsx_writer.py — zip of XML, all cells inline strings so 16-digit CICs / account+report numbers keep leading zeros and never go scientific; reports AND logs export now .xlsx; export_view copy updated; read_xlsx_rows for verification; tests_xlsx.py + tests_log_export.py; e2e counts xlsx rows now 184/184)
    *Ask:* xlsx, not the current format.
    *Do:* report export → xlsx via openpyxl (already a dependency).

17. **Enhanced, config-driven BI (admin + reporter → management)** — ☑ (full engine: dashboard_config widgets rendered dynamically by widget_renderer; every admin-authored query validated to a single read-only SELECT and executed on a mode=ro connection — a widget can never mutate/exfiltrate; get_dashboard_widgets survives a bad widget with an error card; admin CRUD service (create/update/delete/list, gated on configure_dashboard, save-time test-run) + management view /dashboard-widgets with a Test-query button; migration seeds rework rate, reports-in-rework, top entities, classification pie, repeat-CIC + repeat-account tables, approvals-per-month; role-filtered; dashboard now fully config-driven, hardcoded KPI/charts removed; tests_dashboard_config.py)
    *Ask:* real BI, not just productivity; and no reship per new chart.
    *Do:* build out the existing `dashboard_config` substrate: admin composes
    widgets (KPI/chart/table) as read-only SQL saved as DB rows → shared DB →
    every client on refresh, zero app update. Coverage: productivity, aging,
    rework rate, monthly/SLA trends, CIC & account intelligence, top entities.
    Guardrail: admin-authored, SELECT-only. (Big item — its own sub-plan.)

18. **Help / documentation not scrollable** — ☑ (each help tab wrapped in a scrollable Column via scroll_pane helper; long content now reachable in the fixed-height dialog; ui_driver guard)
    *Ask:* let me scroll it.
    *Do:* add scroll to the help dialog (same fix class as the wizard scroll bug).

19. **Updater — push once, every client self-updates (no per-PC visits)** — ☐ (subsystem)
    *Ask:* when the codebase changes (add/retire a feature, a fix), clients must
    NOT be told to manually fetch/delete their copy — that's friction + defects.
    *Do:* distribute app code through the **shared folder** (clients have no
    internet but all reach the share). Host = update hub: you push to Codeberg →
    `git pull` on the host → a "publish app" step snapshots code to
    `share/app/<version>/` + writes `share/app/latest.txt` (version + hash). Each
    client on launch compares its local `VERSION` to `latest.txt`; if newer,
    copies the new files, smoke-checks boot, swaps, relaunches — keeping the
    prior version for auto-rollback if the new one fails. A small stable
    **launcher** does the swap (can't overwrite running Python files in place on
    Windows). Content (dashboards/dropdowns) already syncs via the shared DB, so
    many changes need no code update. Own sub-plan.

20. **Keyboard shortcuts didn't work (browser)** — ☑
    *Fixed by going native desktop* (browser no longer intercepts keys).

21. **Runbook: a clear "do this first" golden path** — ☐
    *Ask:* stop the setup tangling.
    *Do:* rewrite `HOST_RUNBOOK.md` with a strict numbered Day-0 order (pick host
    → set share → hard-reset to clean data → real users → run host windowless →
    each client → autostart) + a quickstart at the top.

22. **Hard reset (test → production), documented** — ☐
    *Ask:* wipe test state and start fresh for production.
    *Do:* a guarded `--reset` (typed confirmation; destructive): wipes DB + bus
    (queue/replica/backups/outbox) + local replicas + config + logs → fresh
    install (schema's clean admin only, forced password change). Documented as
    the pre-go-live step.

23. **No CMD window kept open (host/panel/client run hidden)** — ☐
    *Ask:* host shouldn't need a console window sitting open.
    *Do:* `pythonw.exe` + hidden `.vbs` launchers for host, panel, and client;
    Startup-folder shortcut auto-starts hidden. Honest limit (no admin, no
    service): a user process still dies on logoff/reboot until login — manual
    failover covers the host; documented.

---

## Extra foundational item (not in the original 20 but required)

**SD. Custom searchable dropdown** — ☑ (confirmed: search + collapse + fit-content)
Flet 0.27+ `enable_filter` does NOT render searchable on the desktop client
(0.28.3) — confirmed on the real client. Build a custom component (text field +
live-filtered list) that is a **drop-in for `ft.Dropdown`** (same `.value`,
`.options`, `on_change`, `ref`), behind the existing `searchable_dropdown`
wrapper, so all 22 sites become searchable with no call-site changes. Bakes in
the #12 placeholder fix. UI item → needs a visual confirm.

---

## Proposed execution order (each to 100% before the next)

1. **SD** custom searchable dropdown (+ #12 placeholder) — unblocks every form
2. **#15** numbering grace-removal — isolated, service-layer, high-value
3. **#8** supervisor role + RBAC — foundation → then **#7, #3, #2, #11**
4. Bugs: **#9** gender, **#13** second reason, **#18** help scroll, **#6** log export
5. Intelligence: **#5** CIC banner, **#14** account rapid-repeat
6. **#16** xlsx export · **#1** select-all · **#10** bigger review screen
7. **#17 + #4** config-driven BI (its own sub-plan)
8. **Ops phase:** **#23** windowless runtime · **#22** hard-reset · **#19** shared-folder auto-update (subsystem) · **#21** runbook golden-path (written last, once the above are real)
