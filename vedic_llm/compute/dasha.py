"""Vimshottari Dasha computation."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from vedic_llm.models.enums import Planet, Nakshatra
from vedic_llm.models.chart import BirthData

# Vimshottari cycle: 120 years total
DASHA_YEARS = {
    Planet.KETU: 7, Planet.VENUS: 20, Planet.SUN: 6, Planet.MOON: 10,
    Planet.MARS: 7, Planet.RAHU: 18, Planet.JUPITER: 16,
    Planet.SATURN: 19, Planet.MERCURY: 17,
}

# The dasha sequence order
DASHA_SEQUENCE = [
    Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS,
    Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY,
]

TOTAL_YEARS = 120.0
YEAR_DAYS = 365.25


@dataclass
class DashaPeriod:
    lord: Planet
    level: str  # "MD", "AD", "PD"
    start: datetime
    end: datetime
    parent: Optional['DashaPeriod'] = None


def _nakshatra_lord(nak: Nakshatra) -> Planet:
    """Return the Vimshottari dasha lord for a nakshatra."""
    return nak.lord  # Uses the lord property defined in the enum


def compute_dasha_balance_at_birth(moon_longitude: float) -> tuple[Planet, float]:
    """Given Moon's sidereal longitude, return (starting MD lord, fraction remaining in that MD).

    Each nakshatra = 13°20' = 13.3333°
    The Moon's position within the nakshatra determines how much of the first dasha has elapsed.
    """
    nak_span = 360.0 / 27.0  # 13.3333°
    nak_index = int(moon_longitude / nak_span)  # 0-26
    nak_index = min(nak_index, 26)

    # Get the nakshatra enum (1-indexed)
    nakshatra = Nakshatra(nak_index + 1)
    lord = _nakshatra_lord(nakshatra)

    # How far through this nakshatra is the Moon?
    position_in_nak = moon_longitude - (nak_index * nak_span)
    fraction_elapsed = position_in_nak / nak_span
    fraction_remaining = 1.0 - fraction_elapsed

    return lord, fraction_remaining


def compute_mahadasha_sequence(birth: BirthData, moon_longitude: float) -> list[DashaPeriod]:
    """Compute the full Mahadasha sequence from birth.

    Returns list of 9+ MDs covering 120 years from birth.
    """
    starting_lord, fraction_remaining = compute_dasha_balance_at_birth(moon_longitude)

    # Find starting lord's index in sequence
    start_idx = DASHA_SEQUENCE.index(starting_lord)

    periods = []
    current_date = birth.datetime_utc

    # First MD: only the remaining fraction
    first_duration_days = DASHA_YEARS[starting_lord] * YEAR_DAYS * fraction_remaining
    first_end = current_date + timedelta(days=first_duration_days)
    periods.append(DashaPeriod(
        lord=starting_lord, level="MD",
        start=current_date, end=first_end
    ))
    current_date = first_end

    # Subsequent MDs: cycle through the sequence
    for i in range(1, 10):  # at most 9 more to cover 120 years
        idx = (start_idx + i) % 9
        lord = DASHA_SEQUENCE[idx]
        duration_days = DASHA_YEARS[lord] * YEAR_DAYS
        end = current_date + timedelta(days=duration_days)
        periods.append(DashaPeriod(lord=lord, level="MD", start=current_date, end=end))
        current_date = end

    return periods


def compute_antardasha(md: DashaPeriod) -> list[DashaPeriod]:
    """Compute Antardashas within a Mahadasha.

    AD sequence starts from the MD lord and follows Vimshottari order.
    Each AD's duration = (MD_years * AD_lord_years / 120) years.
    """
    md_duration = (md.end - md.start).total_seconds()
    start_idx = DASHA_SEQUENCE.index(md.lord)

    periods = []
    current = md.start

    for i in range(9):
        idx = (start_idx + i) % 9
        ad_lord = DASHA_SEQUENCE[idx]
        # Proportion = AD lord's years / total 120 years
        ad_fraction = DASHA_YEARS[ad_lord] / TOTAL_YEARS
        ad_seconds = md_duration * ad_fraction
        end = current + timedelta(seconds=ad_seconds)
        periods.append(DashaPeriod(
            lord=ad_lord, level="AD",
            start=current, end=end, parent=md
        ))
        current = end

    return periods


def compute_pratyantardasha(ad: DashaPeriod) -> list[DashaPeriod]:
    """Compute Pratyantar dashas within an Antardasha. Same proportional logic."""
    ad_duration = (ad.end - ad.start).total_seconds()
    start_idx = DASHA_SEQUENCE.index(ad.lord)

    periods = []
    current = ad.start

    for i in range(9):
        idx = (start_idx + i) % 9
        pd_lord = DASHA_SEQUENCE[idx]
        pd_fraction = DASHA_YEARS[pd_lord] / TOTAL_YEARS
        pd_seconds = ad_duration * pd_fraction
        end = current + timedelta(seconds=pd_seconds)
        periods.append(DashaPeriod(
            lord=pd_lord, level="PD",
            start=current, end=end, parent=ad
        ))
        current = end

    return periods


def current_dasha_stack(birth: BirthData, moon_longitude: float, at: datetime) -> dict[str, DashaPeriod]:
    """Returns {'MD': period, 'AD': period, 'PD': period} active at the given datetime."""
    mds = compute_mahadasha_sequence(birth, moon_longitude)

    # Find current MD
    current_md = None
    for md in mds:
        if md.start <= at < md.end:
            current_md = md
            break

    if not current_md:
        # If 'at' is before birth or after 120 years, use first/last
        current_md = mds[0] if at < mds[0].start else mds[-1]

    # Find current AD within MD
    ads = compute_antardasha(current_md)
    current_ad = None
    for ad in ads:
        if ad.start <= at < ad.end:
            current_ad = ad
            break
    if not current_ad:
        current_ad = ads[0]

    # Find current PD within AD
    pds = compute_pratyantardasha(current_ad)
    current_pd = None
    for pd in pds:
        if pd.start <= at < pd.end:
            current_pd = pd
            break
    if not current_pd:
        current_pd = pds[0]

    return {"MD": current_md, "AD": current_ad, "PD": current_pd}


def upcoming_transitions(birth: BirthData, moon_longitude: float, at: datetime, years_ahead: int = 5) -> list[DashaPeriod]:
    """List upcoming MD and AD transitions within years_ahead from 'at'."""
    cutoff = at + timedelta(days=years_ahead * YEAR_DAYS)
    transitions = []

    mds = compute_mahadasha_sequence(birth, moon_longitude)
    for md in mds:
        if md.start > at and md.start < cutoff:
            transitions.append(md)
        if md.end > at:
            ads = compute_antardasha(md)
            for ad in ads:
                if ad.start > at and ad.start < cutoff:
                    transitions.append(ad)

    transitions.sort(key=lambda p: p.start)
    return transitions
