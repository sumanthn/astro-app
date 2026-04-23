"""Extract a NatalDossier from computed D1, D9, and D10 charts.

Converts the raw compute-layer output into a flat, LLM-friendly
fact structure containing every piece of information an astrologer
would reference when reading a natal chart.
"""

from datetime import datetime
from vedic_llm.models.chart import Chart, BirthData
from vedic_llm.models.enums import Planet, Sign, Dignity
from vedic_llm.models.dossier import NatalDossier, PlanetFacts, HouseFacts
from vedic_llm.compute.dignity import SIGN_LORD, EXALTATION
from vedic_llm.compute.aspects import aspects_cast_by, populate_house_aspects
from vedic_llm.compute.yogas import detect_yogas, papa_kartari, shubha_kartari


# Natural karakas for each house
HOUSE_KARAKAS = {
    1: Planet.SUN, 2: Planet.JUPITER, 3: Planet.MARS,
    4: Planet.MOON, 5: Planet.JUPITER, 6: Planet.MARS,
    7: Planet.VENUS, 8: Planet.SATURN, 9: Planet.JUPITER,
    10: Planet.SUN, 11: Planet.JUPITER, 12: Planet.SATURN,
}

# Functional benefics/malefics vary by ascendant. This is a simplified version.
# For yogakaraka: Mars for Cancer/Leo asc, Saturn for Taurus/Libra, Venus for Cap/Aquarius
YOGAKARAKAS = {
    Sign.CANCER: Planet.MARS, Sign.LEO: Planet.MARS,
    Sign.TAURUS: Planet.SATURN, Sign.LIBRA: Planet.SATURN,
    Sign.CAPRICORN: Planet.VENUS, Sign.AQUARIUS: Planet.VENUS,
}


def _format_degree(deg: float) -> str:
    """Format degree as '18\u00b042'"""
    d = int(deg)
    m = int((deg - d) * 60)
    return f"{d}\u00b0{m:02d}'"


def _karaka_state(planet: Planet, chart: Chart) -> str:
    ps = chart.planets.get(planet)
    if not ps:
        return "neutral"
    if ps.dignity in (Dignity.EXALTED, Dignity.MOOLATRIKONA, Dignity.OWN):
        return "strong"
    if ps.dignity in (Dignity.DEBILITATED, Dignity.GREAT_ENEMY):
        return "afflicted"
    if ps.combust:
        return "afflicted"
    return "neutral"


def _functional_nature(planet: Planet, asc_sign: Sign) -> str:
    """Simplified functional nature for a planet given the ascendant."""
    yk = YOGAKARAKAS.get(asc_sign)
    if yk and planet == yk:
        return "yogakaraka"
    # Kendra lords (1,4,7,10) and trikona lords (1,5,9) are generally benefic
    # Dusthana lords (6,8,12) are generally malefic
    # This is a simplification
    return "neutral"


def _rules_houses(planet: Planet, chart: Chart) -> list[int]:
    """Which houses does this planet lord?"""
    result = []
    for h_num, house in chart.houses.items():
        if house.lord == planet:
            result.append(h_num)
    return sorted(result)


def _atmakaraka(chart: Chart) -> Planet:
    """Highest degree planet (excluding Rahu/Ketu in some traditions. Include all here.)"""
    # Use degree_in_sign for Jaimini atmakaraka
    candidates = {p: ps.degree_in_sign for p, ps in chart.planets.items()
                  if p not in (Planet.RAHU, Planet.KETU)}
    return max(candidates, key=candidates.get)


def _amatyakaraka(chart: Chart) -> Planet:
    """Second highest degree planet."""
    candidates = {p: ps.degree_in_sign for p, ps in chart.planets.items()
                  if p not in (Planet.RAHU, Planet.KETU)}
    sorted_planets = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    return sorted_planets[1][0] if len(sorted_planets) > 1 else sorted_planets[0][0]


def extract_natal_dossier(d1: Chart, d9: Chart, d10: Chart) -> NatalDossier:
    """Build the complete natal dossier from computed charts."""
    populate_house_aspects(d1)

    yogas = detect_yogas(d1)
    asc = d1.ascendant_sign

    # Build planet facts
    planets_facts = {}
    for planet, ps in d1.planets.items():
        d9_ps = d9.planets.get(planet)
        d10_ps = d10.planets.get(planet)

        # Find conjunctions (other planets in same house)
        conjunctions = [p.value for p, ops in d1.planets.items()
                       if p != planet and ops.house == ps.house]

        pf = PlanetFacts(
            planet=planet.value,
            sign=ps.sign.name.title(),
            degree=_format_degree(ps.degree_in_sign),
            house=ps.house,
            nakshatra=ps.nakshatra.name.replace("_", " ").title(),
            pada=ps.pada,
            dignity=ps.dignity.value,
            retrograde=ps.retrograde,
            combust=ps.combust,
            vargottama=ps.vargottama,
            aspects_cast_on_houses=aspects_cast_by(planet, ps.house),
            conjunctions=conjunctions,
            rules_houses=_rules_houses(planet, d1),
            functional_nature=_functional_nature(planet, asc),
            d9_sign=d9_ps.sign.name.title() if d9_ps else "",
            d9_dignity=d9_ps.dignity.value if d9_ps else "",
            d9_house_from_d9_lagna=d9_ps.house if d9_ps else 0,
            d10_sign=d10_ps.sign.name.title() if d10_ps else "",
            d10_house=d10_ps.house if d10_ps else 0,
        )
        planets_facts[planet.value] = pf

    # Build house facts
    houses_facts = {}
    for h_num, house in d1.houses.items():
        lord = house.lord
        lord_ps = d1.planets.get(lord)
        karaka = HOUSE_KARAKAS.get(h_num, Planet.SUN)

        hf = HouseFacts(
            number=h_num,
            sign=house.sign.name.title(),
            lord=lord.value,
            lord_sign=lord_ps.sign.name.title() if lord_ps else "",
            lord_house=lord_ps.house if lord_ps else 0,
            lord_dignity=lord_ps.dignity.value if lord_ps else "",
            lord_is_combust=lord_ps.combust if lord_ps else False,
            lord_is_retrograde=lord_ps.retrograde if lord_ps else False,
            occupants=[p.value for p in house.occupants],
            aspected_by=[p.value for p in house.aspected_by],
            is_hemmed_by_malefics=papa_kartari(d1, h_num),
            is_hemmed_by_benefics=shubha_kartari(d1, h_num),
            karaka=karaka.value,
            karaka_state=_karaka_state(karaka, d1),
        )
        houses_facts[h_num] = hf

    # Afflictions summary
    afflictions = []
    for h in range(1, 13):
        if papa_kartari(d1, h):
            afflictions.append({"type": "papa_kartari", "house": h})

    # Vargottama planets
    vargottama = [p.value for p, ps in d1.planets.items() if ps.vargottama]

    ak = _atmakaraka(d1)
    amk = _amatyakaraka(d1)

    # D9 summary
    d9_summary = {
        "ascendant": d9.ascendant_sign.name.title(),
        "ascendant_degree": round(d9.ascendant_degree, 2),
    }

    # Functional benefics/malefics (simplified)
    func_benefics = []
    func_malefics = []
    yk = YOGAKARAKAS.get(asc)
    if yk:
        func_benefics.append(yk.value)

    return NatalDossier(
        birth={
            "datetime_utc": str(d1.birth.datetime_utc),
            "place": d1.birth.place,
            "latitude": d1.birth.latitude,
            "longitude": d1.birth.longitude,
            "timezone": d1.birth.timezone,
        },
        ascendant={
            "sign": asc.name.title(),
            "degree": round(d1.ascendant_degree, 2),
        },
        planets=planets_facts,
        houses=houses_facts,
        yogas=[{"name": y.name, "planets": [p.value for p in y.planets_involved],
                "houses": y.houses_activated, "strength": y.strength, "reason": y.reason}
               for y in yogas],
        afflictions=afflictions,
        vargottama_planets=vargottama,
        atmakaraka=ak.value,
        amatyakaraka=amk.value,
        functional_benefics=func_benefics,
        functional_malefics=func_malefics,
        d9_summary=d9_summary,
    )
