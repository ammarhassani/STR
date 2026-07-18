# Bilingual (Arabic / English) — Implementation Plan (#3)

**Goal:** the whole app is either fully English or fully Arabic — never mixed —
chosen per user at onboarding and toggled in settings. The database stores
language-neutral values so switching language re-localizes existing data.

**Locked decisions (owner-approved):**
- Full UI translation **+ RTL** for Arabic.
- Language is **per-user** (like the theme), picked at onboarding, toggled in settings.
- Data is stored as **language-neutral codes**; labels are rendered per language.
- Sequenced **after** the two-way handshake (#1, done).

---

## The hard dependency: translation content

Code can build the machinery; it cannot invent correct FIU Arabic. Two content
sets are required and must be owner-supplied or owner-reviewed:

1. **Dropdown value pairs** — every dropdown value needs `code · English · Arabic`.
   `fields.xlsx` has the raw values but **unpaired and mixed** (Arabic suspicion
   reasons + transaction types; English classifications + source systems). Someone
   who knows the domain must pair them (which English = which Arabic) and assign a
   stable code.
2. **UI strings** — every label/button/message needs an Arabic translation.
   FIU/AML terminology must be accurate; machine translation is a draft at best.

**Open question for the owner:** provide these, or have me draft them (best-effort
from `fields.xlsx` + domain knowledge) for your review? Nothing in Phases 1–2 can
be called "done" until the content is real.

---

## Architecture

- `flet_app/i18n/` — `catalog_en.py`, `catalog_ar.py` (key → string dicts) + a
  tiny `t(key, **fmt)` that reads the current language. Missing key → falls back
  to English + logs (so gaps are visible, never silent mojibake).
- `users.language TEXT DEFAULT 'en'` (mirrors `theme_preference`). Applied on login.
- `page.rtl = (lang == 'ar')`; direction-aware layout where it matters.
- Dropdown data model: values carry `code`, `label_en`, `label_ar`. Reports store
  the **code**. `get_active_dropdown_values(category, lang)` returns
  `[(code, label)]`; forms bind the code, show the label.

---

## Phases (each independently testable, shipped in order)

### Phase 0 — Infrastructure (CODE ONLY, no translations needed) — ✅ DONE
- ✅ `users.language` column (schema + migration).
- ✅ `flet_app/i18n/` module + `t()` + `catalog_en.py` / `catalog_ar.py` (login,
  onboarding, common, nav keys); English source of truth, Arabic drafted, missing
  key → English fallback + log.
- ✅ Apply language on login (`app_state.login` sets it; user dict carries it
  through the host in client mode); `page.rtl` switch on login + pre-login default.
- ✅ Per-user language toggle in the header (reaches every user); `set_user_language`
  is a write command (host-routed in client mode).
- ✅ Login screen translated as the pattern.
- Deferred within Phase 0: onboarding-dialog + setup-wizard language pickers (the
  header toggle + deployment default cover the need; add pickers in a later pass).
- **Delivered:** plumbing works end-to-end (`tests_i18n.py`); app still English
  because catalogs are seeded for the login/onboarding pattern only. No mixed data.

### Phase 1 — Dropdown / field data → codes  (NEEDS content set #1)
**Phase 1a — bilingual labels + resolution (additive, non-breaking) — ✅ DONE**
- ✅ `system_config.config_value_ar` column (schema + migration). `config_key` is
  the language-neutral CODE; `config_value` = English label, `config_value_ar` =
  Arabic label.
- ✅ Drafted Arabic for all 7 active categories (gender, nationality,
  report_classification, report_source, reporting_entity, fiu_feedback,
  type_of_suspected_transaction — 71 values). `arb_staff` skipped (its EN/AR
  divergence is a separate semantic question); `second_reason_for_suspicion` is
  now free text (#13) so its old 157 dropdown values are dead/ignored.
- ✅ `dropdown_service.get_active_options(category, lang)` → `[(code, label)]` and
  `resolve_label(category, code_or_value, lang)` (accepts a code OR a legacy stored
  label; unknown values pass through). Existing `get_active_dropdown_values`
  unchanged — nothing breaks. `tests_dropdown_i18n.py`.
- **Owner review point:** the drafted Arabic labels in migration `ar_pairs`.

**Phase 1b — flip storage to codes (BREAKING, deliberate) — TODO**
- Forms bind `code` (option key), show `label` per language, store the code.
- Migration converts existing report field values (stored labels) → codes (safe
  now: pre-go-live data will be hard-reset anyway).
- Every consumer resolves codes → labels: report detail/edit, approval panel,
  reports list, **export** (must emit labels, not codes), and **BI widgets**
  (group-by on these columns now yields codes — chart labels must resolve).
- **Deliverable:** dropdowns + stored data are language-neutral; switching language
  re-localizes them. "No mixed values in the DB" achieved for data.

### Phase 2 — UI string translation  (NEEDS content set #2)
- Replace hardcoded strings with `t()` keys across every view; fill
  `catalog_ar.py`.
- **Deliverable:** the entire UI flips language.

### Phase 3 — RTL polish
- Layout mirroring, icon/alignment direction, number/date presentation review.
- **Deliverable:** Arabic reads correctly right-to-left throughout.

---

## Notes
- Admin-configurable dropdowns (the #17 dashboard widgets, dropdown management)
  must edit both labels; the config UI grows an Arabic field.
- Schema seeds must ship both languages for defaults (owner requirement).
- Effort is dominated by content (Phases 1–2), not code. Phase 0 is buildable now.
