# FIU Report Management System
## Roles & Permissions

**Version:** 1.0 | **Date:** January 2026

---

## 1. Role Definitions

| Role | Description | Typical Users |
|------|-------------|---------------|
| **Administrator** | Full system access | STR Unit leadership or approved stakeholders |
| **Agent** | Create and edit own reports | STR Agents |
| **Reporter** | View and export only | Anyone whose business depends on FIU data |

---

## 2. Permission Matrix

### Report Operations

| Permission | Administrator | Agent | Reporter |
|------------|:-------------:|:-----:|:--------:|
| View all reports | Yes | Yes | Yes |
| Create new report | Yes | Yes | No |
| Edit own report | Yes | Yes | No |
| Edit any report | Yes | No | No |
| Delete report | Yes | No | No |
| Restore deleted report | Yes | No | No |
| Permanently delete | Yes | No | No |

### Approval Workflow

| Permission | Administrator | Agent | Reporter |
|------------|:-------------:|:-----:|:--------:|
| Submit own report | Yes | Yes | No |
| Approve reports | Yes | No | No |
| Reject reports | Yes | No | No |
| Request rework | Yes | No | No |
| Resubmit after rework | Yes | Yes (own) | No |

### Version Control

| Permission | Administrator | Agent | Reporter |
|------------|:-------------:|:-----:|:--------:|
| View version history | Yes | Yes | Yes |
| Compare versions | Yes | Yes | Yes |
| Rollback to previous version | Yes | No | No |

### Export & Search

| Permission | Administrator | Agent | Reporter |
|------------|:-------------:|:-----:|:--------:|
| Search reports | Yes | Yes | Yes |
| Export to Excel | Yes | Yes | Yes |

### Administration

| Permission | Administrator | Agent | Reporter |
|------------|:-------------:|:-----:|:--------:|
| Manage users | Yes | No | No |
| Manage dropdowns | Yes | No | No |
| System settings | Yes | No | No |
| View system logs | Yes | No | No |
| Database backup/restore | Yes | No | No |

---

## 3. Role Workflows

### Administrator

Can do everything:
- View and edit all reports
- Approve, reject, or request rework on submitted reports
- Delete and restore reports
- Rollback report versions
- Manage users and assign roles
- Configure dropdowns and system settings
- View audit logs and perform backups
- Reassign rework reports to different agents
- Configure column visibility for Reporter role
- Close month for report numbering (start new sequence)

**Lookup Field Behavior for Admin:**
- Lookup fields (from RBS/SAS) remain EDITABLE after population
- "Re-lookup" button available to refresh data from RBS/SAS
- This allows admin to manually override auto-populated data when needed

**Note:** Reports created by administrators skip approval workflow and are saved directly as Approved.

### Agent

Typical workflow:
1. Create a new report
2. Enter CIC (system retrieves both RBS and SAS data)
3. If multiple Case IDs returned, select from dropdown
4. If multiple accounts/memberships returned, select from dropdown
5. Complete manual fields
6. Save as draft or submit for approval
7. If rework requested, edit and resubmit

**Lookup Field Behavior for Agent:**
- Lookup fields (from RBS/SAS) become READ-ONLY after population
- Agent cannot manually edit auto-populated data
- No "Re-lookup" button available

**Restrictions:**
- Can only edit their own reports
- Cannot approve, reject, or delete reports
- Cannot access administration features

### Reporter

View-only access:
- Browse and search all reports
- View report details
- View version history
- Export data to Excel

**Column Visibility:**
- Administrator configures which columns Reporters can see in Reports list
- Some columns may be hidden from Reporter view

**Restrictions:**
- Cannot create, edit, or delete reports
- Cannot participate in approval workflow
- Cannot access administration features
- May have restricted column visibility (configured by admin)

---

## 4. Edit Restrictions by Status

Even with edit permission, editing depends on report status:

| Status | Administrator | Agent (Owner) |
|--------|:-------------:|:-------------:|
| Draft | Yes | Yes |
| Pending Approval | No | No |
| Approved | Yes | Yes |
| Rejected | No | No |
| Rework | Yes | Yes |

**Note:** Editing an Approved report keeps status as Approved but increments version (v1 → v2 → v3).

---

## 5. Quick Reference

| If you need to... | Required role |
|-------------------|---------------|
| View reports | Any |
| Create a report | Agent or Administrator |
| Edit your own report | Agent or Administrator |
| Edit someone else's report | Administrator |
| Delete a report | Administrator |
| Approve/reject a report | Administrator |
| Manage users | Administrator |
| Configure system | Administrator |
| Export data | Any |

---

*End of Document*

**Next:** [05_UI_Screens.md](05_UI_Screens.md)
