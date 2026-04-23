"""Extract a TransitDossier from computed transit data overlaid on a natal chart.

Converts the raw transit snapshot into a flat, LLM-friendly structure
capturing current transit positions, natal overlays, Sade Sati status,
and which natal houses are most actively stimulated.
"""

from datetime import datetime
from vedic_llm.models.chart import Chart
from vedic_llm.models.enums import Planet
from vedic_llm.models.dossier import TransitDossier
from vedic_llm.compute.transit import snapshot


def extract_transit_dossier(natal: Chart, at: datetime) -> TransitDossier:
    """Build the transit dossier for a given moment overlaid on a natal chart."""
    snap = snapshot(natal, at)

    transit_positions = {}
    for planet, info in snap.transit_planets.items():
        transit_positions[planet.value] = {
            "sign": info["sign"].name.title(),
            "degree": round(info["degree"], 2),
            "house_from_natal": info["house_from_natal"],
            "retrograde": info["retrograde"],
        }

    overlays = []
    for tp, np, orb in snap.transit_over_natal:
        overlays.append({
            "transit_planet": tp.value,
            "natal_planet": np.value,
            "orb": orb,
        })

    # Active natal houses = houses receiving slow planet transits (Saturn, Jupiter, Rahu, Ketu)
    slow_planets = [Planet.SATURN, Planet.JUPITER, Planet.RAHU, Planet.KETU]
    active = []
    for sp in slow_planets:
        if sp in snap.transit_planets:
            active.append(snap.transit_planets[sp]["house_from_natal"])

    return TransitDossier(
        timestamp=str(at),
        transit_positions=transit_positions,
        transit_overlays=overlays,
        sade_sati=snap.sade_sati,
        jupiter_from_moon=snap.jupiter_from_moon,
        active_natal_houses=sorted(set(active)),
    )
