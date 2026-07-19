# Retrospective import — bringing 20 years of Excel history into STR

**Status:** approved design, not yet implemented
**Date:** 2026-07-19
**Owner decision record.** Every choice below was made by the FIU unit owner; the
reasoning is recorded so a later reader knows what was deliberate.

## The job

The unit has ~20 years of filed reports living in the previous team's Excel
files. Those files are being cleansed and enriched to match STR's fields. This
feature is the door they come through: **the app publishes a template, the
filled template is uploaded, and the history lands in the database.**

The goal, in the owner's words: *"imagine the FIU app existed from 2005 until
now"* — one continuous record, searchable, with the customer history visible at
the moment an analyst writes a new report.

Volume: **60,000+ reports.**

## What an imported record is

Historical rows go into the **same `reports` table** as live work. They are
searchable, they count in totals, and they feed the CIC intelligence banner.

They carry a distinct status, **`archived`**, because they never went through
this app's workflow. There is no approval row, no version history, and no
invented filer or approver — *"that workflow does not exist"*. `archived` sits
alongside the six workflow statuses (`draft`, `pending_fiu`, `pending_approval`,
`approved`, `rework`, `rejected`) rather than inside them, so nothing in the
approval machinery ever picks one up.

### Numbering

Each record **keeps its original `report_number` and serial number exactly**.
That is what was filed with the FIU and what an auditor will search for.

The import also writes each number into `reserved_numbers` with `status='used'`,
so the sequence knows the number is spent: *"2016/04/555 is registered because it
has been reserved by an archived report."* It can never be re-issued.

### Provenance

Every imported row records the file and upload it came from
(`import_batch_id`). This answers "where did this record come from?" for an
auditor, and it is what allows a bad batch to be removed cleanly.

### Editing

Archived records are editable by **anyone holding `edit_report`**.

This needs an explicit rule rather than an accident. Today an agent may only edit
reports they own (`has_permission('edit_report', resource_owner=...)`), and an
archived record has no owner — it would fall through an existing quirk where a
`None` owner grants access. So `update_report` will state the rule directly:
an `archived` record is editable by any holder of `edit_report`, regardless of
owner.

From the first edit onward the record gains normal version history, because
`update_report` versions every change. The archive stays honest without being
frozen against a genuine transcription error.

## The template

**The app generates the blank template** (Excel, via the openpyxl already
shipped). One column per field the importer reads, with the header row fixed to
exactly what it expects.

This kills the entire class of "the columns drifted" failure, because the file
always originates from the app rather than from someone's memory of the field
list.

## The import

**All-or-nothing per file.** Nothing is written unless every row is clean. The
owner chose this over partial import: cleansing happens in the source
spreadsheets, and the app is the strict gate.

Two passes:

1. **Validate the whole file.** Every row, every rule. Nothing is written.
   Produce one report of *every* problem found.
2. **If and only if that report is empty**, insert everything in a single
   transaction.

Because a rejected file writes nothing, re-uploading a corrected file is always
safe, and the same file uploaded twice fails on the unique report number rather
than duplicating anything.

Admin only.

### Validation at 60k rows

Per-row database queries would mean 120,000+ round trips. Instead the validator
loads the existing report numbers, serial numbers and CICs into memory once and
checks rows against those sets in a single pass.

It must also catch **duplicates within the file itself** — two rows claiming
2016/04/555 — which a database check alone would miss.

### The error report

A flat list of 5,000 errors is as useless as none. Errors are **grouped by
problem type** with a count and examples:

```
CIC is not 16 digits          412 rows   (first 20: 88, 143, 190, ...)
report_date unparseable        37 rows   (first 20: 22, 511, ...)
report_number already in STR    3 rows   (rows 9001, 9002, 9003)
duplicate within this file      2 rows   (rows 4120 and 8899 both 2016/04/555)
```

Full per-row detail goes to a rejects sheet. The analyst fixes a class of
problem at a time rather than a row at a time.

### Performance

- Read with openpyxl in read-only mode so a 60k-row file streams rather than
  loading whole.
- Insert in one transaction — 60k rows is a few seconds in SQLite — but report
  progress, because a UI that appears frozen for 30 seconds gets killed by the
  user.

### A note on file size

With 60k rows in one file, a single bad cell rejects everything, and several
rounds are likely. **Splitting by year (20 files of ~3k) lets 2005 land while
2011 is still being cleaned**, and each rejection carries less to fix. The
import supports either; this is a workflow choice, not a code change.

## What this changes elsewhere

**CIC lookup.** Historical filings appear in the customer's intelligence banner,
so an analyst sees the full 20-year picture before writing. The
one-live-report-per-CIC rule counts **only live reports** — an archived record
never blocks a new filing. This is the payoff that makes the import worth doing.

**Dashboards.** Totals, by-month and by-classification include archived records,
so the charts run back to 2005. Rework rate and approval turnaround do **not**,
because those measure a workflow these records never went through. Nothing
imported can distort how the current team is measured.

**Numbering.** Unchanged for live use. The sequence simply knows more numbers are
spent.

## Explicitly out of scope

- No workflow for archived records: they are never submitted, approved, reworked
  or rejected.
- No synthetic users for people who have left.
- No in-app queue for fixing bad rows — cleansing happens in Excel.
- No partial or resumable import.

## Decisions that need the real data to confirm

**FIU fields are optional on an archived row.** `fiu_number` and `fiu_date` gate
*submission* for a live report, and an archived row is never submitted, so the
gate does not apply. They are imported when the Excel has them and left empty
when it does not. If it turns out every historical row does carry an FIU number,
making them required would be a one-line change to the validator.

**Required fields on an archived row are: `report_number`, `sn`, `report_date`
and `reported_entity_name`** — the same four the live create path enforces, and
the minimum for a record to be identifiable and searchable. Everything else is
imported when present. This needs one look at a real spreadsheet to confirm the
old data actually carries all four for every row; if it does not, the gap is a
data-cleansing problem to solve before import, not a rule to relax.

**The template column set** is derived from `column_settings` (the same source
the form labels come from), so it stays in step with the app automatically. It
must be checked against one real Excel file before the first import, to catch
fields the old team recorded that STR has no column for.
