# FIU Report Management System
## Developer Decisions

**Version:** 1.0 | **Date:** January 2026

---

## Purpose

This document preemptively answers common developer questions and explicitly marks decisions that are **developer choice**. If a question is not answered here or in the other BRD documents, developers should use their judgment and proceed.

---

## 1. Field Constraints

| Field | Max Length | Notes |
|-------|------------|-------|
| CIC | 16 digits | Auto-padded with leading zeros, PRIMARY KEY |
| Case ID | 50 chars | From SAS lookup or manual |
| Customer Name | 200 chars | From RBS or manual |
| ID Number | 50 chars | From RBS or manual |
| Account Number | 30 chars | From RBS |
| Membership Number | 30 chars | From RBS |
| Branch ID | 20 chars | From RBS |
| First Reason for Suspicion | 4000 chars | Min 10, max 4000 |
| Total Transaction Amount | 18 digits | 15 integer + 3 decimal |
| FIU Number | 50 chars | Manual entry |
| Reporter Initials | 10 chars | Manual entry |
| Comments (approval) | 1000 chars | For reject/rework |
| Other text (all dropdowns) | 4000 chars | Min 10, max 4000 |

**Rule:** If a field comes from RBS/SAS, accept whatever length they return. These limits are for manual entry only.

---

## 2. Date & Time

| Decision | Answer |
|----------|--------|
| Date format display | `DD/MM/YYYY` (e.g., 15/01/2026) |
| Date picker format | Gregorian calendar only |
| Timestamp format | `DD/MM/YYYY HH:mm` (24-hour) |
| Timezone | Server timezone (local) |
| Date storage | ISO 8601 in database |

---

## 3. Numbers & Currency

| Decision | Answer |
|----------|--------|
| Amount display | Comma-separated thousands (e.g., 1,234,567.89) |
| Decimal places | Up to 3 (for fils/cents) |
| Currency code display | Show code after amount (e.g., 1,000.00 SAR) |
| Negative amounts | Not allowed (use transaction type to indicate direction) |

---

## 4. Developer Choice (No Business Requirement)

These are explicitly left to developer judgment. Do not ask business for clarification.

| Topic | Developer Decides |
|-------|-------------------|
| Database technology | PostgreSQL, SQL Server, Oracle - your call |
| API response format | JSON structure, field naming conventions |
| Frontend framework | Whatever the team knows |
| Loading spinners | Design as appropriate |
| Button colors/styling | Follow existing design system or create one |
| Form validation timing | On blur, on submit, real-time - pick one consistently |
| API timeout duration | Standard practice (30 seconds typical) |
| Retry logic for failed API calls | Implement reasonable retry (2-3 attempts) |
| Caching strategy | Developer decision |
| Code architecture | MVC, clean architecture - team choice |
| Logging library | Team standard |
| Testing framework | Team standard |

---

## 5. Browser & Device Support

| Requirement | Answer |
|-------------|--------|
| Application type | Web application (browser-based) |
| Hosting | On-premises server |
| Desktop browsers | Chrome, Edge (latest 2 versions) |
| Mobile/tablet support | **Not required** - desktop browsers only |
| Minimum screen width | 1280px |
| Print support | **Not required** |

---

## 6. Session & Security

| Question | Answer |
|----------|--------|
| What happens on session timeout? | Redirect to login, show message "Session expired" |
| Save unsaved work on timeout? | No - user should save frequently |
| Warn before timeout? | No - not required |
| Password requirements? | Handled by Identity Self Service, not our system |
| Failed login attempts? | Handled by Identity Self Service |
| Remember me? | No - not required |

---

## 7. Concurrency & Locking

| Question | Answer |
|----------|--------|
| How long is a report locked? | Until user closes the form or session expires |
| What if user leaves browser open? | Lock expires with session (30 min inactivity) |
| Can admin override lock? | No - wait for timeout |
| Lock message format? | "This report is currently being edited by [Display Name]" |

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| RBS unavailable | Show message, enable manual entry for those fields |
| SAS unavailable | Show message, enable manual entry for case fields |
| Network error during save | Show error, keep form data, allow retry |
| Duplicate CIC | Block save, show "A report already exists for this CIC" |
| Duplicate Case ID | Block save, show "A report already exists for this Case ID" (secondary check) |
| Required field missing | Highlight field, show "This field is required" |
| Validation failed | Highlight field, show specific error |
| Session expired during action | Redirect to login after action fails |
| "Other" text too short | Highlight field, show "Minimum 10 characters required" |

**Error message tone:** Professional, clear, actionable. No technical jargon.

---

## 9. Performance Expectations

| Metric | Target |
|--------|--------|
| Page load | < 3 seconds |
| Search results | < 2 seconds |
| Save operation | < 2 seconds |
| Export (100 records) | < 5 seconds |
| Export (1000+ records) | Show progress indicator |
| RBS/SAS lookup | Timeout after 30 seconds, then show error |

---

## 10. Export Specifics

| Question | Answer |
|----------|--------|
| Excel file naming | `FIU_Reports_YYYYMMDD_HHmmss.xlsx` |
| Max export size | No hard limit - but warn if > 10,000 records |
| Include headers? | Yes, always |
| Date format in Excel | Same as display (DD/MM/YYYY) |
| Amount format in Excel | Number format, not text |
| Empty fields | Leave blank, don't write "N/A" |

---

## 11. Audit Log Details

What gets logged (exact fields):

| Action | Logged Data |
|--------|-------------|
| Login | Username, timestamp, IP address |
| Logout | Username, timestamp |
| Create report | Report number, username, timestamp |
| Edit report | Report number, username, timestamp, fields changed (old→new) |
| Delete report | Report number, username, timestamp |
| Restore report | Report number, username, timestamp |
| Submit for approval | Report number, username, timestamp |
| Approve | Report number, admin username, timestamp, comment |
| Reject | Report number, admin username, timestamp, comment |
| Rework | Report number, admin username, timestamp, comment, reassigned_to (if changed) |
| User created | Target username, admin username, timestamp, role assigned |
| User modified | Target username, admin username, timestamp, changes |
| Dropdown modified | Category, value, admin username, timestamp, change type |
| Settings changed | Setting name, old value, new value, admin username, timestamp |

---

## 12. Empty States

| Screen | When Empty | Message |
|--------|------------|---------|
| Reports list | No reports exist | "No reports found. Click 'New Report' to create one." |
| Search results | No matches | "No reports match your search criteria." |
| Pending approvals | None pending | "No reports pending approval." |
| Deleted reports | None deleted | "No deleted reports." |
| Version history | N/A | Always has at least v1 |
| Logs | No logs in range | "No activity logs for the selected period." |

---

## 13. Confirmation Dialogs

All confirmations use simple Yes/No pattern except:

| Action | Confirmation Type |
|--------|-------------------|
| Delete report | Yes/No with message |
| Permanent delete | Type "DELETE" to confirm |
| Reject report | Requires comment before confirm enabled |
| Rework request | Requires comment before confirm enabled |
| Bulk delete | Yes/No with count ("Delete 5 reports?") |
| Bulk submit | Yes/No with count ("Submit 3 reports for approval?") |

---

## 14. Edge Cases & Scenarios

### User & Session Edge Cases

| Scenario | Behavior |
|----------|----------|
| User deactivated in app mid-session? | Force logout on next action, show "Account deactivated" |
| Can admin deactivate themselves? | No - block with "Cannot deactivate your own account" |
| Last admin tries to deactivate themselves? | Block - system must have at least one active admin |
| Same user logs in from multiple devices? | Allowed - each device has separate session |
| Multiple browser tabs? | Share same session |
| Role changed by admin mid-session? | Takes effect on next login |
| User not in app but authenticates via IDSS? | Show "No access to this system - contact administrator" |
| User deleted from IDSS entirely? | Cannot authenticate; existing reports remain under their name |

### Report Edge Cases

| Scenario | Behavior |
|----------|----------|
| Two users create report at exact same millisecond? | Database handles - sequential numbers guaranteed unique |
| Year/month changes during save? | Use timestamp when Save clicked |
| Server clock is wrong? | Use server time regardless - IT responsibility |
| Can you delete a Pending report? | No - must approve/reject/rework first |
| Can you edit a Pending report? | No - wait for approval decision |
| RBS/SAS data changes after report created? | Report keeps original data (point-in-time snapshot) |
| CIC was in deleted report, can create new? | Yes - deleted reports don't block new ones for same CIC |
| Case ID was in deleted report, can create new? | Yes - deleted reports don't block new ones for same Case ID |
| Browser crashes with unsaved data? | Data lost, lock released on session timeout |
| Navigate away with unsaved changes? | Browser shows "You have unsaved changes" prompt |

### CIC Lookup & Uniqueness Edge Cases

| Scenario | Behavior |
|----------|----------|
| CIC already has a report in system? | Block creation with "A report already exists for this CIC" |
| CIC check - which statuses count? | All statuses (Draft, Pending, Approved, Rejected, Rework) |
| CIC check - does deleted report count? | No - deleted reports don't block |
| CIC triggers both RBS and SAS? | Yes - single CIC entry triggers both lookups |
| SAS returns no Case ID for CIC? | Allow report creation, Case ID optional |
| SAS returns multiple Case IDs? | Display as dropdown, user selects one |
| User changes CIC after selecting Case ID? | Clear Case ID selection, re-trigger lookups |

### Month Grace Period Edge Cases

| Scenario | Behavior |
|----------|----------|
| February starts, January not closed? | Reports continue as 2026/01/NNNN until admin closes January |
| Admin closes January in March? | January reports finalized, new reports use current month |
| Can admin re-open a closed month? | No - once closed, month is final |
| What happens to in-progress drafts when month closes? | Drafts keep their original month number |
| Month close - does it affect existing reports? | No - only affects new report number generation |

### Admin Editable Fields Edge Cases

| Scenario | Behavior |
|----------|----------|
| Admin edits lookup field, then clicks Re-lookup? | All lookup fields refresh from RBS/SAS, overwriting manual edits |
| Re-lookup button available for Agent? | No - only Administrator |
| Agent tries to edit lookup field? | Field is read-only, cannot edit |
| Admin changes Account Number manually? | Allowed - admin can override any lookup field |
| Admin clears a required lookup field? | Validation fails on Save (but not Save Draft) |

### "Other" Selection Edge Cases

| Scenario | Behavior |
|----------|----------|
| User selects "Other" in dropdown? | Text area appears below dropdown, min 10 characters required |
| User switches from "Other" to another value? | Text area hides, "Other" text is cleared |
| User switches back to "Other"? | Text area shows empty, must re-enter |
| "Other" text has less than 10 chars on Save? | Validation error: "Minimum 10 characters required" |
| "Other" text on Save Draft? | No minimum validation for drafts |
| Which dropdowns have "Other" option? | All: Transaction Type, Report Source, FIU Feedback, 2nd Reason for Suspicion |

### Column Visibility Edge Cases

| Scenario | Behavior |
|----------|----------|
| Admin hides all columns for Reporter? | At least Report Number must remain visible |
| Column hidden in list but shown in detail? | Yes - visibility only affects list view |
| Hidden column in export? | Follow same visibility rules as list |
| Agent sees hidden columns? | Yes - Agents see all columns (restriction is Reporter only) |

### Version & Rollback Edge Cases

| Scenario | Behavior |
|----------|----------|
| Rollback creates new version or overwrites? | Creates new version (v1→v2→v3→rollback to v1 = v4 with v1 content) |
| How many versions to keep? | All versions, forever |
| Can you rollback to current version? | No - button hidden for current version |
| Version diff - show what? | All fields side by side, changed fields highlighted |

### Bulk Operations Edge Cases

| Scenario | Behavior |
|----------|----------|
| Bulk submit - some fail validation? | Submit valid ones, show list of failures with reasons |
| Bulk delete - some are Pending? | Skip Pending, delete eligible ones, show message |
| Bulk approve? | Not supported - review one at a time |
| Select all + bulk action on 1000 reports? | Process all, show progress |

### Search & Filter Edge Cases

| Scenario | Behavior |
|----------|----------|
| Search - exact or partial match? | Partial (contains) |
| Search - case sensitive? | No |
| Search multiple fields at once? | Yes - searches across Report #, Customer Name, CIC, Case ID, Account Number |
| Date range - inclusive? | Yes, both start and end dates included |
| End date before start date? | Block with "End date must be after start date" |
| Clear filters - result? | Remove all filters, show all data |
| Filter + export - what exports? | Filtered data only |

### Dropdown Edge Cases

| Scenario | Behavior |
|----------|----------|
| Can you delete a dropdown value? | No - only deactivate |
| Deactivated value on existing reports? | Remains visible (read-only), can't be selected for new reports |
| Can display order have duplicates (1, 1, 2)? | No - must be unique within category |
| Can dropdown code be changed after creation? | No - code is immutable |
| Empty dropdown category? | At least one active value required |

### Approval Queue Edge Cases

| Scenario | Behavior |
|----------|----------|
| Approval queue order? | Oldest first (FIFO) |
| Can admin edit report during approval? | No - approve, reject, or rework only |
| Agent deactivated with pending reports? | Reports stay pending; admin can reassign on rework |
| Rework reassignment - how to select agent? | Dropdown of all active agents |
| Multiple admins approve same report simultaneously? | First one wins, second sees "Already processed" |

### Account/Membership Selection Edge Cases

| Scenario | Behavior |
|----------|----------|
| Customer has 50 accounts? | Show scrollable dropdown list |
| User picks wrong account, can they change? | Yes, until report is submitted |
| No accounts returned from RBS? | Allow manual entry of account field |
| Both account and membership returned? | Show both, user picks which to use |

### Form & Validation Edge Cases

| Scenario | Behavior |
|----------|----------|
| Can you skip tabs in form? | Yes - tabs are navigation only |
| Required fields validated per tab or on submit? | On submit (and on Save, not Save Draft) |
| Can you submit with only required fields filled? | Yes |
| Auto-save drafts? | No - manual save only |
| Tab order in form? | Standard: left to right, top to bottom |
| Keyboard navigation? | Standard browser behavior |

### Data Display Edge Cases

| Scenario | Behavior |
|----------|----------|
| isLegalOwner display format? | "Yes" or "No" (not checkbox in view mode) |
| Gender display? | Full text from RBS (e.g., "Male", "Female") |
| Nationality display? | Full country name from RBS |
| Branch ID display? | Code only (what RBS returns) |
| Very long customer name? | Truncate with ellipsis in list, full in detail view |

### Logs Edge Cases

| Scenario | Behavior |
|----------|----------|
| Audit log fails to write? | Continue operation, log failure to system error log (IT handles) |
| Log filter options? | Date range, username, action type |
| Logs pagination? | Same as reports list (10, 25, 50, 100, All) |
| Export deleted reports to Excel? | Admin can export from Deleted Reports screen |
| Log IP address - internal or external? | Internal network IP |

### Integration Edge Cases

| Scenario | Behavior |
|----------|----------|
| RBS returns partial data? | Populate what's returned, enable manual entry for empty fields |
| RBS returns unexpected field format? | Accept as-is, display as-is |
| SAS returns case but no creation date? | Allow manual entry for missing field |
| CIC lookup while RBS is slow? | Show loading indicator, timeout after 30 seconds |
| Retry button clicked multiple times? | Disable button during request, re-enable on response |

### User Management Edge Cases

| Scenario | Behavior |
|----------|----------|
| Add user flow? | Admin searches IDSS by username, selects user, assigns role, saves |
| User already exists in app? | Block with "User already exists" |
| Username not found in IDSS? | Show "User not found in Identity Self Service" |
| Can you delete a user from app? | No - only deactivate |
| What happens to deactivated user's reports? | Remain under their name, can still be viewed/edited by admin |
| First admin setup? | IT seeds first admin account during deployment |
| Can you change a user's username? | No - username comes from IDSS, immutable |

### UI Behavior Edge Cases

| Scenario | Behavior |
|----------|----------|
| Home page report list - admin sees what? | All reports (admin sees everything) |
| Home page report order? | Same as Reports list (newest first) |
| Report form - default tab? | First tab (Case Info) |
| View action - opens what? | Same form, but all fields read-only |
| Actions menu style? | Dropdown menu (three dots icon) |
| Edit approved report - needs re-approval? | No - stays Approved, version increments |
| Submit button - when enabled? | When status is Draft or Rework |
| Save Draft vs Save? | Save Draft = no validation; Save = validation required |
| Can Sending Date be in the future? | Yes - no restriction |
| History button - shows what? | Opens Version History panel for that report |
| Can reporter see approval comments? | Yes - view only |
| Created By / Updated By - show what? | Display Name (not username) |
| Approval/rework comments - where visible? | In Version History, attached to that version |
| New Report button visible to Reporter? | No - hidden for Reporter role |
| Pending Approvals menu - show count? | Yes - badge with count (e.g., "Pending Approvals (5)") |
| Click logo - does what? | Navigate to Home page |
| Side menu collapsible? | Developer choice |
| Deleted Reports screen - can filter? | Yes - same filters as Reports list |
| Settings - Save button or auto-save? | Save button (explicit save) |
| Backup - can admin trigger manually? | No - automated weekly only |
| Logs - click entry for details? | No - all info visible in list |
| Session timeout - based on what? | Inactivity (no clicks/typing for 30 min) |
| What counts as activity? | Any user interaction (click, scroll, type) |

### Status Flow Edge Cases

| Scenario | Behavior |
|----------|----------|
| Can status go backwards? | No - only forward through workflow |
| Agent edits Draft - status change? | Stays Draft |
| Agent submits - status change? | Draft → Pending Approval |
| Admin approves - status change? | Pending → Approved |
| Admin rejects - status change? | Pending → Rejected (final) |
| Admin requests rework - status change? | Pending → Rework |
| Agent resubmits after rework - status change? | Rework → Pending Approval |
| Admin edits Approved report - status? | Stays Approved (version increments) |
| Agent edits Approved report - status? | Stays Approved (version increments) |
| Can admin approve their own report? | N/A - admin reports skip workflow entirely |

### Navigation After Actions

| Action | Where User Goes |
|--------|-----------------|
| Save Draft | Stay on form |
| Save | Stay on form |
| Submit | Go to Reports list with success message |
| Cancel | Go to Reports list (with unsaved changes warning if applicable) |
| Approve | Next report in queue, or "No more pending" message |
| Reject | Next report in queue, or "No more pending" message |
| Request Rework | Next report in queue, or "No more pending" message |
| Delete report | Stay on Reports list, row removed |
| Restore report | Stay on Deleted Reports list, row removed |
| Permanent delete | Stay on Deleted Reports list, row removed |

### Message Display

| Type | Display Method |
|------|----------------|
| Success (save, submit, etc.) | Toast notification (auto-dismiss after 5 seconds) |
| Error (validation, network) | Inline on form OR toast for general errors |
| Confirmation required | Modal dialog |
| Info (report locked, etc.) | Banner at top of form |

### Timestamps Display

| Context | Format |
|---------|--------|
| In tables/lists | DD/MM/YYYY HH:mm |
| In version history | DD/MM/YYYY HH:mm |
| In audit logs | DD/MM/YYYY HH:mm:ss |
| Relative time ("2 hours ago") | Not used - always absolute |

### Limits & Boundaries

| Question | Answer |
|----------|--------|
| Max reports per agent? | No limit |
| Max rework cycles for a report? | No limit |
| Max pending reports? | No limit |
| Max users in system? | No limit |
| Max dropdown values per category? | No limit |
| Rows per page setting - per user? | Global default, users can change for their session (not saved) |
| Settings changes - when take effect? | Immediately |
| Auto-purge job fails? | IT responsibility - job retries |

### Quick Action Buttons (Home Page)

| Button | Action | Visible To |
|--------|--------|------------|
| New Report | Opens new report form | Agent, Administrator |
| View Reports | Goes to Reports list | Everyone |
| Export | Opens export dialog for all reports | Everyone |

### Approval Queue Table Columns

| Column | Description |
|--------|-------------|
| Report Number | Report number |
| Case ID | Case ID |
| Customer Name | Customer name (truncated) |
| Submitted By | Agent who submitted |
| Submitted Date | When submitted for approval |

---

## 15. Questions That Are NOT Business Decisions

If developers ask about any of these, they should decide themselves:

- "What color should the buttons be?"
- "Should we use tabs or accordion for the form?"
- "What icon should we use for delete?"
- "How should we structure the API endpoints?"
- "Should we use REST or GraphQL?"
- "What's the database schema?"
- "How do we handle database migrations?"
- "What's the deployment pipeline?"
- "How do we structure the codebase?"
- "What naming conventions for code?"

**These are implementation details, not business requirements.**

---

## 15. If Still Unclear

1. Check all BRD documents first
2. If truly ambiguous, make a reasonable decision and document it
3. Only escalate if the decision affects user-facing behavior significantly

**Default rule:** If in doubt, keep it simple. Don't over-engineer.

---

*End of Document*

**Back to:** [README.md](README.md)
