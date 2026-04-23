"""Dignity computation for Vedic astrology — classical Parashari rules."""
from vedic_llm.models.enums import Planet, Sign, Dignity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vedic_llm.models.chart import Chart

# Exaltation sign and degree for each planet
EXALTATION = {
    Planet.SUN: (Sign.ARIES, 10.0),
    Planet.MOON: (Sign.TAURUS, 3.0),
    Planet.MARS: (Sign.CAPRICORN, 28.0),
    Planet.MERCURY: (Sign.VIRGO, 15.0),
    Planet.JUPITER: (Sign.CANCER, 5.0),
    Planet.VENUS: (Sign.PISCES, 27.0),
    Planet.SATURN: (Sign.LIBRA, 20.0),
}

# Debilitation = 7th sign from exaltation (180° opposite)
DEBILITATION = {
    Planet.SUN: Sign.LIBRA,
    Planet.MOON: Sign.SCORPIO,
    Planet.MARS: Sign.CANCER,
    Planet.MERCURY: Sign.PISCES,
    Planet.JUPITER: Sign.CAPRICORN,
    Planet.VENUS: Sign.VIRGO,
    Planet.SATURN: Sign.ARIES,
}

# Own signs
OWN_SIGNS = {
    Planet.SUN: [Sign.LEO],
    Planet.MOON: [Sign.CANCER],
    Planet.MARS: [Sign.ARIES, Sign.SCORPIO],
    Planet.MERCURY: [Sign.GEMINI, Sign.VIRGO],
    Planet.JUPITER: [Sign.SAGITTARIUS, Sign.PISCES],
    Planet.VENUS: [Sign.TAURUS, Sign.LIBRA],
    Planet.SATURN: [Sign.CAPRICORN, Sign.AQUARIUS],
}

# Moolatrikona signs and degree ranges
# Format: (sign, start_degree, end_degree)
MOOLATRIKONA = {
    Planet.SUN: (Sign.LEO, 0.0, 20.0),
    Planet.MOON: (Sign.TAURUS, 3.0, 30.0),
    Planet.MARS: (Sign.ARIES, 0.0, 12.0),
    Planet.MERCURY: (Sign.VIRGO, 15.0, 20.0),
    Planet.JUPITER: (Sign.SAGITTARIUS, 0.0, 10.0),
    Planet.VENUS: (Sign.LIBRA, 0.0, 15.0),
    Planet.SATURN: (Sign.AQUARIUS, 0.0, 20.0),
}

# Natural friendship table
# Each planet has natural friends, neutrals, and enemies
NATURAL_FRIENDS = {
    Planet.SUN: {
        "friends": [Planet.MOON, Planet.MARS, Planet.JUPITER],
        "neutrals": [Planet.MERCURY],
        "enemies": [Planet.VENUS, Planet.SATURN],
    },
    Planet.MOON: {
        "friends": [Planet.SUN, Planet.MERCURY],
        "neutrals": [Planet.MARS, Planet.JUPITER, Planet.VENUS, Planet.SATURN],
        "enemies": [],
    },
    Planet.MARS: {
        "friends": [Planet.SUN, Planet.MOON, Planet.JUPITER],
        "neutrals": [Planet.VENUS, Planet.SATURN],
        "enemies": [Planet.MERCURY],
    },
    Planet.MERCURY: {
        "friends": [Planet.SUN, Planet.VENUS],
        "neutrals": [Planet.MARS, Planet.JUPITER, Planet.SATURN],
        "enemies": [Planet.MOON],
    },
    Planet.JUPITER: {
        "friends": [Planet.SUN, Planet.MOON, Planet.MARS],
        "neutrals": [Planet.SATURN],
        "enemies": [Planet.MERCURY, Planet.VENUS],
    },
    Planet.VENUS: {
        "friends": [Planet.MERCURY, Planet.SATURN],
        "neutrals": [Planet.MARS, Planet.JUPITER],
        "enemies": [Planet.SUN, Planet.MOON],
    },
    Planet.SATURN: {
        "friends": [Planet.MERCURY, Planet.VENUS],
        "neutrals": [Planet.JUPITER],
        "enemies": [Planet.SUN, Planet.MOON, Planet.MARS],
    },
}

# Sign lordship (which planet rules which sign)
SIGN_LORD = {
    Sign.ARIES: Planet.MARS, Sign.TAURUS: Planet.VENUS,
    Sign.GEMINI: Planet.MERCURY, Sign.CANCER: Planet.MOON,
    Sign.LEO: Planet.SUN, Sign.VIRGO: Planet.MERCURY,
    Sign.LIBRA: Planet.VENUS, Sign.SCORPIO: Planet.MARS,
    Sign.SAGITTARIUS: Planet.JUPITER, Sign.CAPRICORN: Planet.SATURN,
    Sign.AQUARIUS: Planet.SATURN, Sign.PISCES: Planet.JUPITER,
}


def _natural_relationship(planet: Planet, sign_lord: Planet) -> str:
    """Returns 'friend', 'neutral', or 'enemy'."""
    if planet == sign_lord:
        return "own"
    # Rahu/Ketu don't have standard friendship tables
    if planet in (Planet.RAHU, Planet.KETU) or sign_lord in (Planet.RAHU, Planet.KETU):
        return "neutral"

    info = NATURAL_FRIENDS.get(planet)
    if not info:
        return "neutral"
    if sign_lord in info["friends"]:
        return "friend"
    if sign_lord in info["enemies"]:
        return "enemy"
    return "neutral"


def _temporary_relationship(planet: Planet, chart: 'Chart') -> dict[Planet, str]:
    """Temporary friendship based on house positions.
    Planets in 2,3,4,10,11,12 from a planet are temporary friends.
    Planets in 1,5,6,7,8,9 are temporary enemies.
    """
    result = {}
    if planet not in chart.planets:
        return result

    planet_house = chart.planets[planet].house

    for other_planet, other_state in chart.planets.items():
        if other_planet == planet:
            continue
        if other_planet in (Planet.RAHU, Planet.KETU):
            continue

        other_house = other_state.house
        # Distance in houses (1-indexed, counting from planet's house)
        distance = ((other_house - planet_house) % 12) + 1

        if distance in (2, 3, 4, 10, 11, 12):
            result[other_planet] = "friend"
        else:
            result[other_planet] = "enemy"

    return result


def _combined_relationship(natural: str, temporary: str) -> Dignity:
    """Combine natural and temporary friendship into final dignity."""
    combo = {
        ("friend", "friend"): Dignity.GREAT_FRIEND,
        ("friend", "enemy"): Dignity.NEUTRAL,
        ("neutral", "friend"): Dignity.FRIEND,
        ("neutral", "enemy"): Dignity.ENEMY,
        ("enemy", "friend"): Dignity.NEUTRAL,
        ("enemy", "enemy"): Dignity.GREAT_ENEMY,
    }
    return combo.get((natural, temporary), Dignity.NEUTRAL)


def compute_dignity(planet: Planet, sign: Sign, degree: float, chart: 'Chart') -> Dignity:
    """Compute the dignity of a planet in a given sign and degree.

    Priority order:
    1. Exaltation (within sign)
    2. Debilitation (within sign)
    3. Moolatrikona (within sign and degree range)
    4. Own sign
    5. Combined (natural + temporary) friendship
    """
    # Rahu/Ketu: use simplified rules
    # Rahu is exalted in Taurus/Gemini (texts vary), debilitated in Scorpio/Sagittarius
    # Ketu is exalted in Scorpio/Sagittarius, debilitated in Taurus/Gemini
    if planet == Planet.RAHU:
        if sign in (Sign.TAURUS, Sign.GEMINI):
            return Dignity.EXALTED
        if sign in (Sign.SCORPIO, Sign.SAGITTARIUS):
            return Dignity.DEBILITATED
        return Dignity.NEUTRAL

    if planet == Planet.KETU:
        if sign in (Sign.SCORPIO, Sign.SAGITTARIUS):
            return Dignity.EXALTED
        if sign in (Sign.TAURUS, Sign.GEMINI):
            return Dignity.DEBILITATED
        return Dignity.NEUTRAL

    # Check exaltation
    if planet in EXALTATION:
        ex_sign, _ = EXALTATION[planet]
        if sign == ex_sign:
            return Dignity.EXALTED

    # Check debilitation
    if planet in DEBILITATION and sign == DEBILITATION[planet]:
        return Dignity.DEBILITATED

    # Check moolatrikona
    if planet in MOOLATRIKONA:
        mt_sign, mt_start, mt_end = MOOLATRIKONA[planet]
        if sign == mt_sign and mt_start <= degree <= mt_end:
            return Dignity.MOOLATRIKONA

    # Check own sign
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]:
        return Dignity.OWN

    # Combined friendship
    sign_lord = SIGN_LORD[sign]
    natural = _natural_relationship(planet, sign_lord)

    temp_rels = _temporary_relationship(planet, chart)
    temporary = temp_rels.get(sign_lord, "neutral")

    return _combined_relationship(natural, temporary)
