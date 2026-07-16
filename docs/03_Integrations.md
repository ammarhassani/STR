# FIU Report Management System
## Integrations

**Version:** 1.0 | **Date:** January 2026

---

## Integration Summary

All external integrations are **read-only data lookups**. The system does not write back to any external system.

**CIC is the primary lookup key** - it triggers both RBS and SAS lookups.

| System | Purpose | Lookup Key | Data Retrieved |
|--------|---------|------------|----------------|
| Identity Self Service | User authentication (SSO) | Username | User identity and role |
| RBS (Core Banking) | Customer data lookup | CIC | Customer details |
| SAS Visual Investigator | Case data lookup | CIC | Case ID(s) and Case Date Created |

---

## 1. Identity Self Service

### What It Does
- Provides enterprise single sign-on (SSO) authentication
- No local passwords stored in FIU system
- Users authenticate through organizational identity platform

### What We Get From It
| Data | Used For |
|------|----------|
| User ID | Session management |
| Username | Display and report ownership |
| Display Name | UI display |
| Groups/Roles | Role assignment |

### Role Mapping
Users are assigned FIU roles based on their Identity Self Service groups:
- Administrator
- Agent
- Reporter

*Specific group names to be defined with IT Security.*

---

## 2. RBS (Core Banking System)

### What It Does
- Provides customer information lookup
- Triggered when user enters CIC in a report

### What We Get From It
| Field | Description |
|-------|-------------|
| Customer Name | Full customer name |
| Gender | Customer gender |
| Nationality | Nationality code |
| isLegalOwner? | Legal entity owner flag |
| ID Type | Document type (various types from RBS) |
| ID Number | Document number |
| Account Number(s) | Customer accounts (may return multiple) |
| Membership Number(s) | Membership numbers (may return multiple) |
| Branch ID | Home branch code |
| ARB Staff | ARB staff indicator |

### How It Works
1. User enters CIC in the report form
2. System auto-pads CIC to 16 digits with leading zeros
3. System looks up customer in RBS using CIC
4. **If found:** Fields populate automatically and become read-only (editable for Admin)
5. **If multiple accounts/memberships:** Display as dropdown list for user selection
6. **If not found:** User can enter fields manually

### Fallback
- If RBS is unavailable: manual entry enabled for all customer fields
- If RBS returns partial data: only fields with no value become editable for manual entry

---

## 3. SAS Visual Investigator

### What It Does
- Provides investigation case data lookup
- Triggered when user enters CIC in a report (same as RBS lookup)
- Lookup uses CIC as the key, NOT Case ID

### What We Get From It
| Field | Description |
|-------|-------------|
| Case ID(s) | Case identifier(s) for this CIC (may return multiple) |
| Case Date Created | Date case was created |

### How It Works
1. User enters CIC in the report form
2. System looks up cases in SAS using CIC
3. **If found:** Case ID(s) and Case Date Created returned
4. **If multiple Case IDs:** Display as dropdown list for user selection
5. **If found:** Selected Case ID and Case Date Created populate automatically (read-only for Agent, editable for Admin)
6. **If not found:** Case ID and Case Date Created can be entered manually (or left empty)

### Fallback
If SAS is unavailable or returns no results, manual entry is enabled for case fields. Case ID is optional - reports can be created without a Case ID.

---

## Dependencies by Integration

| Integration | Owner | What They Provide |
|-------------|-------|-------------------|
| Identity Self Service | IT Security | Authentication endpoint, role mapping |
| RBS | Core Banking Team | Customer lookup endpoint |
| SAS | SAS Administration | Case lookup endpoint |

---

*End of Document*

**Next:** [04_Roles_Permissions.md](04_Roles_Permissions.md)
