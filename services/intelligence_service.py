"""Report intelligence — read-only context that enriches data entry without
ever blocking it (#5, #14). Given a CIC or an account number, surface the
related reports already in the system so an analyst sees the fuller picture:
 - CIC history: every prior report on the same customer (a duplicate CIC is
   information, not an error — see the same subject's earlier filings).
 - Account rapid-repeat: multiple reports on one account inside a tight window
   is a classic structuring signal worth flagging.

All queries are read-only and scoped to non-deleted reports.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional


# report_date is stored as DD/MM/YYYY text; parse defensively.
def _parse_report_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _parse_amount(value) -> Optional[float]:
    """Best-effort numeric parse of a total_transaction cell (commas, currency)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    cleaned = "".join(c for c in s if c.isdigit() or c in ".-")
    try:
        return float(cleaned) if cleaned not in ("", ".", "-") else None
    except ValueError:
        return None


_PENDING_STATUSES = ("pending_approval", "rework")


class IntelligenceService:
    def __init__(self, db_manager, logging_service=None, now=None):
        self.db_manager = db_manager
        self.logger = logging_service
        self._now = now or datetime.now   # injectable for tests

    def _rows(self, where: str, params) -> List[Dict]:
        try:
            q = ("SELECT report_id, report_number, reported_entity_name, report_date, "
                 "approval_status, cic, account_membership, total_transaction, "
                 "report_classification, created_by, created_at "
                 "FROM reports WHERE is_deleted = 0 " + where +
                 " ORDER BY created_at DESC")
            res = self.db_manager.execute_with_retry(q, params)
            return [{k: r[k] for k in r.keys()} for r in (res or [])]
        except Exception as e:
            if self.logger:
                self.logger.error(f"IntelligenceService query failed: {e}")
            return []

    def _summarize(self, rows: List[Dict]) -> Dict[str, Any]:
        """Enriching aggregates over a set of related reports (#5 signal set)."""
        entities = list(dict.fromkeys(
            r.get("reported_entity_name") for r in rows if r.get("reported_entity_name")))
        classifications = list(dict.fromkeys(
            r.get("report_classification") for r in rows if r.get("report_classification")))
        amounts = [a for a in (_parse_amount(r.get("total_transaction")) for r in rows) if a is not None]
        pending = sum(1 for r in rows if (r.get("approval_status") or "") in _PENDING_STATUSES)

        # days since the most recent prior report on this key
        dates = [d for d in (_parse_report_date(r.get("report_date")) for r in rows) if d is not None]
        days_since_last = None
        if dates:
            days_since_last = (self._now() - max(dates)).days

        return {
            "entities": entities,
            "classifications": classifications,
            "amount_sum": round(sum(amounts), 2) if amounts else None,
            "amount_min": min(amounts) if amounts else None,
            "amount_max": max(amounts) if amounts else None,
            "pending": pending,
            "days_since_last": days_since_last,
        }

    def cic_history(self, cic: str, exclude_report_id: Optional[int] = None) -> Dict[str, Any]:
        """Prior reports sharing this CIC (excluding the report being edited),
        plus an enriching summary (#5). Returns {count, reports, summary}."""
        cic = (cic or "").strip()
        if not cic:
            return {"count": 0, "reports": [], "summary": self._summarize([])}
        where = "AND cic = ?"
        params: List[Any] = [cic]
        if exclude_report_id:
            where += " AND report_id != ?"
            params.append(exclude_report_id)
        rows = self._rows(where, params)
        return {"count": len(rows), "reports": rows, "summary": self._summarize(rows)}

    def account_rapid_repeat(self, account: str, report_date: str,
                             within_days: int = 2,
                             exclude_report_id: Optional[int] = None) -> Dict[str, Any]:
        """Other reports on the same account whose report_date falls within
        `within_days` of the given report_date — a structuring signal.
        Returns {count, reports, within_days}. count is OTHER reports (the one
        being entered is excluded), so count>=1 means a repeat.
        ponytail: window on report_date (the event date), not created_at."""
        account = (account or "").strip()
        anchor = _parse_report_date(report_date)
        if not account or anchor is None:
            return {"count": 0, "reports": [], "within_days": within_days}

        where = "AND account_membership = ?"
        params: List[Any] = [account]
        if exclude_report_id:
            where += " AND report_id != ?"
            params.append(exclude_report_id)

        near = []
        for r in self._rows(where, params):
            d = _parse_report_date(r.get("report_date"))
            if d is not None and abs((d - anchor).days) <= within_days:
                near.append(r)
        return {"count": len(near), "reports": near, "within_days": within_days}
