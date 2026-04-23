"""Extract a DashaDossier from computed dasha data and natal chart.

Converts the raw Vimshottari dasha stack into a flat, LLM-friendly
structure capturing the current MD/AD/PD periods, their relationships,
and upcoming transitions.
"""

from datetime import datetime
from vedic_llm.models.chart import Chart, BirthData
from vedic_llm.models.enums import Planet
from vedic_llm.models.dossier import DashaDossier
from vedic_llm.compute.dasha import current_dasha_stack, upcoming_transitions, DashaPeriod
from vedic_llm.compute.dignity import NATURAL_FRIENDS


def _relationship(p1, p2) -> str:
    info = NATURAL_FRIENDS.get(p1)
    if not info:
        return "neutral"
    if p2 in info.get("friends", []):
        return "friend"
    if p2 in info.get("enemies", []):
        return "enemy"
    return "neutral"


def _period_to_dict(p: DashaPeriod) -> dict:
    return {
        "lord": p.lord.value,
        "level": p.level,
        "start": str(p.start),
        "end": str(p.end),
    }


def _activated_houses(lord: Planet, chart: Chart) -> list[int]:
    """Houses activated by a dasha lord: houses it rules + house it sits in."""
    ps = chart.planets.get(lord)
    houses = []
    if ps:
        houses.append(ps.house)
    for h_num, house in chart.houses.items():
        if house.lord == lord:
            houses.append(h_num)
    return sorted(set(houses))


def extract_dasha_dossier(birth: BirthData, natal: Chart, at: datetime) -> DashaDossier:
    """Build the dasha dossier for a given moment in time."""
    # Get Moon's longitude for dasha computation
    moon_lon = natal.planets[Planet.MOON].longitude

    stack = current_dasha_stack(birth, moon_lon, at)
    transitions = upcoming_transitions(birth, moon_lon, at)

    md = stack["MD"]
    ad = stack["AD"]
    pd = stack["PD"]

    md_houses = _activated_houses(md.lord, natal)
    ad_houses = _activated_houses(ad.lord, natal)
    pd_houses = _activated_houses(pd.lord, natal)

    doubly = sorted(set(md_houses) & set(ad_houses))

    return DashaDossier(
        current_md=_period_to_dict(md),
        current_ad=_period_to_dict(ad),
        current_pd=_period_to_dict(pd),
        md_ad_relationship=_relationship(md.lord, ad.lord),
        ad_pd_relationship=_relationship(ad.lord, pd.lord),
        doubly_activated_houses=doubly,
        upcoming_transitions=[_period_to_dict(t) for t in transitions[:10]],
    )
