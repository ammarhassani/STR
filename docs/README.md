# FIU Report Management System
## Business Requirements Documentation

**Version:** 1.0 | **Date:** January 2026

---

## Documents

| Document | Description |
|----------|-------------|
| [01_BRD_Main.md](01_BRD_Main.md) | System overview, scope, and requirements |
| [02_Data_Fields.md](02_Data_Fields.md) | Report fields and dropdown values |
| [03_Integrations.md](03_Integrations.md) | External system integrations |
| [04_Roles_Permissions.md](04_Roles_Permissions.md) | User roles and access rights |
| [05_UI_Screens.md](05_UI_Screens.md) | Screen layouts and navigation |
| [06_Developer_Decisions.md](06_Developer_Decisions.md) | Preemptive answers to common developer questions |

---

## System Summary

The FIU Report Management System manages FIU reports for the STR Unit with:

- **RBS Integration** - Customer data lookup via CIC
- **SAS Integration** - Case data lookup via Case ID
- **Identity Self Service** - Enterprise SSO authentication

All integrations are **read-only**. The system is deployed **on-premises only**.

---

*End of Index*
