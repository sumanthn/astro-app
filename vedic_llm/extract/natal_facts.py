"""Extract a NatalDossier from computed D1, D9, and D10 charts.

Converts the raw compute-layer output into a flat, LLM-friendly
fact structure containing every piece of information an astrologer
would reference when reading a natal chart.
"""

from datetime import datetime
from vedic_llm.models.chart import Chart, BirthData
from vedic_llm.models.enums import Planet, Sign, Dignity
from vedic_llm.models.dossier import NatalDossier, PlanetFacts, HouseFacts
from vedic_llm.compute.dignity import (
    SIGN_LORD,
    EXALTATION,
    NATURAL_FRIENDS,
    natural_dignity,
    functional_nature,
    houses_ruled_by,
)
from vedic_llm.models.chart import PlanetState
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
    """Parashari functional nature — delegates to compute.dignity."""
    return functional_nature(planet, asc_sign)


def _nakshatra_from_degree(lon: float):
    """Return (Nakshatra, pada) for a sidereal longitude — inline duplicate of
    chart._nakshatra_from_longitude to avoid importing a private helper."""
    from vedic_llm.models.enums import Nakshatra
    nak_span = 360.0 / 27.0
    pada_span = nak_span / 4.0
    nak_index = min(int(lon / nak_span), 26)
    offset = lon - nak_index * nak_span
    pada = min(int(offset / pada_span) + 1, 4)
    return Nakshatra(nak_index + 1), pada


def _house_from(asc_sign: Sign, planet_sign: Sign) -> int:
    """Whole-sign house number of *planet_sign* when *asc_sign* is the 1st house."""
    return ((planet_sign.value - asc_sign.value) % 12) + 1


def _alternate_lagna_view(chart: Chart, lagna_planet: Planet) -> dict:
    """Return per-planet houses when *lagna_planet*'s sign is treated as 1st house.
    Used for Chandra Lagna (Moon) and Surya Lagna (Sun) cross-checks."""
    ps = chart.planets.get(lagna_planet)
    if not ps:
        return {}
    lagna_sign = ps.sign
    planet_houses = {}
    occupants_by_house = {i: [] for i in range(1, 13)}
    for p, pstate in chart.planets.items():
        h = _house_from(lagna_sign, pstate.sign)
        planet_houses[p.value] = h
        occupants_by_house[h].append(p.value)
    # Which sign lands on each house and which planet lords it
    houses_map = {}
    for h in range(1, 13):
        sign_num = ((lagna_sign.value - 1 + h - 1) % 12) + 1
        s = Sign(sign_num)
        houses_map[h] = {
            "sign": s.name.title(),
            "lord": SIGN_LORD[s].value,
            "occupants": occupants_by_house[h],
        }
    return {
        "lagna_planet": lagna_planet.value,
        "lagna_sign": lagna_sign.name.title(),
        "planet_houses": planet_houses,
        "houses": houses_map,
    }


def _d9_full(d9: Chart, atmakaraka: Planet, d1: Chart) -> dict:
    """Rich D9 summary: asc, asc-lord placement, every planet's D9 state,
    a 12-house map, karakamsha, and vargottama planets."""
    populate_house_aspects(d9)
    asc = d9.ascendant_sign
    asc_lord = SIGN_LORD[asc]
    asc_lord_state = d9.planets.get(asc_lord)
    asc_nak, asc_pada = _nakshatra_from_degree(d9.ascendant_degree + (asc.value - 1) * 30)

    planets_d9 = {}
    for p, ps in d9.planets.items():
        planets_d9[p.value] = {
            "sign": ps.sign.name.title(),
            "house_from_d9_lagna": ps.house,
            "dignity": ps.dignity.value,
            "natural_dignity": natural_dignity(p, ps.sign, ps.degree_in_sign).value,
            "conjunctions": [op.value for op, ops in d9.planets.items()
                             if op != p and ops.house == ps.house],
            "aspects_cast_on_houses": aspects_cast_by(p, ps.house),
        }

    houses_d9 = {}
    for h_num, house in d9.houses.items():
        lord = house.lord
        lord_ps = d9.planets.get(lord)
        houses_d9[h_num] = {
            "sign": house.sign.name.title(),
            "lord": lord.value,
            "lord_sign": lord_ps.sign.name.title() if lord_ps else "",
            "lord_house": lord_ps.house if lord_ps else 0,
            "lord_dignity": lord_ps.dignity.value if lord_ps else "",
            "occupants": [p.value for p in house.occupants],
            "aspected_by": [p.value for p in house.aspected_by],
        }

    ak_d9 = d9.planets.get(atmakaraka)
    d1_lagna_lord = SIGN_LORD[d1.ascendant_sign]
    d1_lagna_lord_d9 = d9.planets.get(d1_lagna_lord)

    return {
        "ascendant": asc.name.title(),
        "ascendant_degree": round(d9.ascendant_degree, 2),
        "ascendant_nakshatra": asc_nak.name.replace("_", " ").title(),
        "ascendant_pada": asc_pada,
        "ascendant_lord": asc_lord.value,
        "ascendant_lord_in_d9": {
            "sign": asc_lord_state.sign.name.title() if asc_lord_state else "",
            "house": asc_lord_state.house if asc_lord_state else 0,
            "dignity": asc_lord_state.dignity.value if asc_lord_state else "",
        },
        "d1_lagna_lord_in_d9": {
            "planet": d1_lagna_lord.value,
            "sign": d1_lagna_lord_d9.sign.name.title() if d1_lagna_lord_d9 else "",
            "house_from_d9_lagna": d1_lagna_lord_d9.house if d1_lagna_lord_d9 else 0,
            "dignity": d1_lagna_lord_d9.dignity.value if d1_lagna_lord_d9 else "",
        },
        "karakamsha": {
            "planet": atmakaraka.value,
            "sign": ak_d9.sign.name.title() if ak_d9 else "",
            "house_from_d9_lagna": ak_d9.house if ak_d9 else 0,
            "dignity": ak_d9.dignity.value if ak_d9 else "",
        },
        "planets": planets_d9,
        "houses": houses_d9,
        "moon_in_d9_house": d9.planets[Planet.MOON].house if Planet.MOON in d9.planets else 0,
        "sun_in_d9_house": d9.planets[Planet.SUN].house if Planet.SUN in d9.planets else 0,
    }


def _natural_relation_to_sign_lord(planet: Planet, sign: Sign) -> str:
    """Return 'own' / 'friend' / 'neutral' / 'enemy' for planet in this sign."""
    lord = SIGN_LORD[sign]
    if planet == lord:
        return "own"
    if planet in (Planet.RAHU, Planet.KETU) or lord in (Planet.RAHU, Planet.KETU):
        return "neutral"
    info = NATURAL_FRIENDS.get(planet)
    if not info:
        return "neutral"
    if lord in info["friends"]:
        return "friend"
    if lord in info["enemies"]:
        return "enemy"
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
            natural_dignity=natural_dignity(planet, ps.sign, ps.degree_in_sign).value,
            sign_lord=SIGN_LORD[ps.sign].value,
            natural_relation_to_sign_lord=_natural_relation_to_sign_lord(planet, ps.sign),
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
            lord_natural_dignity=(
                natural_dignity(lord, lord_ps.sign, lord_ps.degree_in_sign).value
                if lord_ps else ""
            ),
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

    # Full D9 picture — asc, asc-lord, every planet, every house, karakamsha
    d9_summary = _d9_full(d9, ak, d1)

    # Functional natures — classical Parashari rules
    func_natures = {p.value: functional_nature(p, asc)
                    for p in [Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
                              Planet.JUPITER, Planet.VENUS, Planet.SATURN,
                              Planet.RAHU, Planet.KETU]}
    func_benefics = [p for p, n in func_natures.items() if n == "benefic"]
    func_malefics = [p for p, n in func_natures.items() if n == "malefic"]
    func_neutrals = [p for p, n in func_natures.items() if n in ("neutral", "maraka")]
    yogakarakas = [p for p, n in func_natures.items() if n == "yogakaraka"]

    # Ascendant nakshatra from the sidereal longitude
    asc_lon_absolute = (asc.value - 1) * 30 + d1.ascendant_degree
    asc_nak, asc_pada = _nakshatra_from_degree(asc_lon_absolute)
    nak_lord = asc_nak.lord
    nak_lord_ps = d1.planets.get(nak_lord)

    asc_dict = {
        "sign": asc.name.title(),
        "degree": round(d1.ascendant_degree, 2),
        "nakshatra": asc_nak.name.replace("_", " ").title(),
        "pada": asc_pada,
        "nakshatra_lord": nak_lord.value,
        "nakshatra_lord_sign": nak_lord_ps.sign.name.title() if nak_lord_ps else "",
        "nakshatra_lord_house": nak_lord_ps.house if nak_lord_ps else 0,
        "nakshatra_lord_dignity": nak_lord_ps.dignity.value if nak_lord_ps else "",
        "lagna_lord": SIGN_LORD[asc].value,
        "is_hemmed_by_malefics": papa_kartari(d1, 1),
        "is_hemmed_by_benefics": shubha_kartari(d1, 1),
    }

    return NatalDossier(
        birth={
            "datetime_utc": str(d1.birth.datetime_utc),
            "place": d1.birth.place,
            "latitude": d1.birth.latitude,
            "longitude": d1.birth.longitude,
            "timezone": d1.birth.timezone,
        },
        ascendant=asc_dict,
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
        functional_neutrals=func_neutrals,
        yogakarakas=yogakarakas,
        functional_natures=func_natures,
        d9_summary=d9_summary,
        chandra_lagna=_alternate_lagna_view(d1, Planet.MOON),
        surya_lagna=_alternate_lagna_view(d1, Planet.SUN),
    )
