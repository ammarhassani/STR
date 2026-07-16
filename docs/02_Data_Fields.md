# FIU Report Management System
## Data Fields

**Version:** 1.0 | **Date:** January 2026

---

## 1. Report Fields by Tab

### Tab 1: Case Information

| Field | Source | Required |
|-------|--------|----------|
| CIC | Manual (triggers RBS + SAS lookups) | Yes |
| Source System | Manual (dropdown) | Yes |
| Case ID | SAS Lookup (or manual) | No |
| Case Date Created | SAS Lookup (or manual) | No |

**Notes:**
- **CIC:** 16-digit Customer Information Code. Primary key for ALL lookups. When entered:
  - Triggers RBS lookup → customer data (Tab 2)
  - Triggers SAS lookup → Case ID(s) and Case Date Created
  - Auto-padded with leading zeros (e.g., "1234" becomes "0000000000001234")
  - **Unique constraint:** If a report already exists for this CIC, system blocks creation with error "A report already exists for this CIC"
- **Source System:** Dropdown with values: SAS, INCIDENT
- **Case ID:** Retrieved from SAS by CIC. If SAS returns multiple Case IDs, display as dropdown for user selection. Case ID can be empty if SAS returns none. If provided, must be unique (secondary check).
- **Case Date Created:** Retrieved from SAS with Case ID.

**1-to-Many Lookup Rule:** If SAS returns multiple Case IDs for a CIC, display as dropdown list for user to select.

### Tab 2: Customer Information

| Field | Source | Required |
|-------|--------|----------|
| Customer Name | RBS | Yes |
| Gender | RBS | Yes |
| Nationality | RBS | Yes |
| isLegalOwner? | RBS | Yes |
| ID Type | RBS | Yes |
| ID Number | RBS | Yes |
| Account Number | RBS | Yes (one of Account or Membership) |
| Membership Number | RBS | Yes (one of Account or Membership) |
| Branch ID | RBS | Yes |

**Notes:**
- All fields populated from RBS lookup (by CIC) and become read-only when populated (editable for Admin).
- If RBS returns no value for a specific field, that field becomes editable for manual entry.
- **Account/Membership:** At least one is required. If RBS returns multiple accounts or memberships, display as dropdown for user selection.
- **ID Type:** Document types are sourced from RBS (includes National ID, Iqama, CR, Passport, etc.).

**1-to-Many Lookup Rule:** If RBS returns multiple values for Account Number or Membership Number, display as dropdown list for user to select.

### Tab 3: Suspicion Details

| Field | Source | Required |
|-------|--------|----------|
| First Reason for Suspicion | Manual (free text) | Yes |
| Second Reason for Suspicion | Manual (dropdown) | No |
| Suspicion Classification | Manual (dropdown) | Yes |
| Type of Suspected Transaction | Manual (dropdown) | Yes |
| Total Transaction Amount | Manual | No |
| Transaction Currency | Manual (dropdown) | No |

**Notes:**
- **First Reason for Suspicion:** Free text field where agents describe the suspicious activity in detail. Minimum 10 characters required.
- **Second Reason for Suspicion:** Dropdown populated from FIU reference data (~130 Arabic values). See attached FIU Excel file. Includes "Other" option.
- **Suspicion Classification:** Required dropdown - Terrorism Funding, Money Laundering, Original Crime.
- **Total Transaction Amount:** Numeric field. Supports international number formats.
- **Transaction Currency:** Standard ISO 4217 currency codes (e.g., SAR, USD, EUR).

### Tab 4: FIU Correspondence

| Field | Source | Required |
|-------|--------|----------|
| FIU Number | Manual | No |
| FIU Date | Manual | No |
| FIU Letter Receive Date | Manual | No |
| FIU Feedback | Manual (dropdown) | No |

### Tab 5: Reporter Information

| Field | Source | Required |
|-------|--------|----------|
| Report Source | Manual (dropdown) | Yes |
| Reporter Initials | Manual | No |
| Original Copy Confirmation | Manual (checkbox) | No |
| Sending Date | Manual (date) | No |
| ARB Staff | RBS | No |

**Notes:**
- **Report Source:** Dropdown - Internal Dept, SAS, Branch, Other.
- **Reporter Initials:** Agent's initials (free text).
- **Original Copy Confirmation:** Checkbox to confirm original copy received.
- **Sending Date:** Date when report was sent to FIU. Entered by agent.

### System Fields (Auto-generated)

| Field | Description |
|-------|-------------|
| Serial Number | Unique record ID |
| Report Number | Format: YYYY/MM/NNNN |
| Approval Status | Workflow state |
| Current Version | Version number |
| Created By | User who created |
| Created At | Creation timestamp |
| Updated By | Last modifier |
| Updated At | Last update timestamp |

---

## 2. Dropdown Values

**Note:** Fields sourced from RBS (Gender, Nationality, ID Type, ARB Staff) do not have local dropdowns - values come from RBS.

**Global "Other" Rule:** When "Other" is selected in any dropdown, a free text field appears requiring minimum 10 characters.

### Source System

| Value | Display |
|-------|---------|
| SAS | SAS |
| INCIDENT | INCIDENT |

### Suspicion Classification

| Value | Display |
|-------|---------|
| TERRORISM_FUNDING | Terrorism Funding |
| MONEY_LAUNDERING | Money Laundering |
| ORIGINAL_CRIME | Original Crime |

### Second Reason for Suspicion

**Source:** FIU reference Excel file (~130 Arabic values). See attached fields.xlsx.

IT loads these values from the reference document during system deployment.

| Value | Display |
|-------|---------|
| (See FIU Excel) | (~130 Arabic suspicion reason descriptions) |
| OTHER | Other (opens text area, min 10 chars) |

### Type of Suspected Transaction

| Value | Display |
|-------|---------|
| CASH_DEPOSIT | Cash Deposit |
| CHECK_DEPOSIT | Check Deposit |
| CHECK_WITHDRAWAL | Check Withdrawal |
| DISBURSEMENT_ORDER | Disbursement Order |
| INTERNAL_TRANSFER | Internal Transfer |
| LOCAL_TRANSFER | Local Transfer |
| EXTERNAL_TRANSFER | External Transfer (Wire) |
| SADAD_PAYMENTS | SADAD Payments |
| POS_PAYMENTS | POS Payments |
| OTHER | Other (opens text area, min 10 chars) |

### Report Source

| Value | Display |
|-------|---------|
| INTERNAL_DEPT | Internal Dept |
| SAS | SAS |
| BRANCH | Branch |
| OTHER | Other (opens text area, min 10 chars) |

### FIU Feedback

| Value | Display |
|-------|---------|
| ADDED_FIU_DB | Added in FIU DB |
| FORWARD_ENTITY | Forward to Specific Entity |
| UNDER_INVESTIGATION | Under Investigation |
| SEND_BACK | Send Back for Correction |
| OTHER | Other (opens text area, min 10 chars) |

---

## 3. Dropdown Management

For locally-managed dropdowns (Source System, Suspicion Classification, Transaction Type, Report Source, FIU Feedback), administrators can:
- Add new values
- Edit display text
- Change display order
- Deactivate values (hidden from new reports, preserved in existing)
- Reactivate previously deactivated values

**Note:** Deactivated values remain visible on existing reports but cannot be selected for new reports.

**Exception:** Second Reason for Suspicion values are managed by IT from FIU reference document, not by administrators.

---

*End of Document*

**Next:** [03_Integrations.md](03_Integrations.md)
