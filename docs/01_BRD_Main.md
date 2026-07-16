# Business Requirements Document
## FIU Report Management System

**Version:** 1.0 | **Date:** January 2026

---

## 1. Purpose

This system manages FIU reports for the STR Unit. It retrieves customer data from the Core Banking System (RBS) and case data from SAS Visual Investigator, eliminating manual data entry.

---

## 2. What The System Does

### Core Features

| Feature | Description |
|---------|-------------|
| **Report Management** | Create, edit, delete, and restore FIU reports (deleted reports auto-purge after 30 days, configurable) |
| **RBS Integration** | Auto-populate customer fields by entering CIC |
| **SAS Integration** | Auto-populate case fields by entering Case ID |
| **Approval Workflow** | Submit reports for approval; approve, reject, or request rework |
| **Version Control** | Track all changes with version history and rollback |
| **User Management** | Manage users and assign roles |
| **Export** | Export reports to Excel |
| **Localization** | English only |

### Approval Workflow

Reports follow this workflow:

```
Draft → Pending Approval → Approved / Rejected / Rework

- Draft: Report being created or edited
- Pending Approval: Submitted, waiting for administrator review
- Approved: Approved by administrator (final)
- Rejected: Rejected by administrator (final, cannot be resubmitted)
- Rework: Sent back for corrections, then resubmitted
```

**Note:** Reports created by administrators skip the approval workflow and are saved directly as Approved.

### Report Number Format

Reports are automatically numbered: **YYYY/MM/NNNN**

- YYYY = Year (e.g., 2026)
- MM = Month (01-12)
- NNNN = Sequential number (0001, 0002, ...)
- No upper limit on the sequential number (can exceed 9999 if needed)

Example: `2026/01/0005` = 5th report of January 2026

**Month Grace Period:** Sequential numbering continues past month-end until administrator manually closes the month. Example: January reports (2026/01/NNNN) can continue into February until admin closes January and starts February sequence.

**Note:** All dates use Gregorian calendar only.

### Report Uniqueness

- **CIC is the primary key** - Only one report allowed per CIC in the system
- If a report already exists for a CIC, new report creation is blocked
- Error message: "A report already exists for this CIC"
- Case ID uniqueness is secondary (if provided, must also be unique)

---

## 3. Scope

### In Scope

- FIU report creation and management
- Customer data lookup from RBS (read-only)
- Case data lookup from SAS (read-only)
- User authentication via Identity Self Service
- Approval workflow within this system
- Version history and rollback
- Excel export
- Dropdown management
- System settings and backup

### Out of Scope

| Item | Reason |
|------|--------|
| Write-back to RBS | Integration is read-only |
| Write-back to SAS | Integration is read-only |
| Document attachments | Not required |
| Regulatory submission | System captures data; submission is separate |
| Report Classification (jurisdiction-based) | RBS jurisdiction lookup logic removed from scope |

---

## 4. User Roles

| Role | Can Do |
|------|--------|
| **Administrator** | Everything: manage users, approve reports, system settings, edit lookup fields |
| **Agent** | Create reports, edit own reports, submit for approval |
| **Reporter** | View and export reports only |

### Admin Lookup Field Behavior

- Lookups (RBS, SAS) trigger automatically when CIC is entered
- For **Agents**: Lookup fields become READ-ONLY after population
- For **Administrators**: Lookup fields remain EDITABLE after population
- Administrators have a "Re-lookup" button to refresh data from RBS/SAS if needed

---

## 5. Dependencies

| System | Owner | What We Need |
|--------|-------|--------------|
| RBS (Core Banking) | Core Banking Team | Customer lookup endpoint |
| SAS Visual Investigator | SAS Administration | Case lookup endpoint |
| Identity Self Service | IT Security | SSO authentication |
| Server infrastructure | Infrastructure Team | On-premises servers |
| Database | DBA Team | Database instance |

---

## 6. Constraints

- **On-premises only** - No cloud services
- **Read-only integrations** - Cannot write to RBS or SAS
- **Session timeout** - Users are logged out after 30 minutes of inactivity

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **Case** | Suspected behaviour flagged by investigation level 3, then processed by STR Unit |
| **CIC** | Customer Information Code - 16-digit banking customer identifier |
| **CR** | Commercial Registration - identifier for corporate entities |
| **FIU** | Financial Intelligence Unit - external authority receiving reports |
| **RBS** | Core Banking System |
| **SAS** | SAS Visual Investigator |
| **STR** | STR Unit - the unit managing FIU reports |
| **isLegalOwner?** | Whether the customer owns a legal corporation |

---

*End of Document*

**Next:** [02_Data_Fields.md](02_Data_Fields.md)
