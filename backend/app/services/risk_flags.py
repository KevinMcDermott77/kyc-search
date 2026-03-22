"""
Compute risk flags for a company based on available data.
Returns a list of flag strings stored in Company.risk_flags.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Company, Officer, Psc

# Thresholds
FREQUENT_RESIGNATIONS_COUNT = 3
FREQUENT_RESIGNATIONS_MONTHS = 12
RECENT_CHANGES_DAYS = 90


def compute_risk_flags(
    company: "Company",
    officers: list["Officer"],
    pscs: list["Psc"],
) -> list[str]:
    flags: list[str] = []

    if company.accounts_overdue:
        flags.append("OVERDUE_ACCOUNTS")

    if company.confirmation_statement_overdue:
        flags.append("OVERDUE_CS")

    if company.has_insolvency_history:
        flags.append("INSOLVENCY_HISTORY")

    # Frequent resignations in the past year
    cutoff = date.today() - timedelta(days=FREQUENT_RESIGNATIONS_MONTHS * 30)
    recent_resignations = [
        o for o in officers
        if o.resigned_on and o.resigned_on >= cutoff
    ]
    if len(recent_resignations) >= FREQUENT_RESIGNATIONS_COUNT:
        flags.append("FREQUENT_RESIGNATIONS")

    # Recent director / officer changes
    recent_cutoff = date.today() - timedelta(days=RECENT_CHANGES_DAYS)
    recent_appointments = [
        o for o in officers
        if o.appointed_on and o.appointed_on >= recent_cutoff
    ]
    if recent_appointments:
        flags.append("RECENT_OFFICER_CHANGES")

    # No PSCs registered
    active_pscs = [p for p in pscs if not p.ceased_on]
    if not active_pscs:
        flags.append("NO_ACTIVE_PSCS")

    return flags
