# STR bug-hunt ledger

One line per assignment. The loop takes the **first `todo `** line, works only
that one, and rewrites its prefix before it stops. Ranked by blast radius:
authorization first, audit trail second, then everything whose failure is a
support ticket rather than a regulator finding.

Format: `<prefix><ID> | <target file:line> | <claim> | <note>`

| prefix | meaning |
|---|---|
| `todo` | not started |
| `done` | fixed, suite green, commit sha in the note |
| `void` | probe ran, behaviour was correct, no bug — a successful iteration |
| `park` | Windows / packaged-build only, moved to WINDOWS_MANUAL.md |
| `ask` | product decision, not a defect — needs a human |
| `blocked` | red test committed, cause not found. Left red on purpose. |

`tests/loop_gate.py` exits 0 only when every suite passes **and** zero `todo`
or `blocked` lines remain. Nothing the agent can type ends the loop.

Audit in two commands:

    grep -c '^todo \|^blocked ' tests/LOOP_LEDGER.md      # must be 0
    git log --oneline --name-only loop/night-1 ^main      # each fix paired with a RED test

---

todo F1a | services/report_number_service.py:153 | reserve_block takes the actor as a plain argument and command_registry.py:64 only guards the RPC path, so a caller on the HOST PC can burn official FIU numbers in a colleague's name | Evidence: services/command_registry.py IDENTITY_ARGS
todo F1b | services/report_number_service.py:222 | release_numbers takes the actor as a plain argument with no current_user check | Evidence: services/command_registry.py:56-62
todo F1c | services/report_number_service.py:262 | transfer_numbers has the same hole; one agent can move another agent's reserved block | Evidence: services/command_registry.py:64
todo A2 | services/command_registry.py | DRIFT GUARD: inspect.signature every WRITE_COMMANDS target; any parameter named username/user_id/from_user/admin_username with no IDENTITY_ARGS entry is a silent privilege escalation waiting for the next service method | Evidence: services/command_registry.py:64
todo A1 | services/command_registry.py | bind_identity has zero tests; assert it overwrites the client-supplied identity for all IDENTITY_ARGS entries across positional, keyword and omitted argument shapes | Evidence: services/command_registry.py header
todo A3 | services/settings_service.py | save_settings/delete_settings appear in IDENTITY_ARGS at indexes 1 and 0 and are called by no test; verify the declared index matches the real signature — an off-by-one binds the caller's identity onto the wrong argument | Evidence: services/command_registry.py IDENTITY_ARGS
todo A4 | services/restore_service.py | restore_report takes admin_username as a caller-supplied string, has no authz inside, and is NOT in WRITE_COMMANDS; establish whether it is client-reachable — either an unguarded privileged write or dead code | Evidence: flet_app/views/reports_view.py:935
todo A5 | host/host_service.py | handle_command sets self.auth.current_user per command on a SHARED auth service; prove serialization — two client sessions must never swap identity mid-command | Evidence: host/host_service.py handle_command
todo A6 | services/auth_service.py:331 | complete_onboarding is dispatched pre-auth and excluded from the applied_commands ledger; hunt unlimited folder-queue replay as a password-setting oracle | Evidence: services/auth_service.py:331
todo B5 | services/report_service.py:338-349 | admin-created reports auto-approve, skipping BOTH the FIU gate and four-eyes; claimed reproduction: approved with no fiu_number and zero rows in report_approvals | Evidence: services/approval_service.py:67 REQUIRED_FIU_FIELDS
todo F2 | services/approval_service.py:67-76 | request_approval refuses pending_approval/approved/rejected but not archived, so a retrospective import can be pushed into the live supervisor queue | Evidence: services/retrospective_import.py:27
todo B4 | services/approval_service.py:183 | separation of duties compares requested_by to current_user['username'] as a raw string; hunt bypass via case, surrounding whitespace, or an account recreated with a reused username | Evidence: services/approval_service.py:183
todo B3 | services/approval_service.py | enumerate every (status, action) pair including the illegal ones; each must refuse cleanly with NO partial write left behind | Evidence: services/approval_service.py:67-76
todo B1 | services/logging_service.py | log_user_action is called throughout production and named in no test; assert the payload for create/edit/delete/restore/request/approve/reject/rework | Evidence: services/logging_service.py
todo B2 | services/logging_service.py | prove the activity log is append-only for every non-admin role | Evidence: tests/tests_warzone.py:382
todo B6 | services/report_number_service.py:83-109 | assert global uniqueness of report_number + serial_number under concurrent reserve/consume/release/transfer ACROSS a month rollover | Evidence: services/report_number_service.py:83-109
todo B7 | services/report_service.py:1034 | edit-lock lifecycle: get_lock_holder is untested, there is no admin force-unlock, and a client that dies mid-edit orphans the lock | Evidence: services/report_service.py:1034 LOCK_MINUTES
todo B8 | services/security_service.py | migrate_plain_password / needs_migration / migrate_all_passwords are untested; a bug here either leaves plaintext at rest or locks out every user | Evidence: services/security_service.py
todo C8 | services/queue_transport.py:43-46 | outbox durability: queued commands must survive a process restart and drain EXACTLY once. A client who sees her own queued report as missing files it twice, burning two official FIU numbers | Evidence: services/remote_gateway.py:63-88
todo C1 | services/report_number_service.py:262 | transfer_numbers checks the recipient is_active but not that they may file at all; numbers moved to a reporter can never be used or returned | Evidence: services/report_number_service.py:144 _may_reserve
todo C2 | services/approval_service.py:289 | rework reassignment requires the target role to be exactly 'agent', but supervisors hold add_report and edit-own; no move is possible when the agent is on leave | Evidence: utils/permissions.py:25-39
todo C7 | tests/tests_overlay_leak.py:22 | extend OffstagePage coverage to EVERY dialog; only change_password_dialog is checked today, and this bug already survived one claimed fix | Evidence: tests/tests_overlay_leak.py:31-38
todo C3 | flet_app/views/fiu_basket_view.py | wired up in main.py:37, referenced by zero tests; drive it through the FakePage harness as the FIU analyst persona | Evidence: flet_app/main.py:37
todo C4 | flet_app/views/activity_view.py | wired up in main.py:46, referenced by zero tests | Evidence: flet_app/main.py:46
todo C5 | flet_app/dialogs/backup_restore_dialog.py | 626 lines, untested, and it triggers destructive restores | Evidence: flet_app/dialogs/backup_restore_dialog.py
todo C6 | flet_app/dialogs/version_history_dialog.py | 712 lines plus diff_view_dialog.py at 514; no test touches either | Evidence: flet_app/dialogs/version_history_dialog.py
todo C9 | database/seed_dropdowns.py | untested and imported by deploy.py; a bad seed ships broken dropdowns to every workstation | Evidence: deploy.py
todo Z1 | utils/validation.py, utils/logger.py, database/queue_manager.py, database/migrate_add_columns.py | claimed dead: nothing under services/ database/ host/ panel/ utils/ flet_app/ imports them and they duplicate the live validation and logging stacks. VERIFY before deleting, then ban re-import in conformance | Evidence: services/validation_service.py, services/logging_service.py

ask F7 | services/report_service.py:678 | get_reports with no status filter returns archived rows, while create/update deliberately EXCLUDE archived from CIC checks — the intent for the list itself is unowned | product decision: should a regulator export include twenty years of imported history?
ask F3 | flet_app/views/my_work_view.py:15-21 | _lanes() has no 'rejected' lane. The premise is true but 'invisible' is false — reports_view.py:469 renders rejected and view_reports is true for every role | product decision: should a terminal state appear in a "must act on" queue?
