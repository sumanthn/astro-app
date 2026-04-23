"""Transit (Gochara) computations."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from vedic_llm.models.enums import Planet, Sign
from vedic_llm.models.chart import Chart, PlanetState, BirthData
from vedic_llm.compute.ephemeris import julian_day, planet_longitude, ascendant
from vedic_llm.compute.chart import _sign_from_longitude, _degree_in_sign, _nakshatra_from_longitude


@dataclass
class TransitSnapshot:
    timestamp: datetime
    transit_planets: dict  # Planet -> dict with sign, degree, house_from_natal, retrograde
    natal_house_occupancy: dict  # house_number -> list of transit Planets in that natal house
    transit_over_natal: list  # list of (transit_planet, natal_planet, orb_degrees) for conjunctions within 5°
    sade_sati: dict  # phase info
    jupiter_from_moon: int  # house count from natal Moon
    rahu_ketu_axis: list  # natal houses on the axis


def snapshot(natal: Chart, at: datetime) -> TransitSnapshot:
    """Compute current transit positions overlaid on natal chart."""
    jd = julian_day(at)

    transit_planets = {}
    natal_house_occupancy = {i: [] for i in range(1, 13)}
    transit_over_natal = []

    natal_asc_sign = natal.ascendant_sign

    for planet in Planet:
        lon, speed, retro = planet_longitude(jd, planet)
        sign = _sign_from_longitude(lon)
        deg = _degree_in_sign(lon)

        # House from natal ascendant (whole sign)
        house = ((sign.value - natal_asc_sign.value) % 12) + 1

        transit_planets[planet] = {
            "sign": sign,
            "degree": deg,
            "longitude": lon,
            "house_from_natal": house,
            "retrograde": retro,
            "speed": speed,
        }

        natal_house_occupancy[house].append(planet)

        # Check conjunctions with natal planets (within 5°)
        for natal_planet, natal_state in natal.planets.items():
            orb = abs(lon - natal_state.longitude)
            if orb > 180:
                orb = 360 - orb
            if orb <= 5.0:
                transit_over_natal.append((planet, natal_planet, round(orb, 2)))

    # Sade Sati: Saturn in 12th, 1st, or 2nd from natal Moon sign
    sade_sati = _compute_sade_sati(natal, transit_planets)

    # Jupiter from Moon
    jupiter_from_moon = _jupiter_from_moon(natal, transit_planets)

    # Rahu-Ketu axis
    rahu_ketu_axis = _rahu_ketu_axis(natal, transit_planets)

    return TransitSnapshot(
        timestamp=at,
        transit_planets=transit_planets,
        natal_house_occupancy=natal_house_occupancy,
        transit_over_natal=transit_over_natal,
        sade_sati=sade_sati,
        jupiter_from_moon=jupiter_from_moon,
        rahu_ketu_axis=rahu_ketu_axis,
    )


def _compute_sade_sati(natal: Chart, transit_planets: dict) -> dict:
    """Sade Sati = Saturn transiting 12th, 1st, or 2nd from natal Moon sign."""
    moon_sign = natal.planets[Planet.MOON].sign
    saturn_sign = transit_planets[Planet.SATURN]["sign"]

    distance = ((saturn_sign.value - moon_sign.value) % 12)

    if distance == 11:  # 12th from Moon
        return {"active": True, "phase": "rising (12th from Moon)", "severity": "building"}
    elif distance == 0:  # same sign as Moon
        return {"active": True, "phase": "peak (over Moon)", "severity": "intense"}
    elif distance == 1:  # 2nd from Moon
        return {"active": True, "phase": "setting (2nd from Moon)", "severity": "waning"}
    else:
        return {"active": False, "phase": "none", "severity": "none"}


def _jupiter_from_moon(natal: Chart, transit_planets: dict) -> int:
    """House number of transit Jupiter counted from natal Moon sign."""
    moon_sign = natal.planets[Planet.MOON].sign
    jup_sign = transit_planets[Planet.JUPITER]["sign"]
    return ((jup_sign.value - moon_sign.value) % 12) + 1


def _rahu_ketu_axis(natal: Chart, transit_planets: dict) -> list[int]:
    """Which natal houses currently sit on the transiting Rahu-Ketu axis."""
    rahu_house = transit_planets[Planet.RAHU]["house_from_natal"]
    ketu_house = transit_planets[Planet.KETU]["house_from_natal"]
    return sorted(set([rahu_house, ketu_house]))
