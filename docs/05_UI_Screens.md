# FIU Report Management System
## UI Screens

**Version:** 1.0 | **Date:** January 2026

---

## 1. Application Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]        FIU Report Management        [EN/AR] [User]  │
├─────────────────────────────────────────────────────────────┤
│         │                                                   │
│  Side   │                                                   │
│  Menu   │              Main Content Area                    │
│         │                                                   │
│  Home   │                                                   │
│  Reports│                                                   │
│  Admin  │                                                   │
│         │                                                   │
├─────────────────────────────────────────────────────────────┤
│                        Footer                               │
└─────────────────────────────────────────────────────────────┘
```

### Navigation Menu

| Menu Item | Shows For |
|-----------|-----------|
| Home | Everyone |
| Reports | Everyone |
| Pending Approvals | Administrator |
| Deleted Reports | Administrator |
| Users | Administrator |
| Dropdowns | Administrator |
| Settings | Administrator |
| Logs | Administrator |

### Language

- User interface: English only
- Text entry: Supports Arabic characters in free text fields

---

## 2. Home Page

### Overview

- Welcome message with username and role
- Quick action buttons (New Report, View Reports, Export)
- List of all user's reports

---

## 3. Reports List

```
┌─────────────────────────────────────────────────────────────┐
│  Reports                                    [+ New Report]  │
├─────────────────────────────────────────────────────────────┤
│  Search: [________]  Status: [All ▼]  Date: [From] - [To]  │
│  [Search]  [Clear]                           [Export ▼]     │
├─────────────────────────────────────────────────────────────┤
│  Report #    │ Case ID  │ Customer   │ Date    │ Status    │
│  2026/01/005 │ CASE-123 │ Ahmed...   │ Jan 15  │ Draft     │
│  2026/01/004 │ CASE-122 │ Mohammed...│ Jan 14  │ Pending   │
│  2026/01/003 │ CASE-121 │ Sara...    │ Jan 13  │ Approved  │
├─────────────────────────────────────────────────────────────┤
│                                    Page 1 of 5  [< 1 2 3 >] │
└─────────────────────────────────────────────────────────────┘
```

### Table Columns

- Report Number
- Case ID
- Customer Name
- Creation Date
- Status (color badge: Draft=gray, Pending=yellow, Approved=green, Rejected=red, Rework=orange)
- Actions menu

All columns are sortable by clicking the column header. Default sort: newest first (by creation date).

### Pagination

Users can select rows per page: 10, 25, 50, 100, or All.

### Search & Filters

- Text search (Report #, Customer Name, CIC, Case ID, Account Number)
- Status dropdown
- Date range (Gregorian calendar)

### Row Actions

- **View** - Open report details
- **Edit** - Modify report (if permitted)
- **History** - View version history
- **Submit** - Submit for approval (if Draft/Rework)
- **Delete** - Remove report (Administrator only)

### Bulk Operations

- Users can select multiple reports and submit them for approval at once
- Administrators can delete multiple reports at once

---

## 4. Report Form

```
┌─────────────────────────────────────────────────────────────┐
│  Report: 2026/01/0005              Status: Draft    [Save]  │
├─────────────────────────────────────────────────────────────┤
│  [Case Info] [Customer] [Suspicion] [FIU] [Reporter]        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CIC *                                                      │
│  [0000001234567890__] [Lookup]            [Re-lookup](Admin)│
│                                                             │
│  Source System *                                            │
│  [SAS ▼]                                                    │
│                                                             │
│  Case ID                                                    │
│  [CASE-00123 ▼] (dropdown if multiple from SAS)            │
│                                                             │
│  Case Date Created                                          │
│  [2026-01-15] (from SAS)                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                              [Cancel]  [Save]  [Next Tab]   │
└─────────────────────────────────────────────────────────────┘
```

### Tabs

1. **Case Info** - CIC (triggers lookups), Source System, Case ID (from SAS), Case Date Created
2. **Customer** - Name, Gender, Nationality, ID Type, etc. (from RBS)
3. **Suspicion** - Suspicion Classification, Reason, Transaction Type, Amount
4. **FIU** - FIU correspondence fields (FIU Number, FIU Date, FIU Feedback, etc.)
5. **Reporter** - Report Source, Initials, etc.

### Field Indicators

- Required fields marked with *
- Fields from RBS/SAS show lock icon (read-only for Agent, editable for Admin)
- Integration status message (success/not found/error)
- Retry button if lookup fails
- **Re-lookup button** (Admin only) - refreshes data from RBS/SAS

### Validation

- Real-time validation as user enters data
- Invalid/missing required fields highlighted in red with error message

### Form Actions

- **Save Draft** - Save without validation
- **Save** - Validate and save
- **Submit** - Send for approval
- **Cancel** - Return to list

### Concurrent Editing

When a user opens a report that is already being edited by another user, the report is locked. The system displays who currently has the report open. The second user must wait until the first user closes the report.

---

## 5. Version History

```
┌─────────────────────────────────────────────────────────────┐
│  Version History: Report 2026/01/0005                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ● Version 5 (Current)                         [View][Diff] │
│    Modified by: Ahmed | Jan 16, 2026                        │
│    Changes: Updated suspicion details                       │
│                                                             │
│  ● Version 4                          [View][Diff][Rollback]│
│    Modified by: Ahmed | Jan 15, 2026                        │
│    Changes: Status changed to Rework                        │
│                                                             │
│  ● Version 3                          [View][Diff][Rollback]│
│    Modified by: Admin | Jan 15, 2026                        │
│    Changes: Customer name corrected                         │
│                                                             │
│  ● Version 1 (Original)                              [View] │
│    Created by: Ahmed | Jan 14, 2026                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Actions

- **View** - Open read-only view of version
- **Diff** - Compare with current version (side by side, all changed fields highlighted)
- **Rollback** - Restore to this version (Administrator only)

---

## 6. Approval Queue (Administrator)

```
┌─────────────────────────────────────────────────────────────┐
│  Pending Approvals (5)                                      │
├─────────────────────────────────────────────────────────────┤
│  Report #    │ Case ID  │ Customer    │ Submitted By │ Date │
│  2026/01/005 │ CASE-123 │ Ahmed...    │ Ahmed        │Jan 15│
│  2026/01/004 │ CASE-122 │ Mohammed... │ Sara         │Jan 14│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Full report details displayed here]                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Comment: [_________________________________]               │
│                                                             │
│  [Approve]      [Request Rework]      [Reject]              │
└─────────────────────────────────────────────────────────────┘
```

### Approval Rules

- **Approve** - Comment optional
- **Reject** - Comment required (rejection is final)
- **Request Rework** - Comment required (so agent knows what to fix)
- **Reassign** - Admin can reassign rework to a different agent if original is unavailable

---

## 7. Deleted Reports (Administrator)

Shows soft-deleted reports awaiting permanent deletion.

| Column | Description |
|--------|-------------|
| Report Number | Original report number |
| Case ID | Associated case |
| Customer Name | Customer on the report |
| Deleted By | User who deleted the report |
| Deleted Date | When it was deleted |
| Days Until Purge | Days remaining before auto-purge |

### Actions

- **Restore** - Restore report to active status
- **Permanently Delete** - Remove forever (requires confirmation)

---

## 8. User Management (Administrator)

```
┌─────────────────────────────────────────────────────────────┐
│  Users                                        [+ Add User]  │
├─────────────────────────────────────────────────────────────┤
│  Search: [________]                                         │
├─────────────────────────────────────────────────────────────┤
│  Username  │ Display Name   │ Role          │ Status       │
│  ahmed.m   │ Ahmed Mohammed │ Agent         │ Active       │
│  sara.k    │ Sara Khalid    │ Agent         │ Active       │
│  admin     │ Administrator  │ Administrator │ Active       │
│  khalid.r  │ Khalid Rahman  │ Reporter      │ Inactive     │
└─────────────────────────────────────────────────────────────┘
```

### Add User Flow

1. Admin clicks "+ Add User"
2. Admin enters username and searches IDSS
3. If found: Display Name auto-populates from IDSS
4. Admin selects Role (Administrator / Agent / Reporter)
5. Admin saves - user is Active by default

### User Form Fields

- **Username** - From Identity Self Service (read-only after creation)
- **Display Name** - From Identity Self Service (read-only)
- **Role** - Administrator / Agent / Reporter
- **Active status** - Toggle on/off

**Note:** Username and Display Name come from IDSS. Administrators only assign roles and active status locally. Users cannot be deleted, only deactivated.

---

## 9. Dropdown Management (Administrator)

```
┌─────────────────────────────────────────────────────────────┐
│  Dropdown Management                                        │
├─────────────────────────────────────────────────────────────┤
│  Category: [Report Source ▼]                 [+ Add Value]  │
├─────────────────────────────────────────────────────────────┤
│  Code         │ Display        │ Order │ Status │
│  BRANCH       │ Branch         │ 1     │ Active │
│  CALL_CENTER  │ Call Center    │ 2     │ Active │
│  COMPLIANCE   │ Compliance     │ 3     │ Active │
└─────────────────────────────────────────────────────────────┘
```

**Note:** Only locally-managed dropdowns appear here. Fields sourced from RBS (Gender, Nationality, ID Type, ARB Staff) are not managed in this screen. Second Reason for Suspicion values are managed by IT from FIU reference document.

### Actions

- **Add** - Add new dropdown value
- **Edit** - Modify display text and order
- **Activate/Deactivate** - Toggle value visibility

---

## 10. Settings (Administrator)

### System Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Deleted reports retention | Days before auto-purge | 30 |
| Session timeout | Minutes of inactivity before logout | 30 |
| Default rows per page | Default pagination size | 25 |

### Report Number Month Management

Admin can close the current month to start a new report number sequence:

```
Current Month: January 2026 (Active)
Last Report: 2026/01/0045

[Close January & Start February]
```

**Note:** Sequential numbering continues past month-end until admin manually closes the month (grace period).

### Reporter Column Visibility

Admin configures which columns Reporters see in the Reports list:

```
Column Visibility for Reporter Role:
☑ Report Number
☑ Case ID
☑ Customer Name
☑ Creation Date
☑ Status
☐ CIC
☐ Account Number
☐ Amount
[Save]
```

Agents and Administrators always see all columns.

**Backup:** Automated weekly backup of database.

---

## 11. Logs (Administrator)

### Log Types

| Log Type | What It Records |
|----------|-----------------|
| User logins | Login/logout timestamps, username |
| Report actions | Create, edit, delete, restore, submit, approve, reject, rework |
| Version changes | Who changed what, when |
| Admin actions | User management, dropdown changes, settings changes |

**Note:** System errors are handled separately by IT and not shown in this screen.

**Retention:** Logs are kept for 1 year.

**Export:** Administrators can export logs to Excel.

---

## 12. Export Options

```
┌─────────────────┐
│ Export          │
├─────────────────┤
│ ○ Current Page  │
│ ● Filtered Data │
│ ○ All Data      │
├─────────────────┤
│ [Export]        │
└─────────────────┘
```

### Export Details

- Excel format (.xlsx)
- All fields included by default
- Column selector allows user to choose which fields to export

---

## 13. Confirmations

### Delete Confirmation

> "Are you sure you want to delete report 2026/01/0005? This action can be undone by an administrator."

### Permanent Delete Confirmation

> "This action CANNOT be undone. The report and all its version history will be permanently removed. Type DELETE to confirm."

### Reject Confirmation

> Requires mandatory rejection reason before confirmation is enabled.

---

*End of Document*

**Back to:** [README.md](README.md)
