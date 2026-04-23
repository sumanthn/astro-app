"""Build Vedic astrology charts (D1, D9, D10) from birth data."""
from datetime import datetime, timezone
from dateutil import tz

from vedic_llm.models.enums import Planet, Sign, Nakshatra, Dignity
from vedic_llm.models.chart import BirthData, PlanetState, House, Chart
from vedic_llm.compute.ephemeris import julian_day, planet_longitude, ascendant
from vedic_llm.compute.dignity import SIGN_LORD, compute_dignity

# All nine Vedic planets in standard order.
_ALL_PLANETS = [
    Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
    Planet.JUPITER, Planet.VENUS, Planet.SATURN,
    Planet.RAHU, Planet.KETU,
]

# Planets that can be combust (not Sun, Moon, Rahu, Ketu).
_COMBUSTIBLE = {
    Planet.MARS, Planet.MERCURY, Planet.JUPITER,
    Planet.VENUS, Planet.SATURN,
}

# Navamsa starting-sign offsets by sign modality.
# Movable (chara): start from the sign itself -> offset 0
# Fixed (sthira): start from 9th sign from it -> offset 8
# Dual (dvisvabhava): start from 5th sign from it -> offset 4
_NAVAMSA_OFFSETS = {
    Sign.ARIES: 0, Sign.CANCER: 0, Sign.LIBRA: 0, Sign.CAPRICORN: 0,
    Sign.TAURUS: 8, Sign.LEO: 8, Sign.SCORPIO: 8, Sign.AQUARIUS: 8,
    Sign.GEMINI: 4, Sign.VIRGO: 4, Sign.SAGITTARIUS: 4, Sign.PISCES: 4,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sign_from_longitude(lon: float) -> Sign:
    """Convert a sidereal longitude (0-360) to its zodiac Sign.

    0-30 = Aries (1), 30-60 = Taurus (2), ..., 330-360 = Pisces (12).
    """
    index = int(lon // 30) % 12  # 0..11
    return Sign(index + 1)


def _degree_in_sign(lon: float) -> float:
    """Return the degree within the current sign (0-30)."""
    return lon % 30.0


def _nakshatra_from_longitude(lon: float) -> tuple[Nakshatra, int]:
    """Return (Nakshatra, pada) for a given sidereal longitude.

    Each nakshatra spans 13 20' = 13.333... degrees.
    Each pada spans 3 20' = 3.333... degrees (4 padas per nakshatra).
    """
    nak_span = 360.0 / 27.0  # 13.3333...
    pada_span = nak_span / 4.0  # 3.3333...

    nak_index = int(lon / nak_span)  # 0..26
    nak_index = min(nak_index, 26)  # clamp to valid range

    offset_in_nak = lon - nak_index * nak_span
    pada = int(offset_in_nak / pada_span) + 1  # 1..4
    pada = min(pada, 4)

    return Nakshatra(nak_index + 1), pada


def _is_combust(planet: Planet, planet_lon: float, sun_lon: float) -> bool:
    """Determine whether *planet* is combust (within 8 of the Sun).

    Combustion applies only to Mars, Mercury, Jupiter, Venus, and Saturn.
    Sun, Moon, Rahu, and Ketu are never considered combust.
    """
    if planet not in _COMBUSTIBLE:
        return False

    diff = abs(planet_lon - sun_lon)
    if diff > 180.0:
        diff = 360.0 - diff

    return diff <= 8.0


def _sign_number(sign: Sign) -> int:
    """Return the 1-based sign number (Aries=1 ... Pisces=12)."""
    return sign.value


def _sign_from_number(n: int) -> Sign:
    """Convert a 1-based sign number (possibly > 12) back to Sign enum."""
    return Sign(((n - 1) % 12) + 1)


def _house_of_planet(planet_sign: Sign, asc_sign: Sign) -> int:
    """Whole-sign house number: ascendant sign = house 1."""
    return ((planet_sign.value - asc_sign.value) % 12) + 1


def _build_houses(
    asc_sign: Sign,
    planet_states: dict[Planet, PlanetState],
) -> dict[int, House]:
    """Build 12 House objects using whole-sign houses."""
    houses: dict[int, House] = {}
    for h in range(1, 13):
        sign = _sign_from_number(asc_sign.value + h - 1)
        houses[h] = House(
            number=h,
            sign=sign,
            lord=SIGN_LORD[sign],
            occupants=[],
            aspected_by=[],
        )

    # Place planets into their houses.
    for planet, ps in planet_states.items():
        house_num = ps.house
        houses[house_num].occupants.append(planet)

    return houses


# ---------------------------------------------------------------------------
# D1 - Rasi chart
# ---------------------------------------------------------------------------

def build_d1_chart(birth: BirthData) -> Chart:
    """Construct the D1 (Rasi / natal) chart from birth data.

    Steps
    -----
    1. Convert the birth datetime to UTC.
    2. Compute Julian Day, ascendant, and planetary longitudes.
    3. Derive sign, nakshatra, pada, house, dignity, and combustion.
    4. Assemble whole-sign houses and return a ``Chart``.
    """
    # -- 1. Convert to UTC ------------------------------------------------
    local_tz = tz.gettz(birth.timezone)
    if birth.datetime_utc.tzinfo is None:
        # Treat the stored datetime as local time in the given timezone
        local_dt = birth.datetime_utc.replace(tzinfo=local_tz)
    else:
        local_dt = birth.datetime_utc.astimezone(local_tz)
    dt_utc = local_dt.astimezone(timezone.utc)

    # -- 2. Ephemeris queries ---------------------------------------------
    jd = julian_day(dt_utc)
    asc_lon = ascendant(jd, birth.latitude, birth.longitude)
    asc_sign = _sign_from_longitude(asc_lon)
    asc_degree = _degree_in_sign(asc_lon)

    # Pre-compute Sun longitude for combustion checks.
    sun_lon, _, _ = planet_longitude(jd, Planet.SUN)

    # -- 3. Build PlanetState for each planet -----------------------------
    # First pass: basic data (dignity needs Chart, so we'll recompute after).
    planet_states: dict[Planet, PlanetState] = {}
    for planet in _ALL_PLANETS:
        lon, speed, retro = planet_longitude(jd, planet)
        sign = _sign_from_longitude(lon)
        deg = _degree_in_sign(lon)
        nak, pada = _nakshatra_from_longitude(lon)
        house = _house_of_planet(sign, asc_sign)
        combust = _is_combust(planet, lon, sun_lon)

        planet_states[planet] = PlanetState(
            planet=planet,
            longitude=lon,
            sign=sign,
            degree_in_sign=round(deg, 4),
            house=house,
            nakshatra=nak,
            pada=pada,
            retrograde=retro,
            combust=combust,
            dignity=Dignity.NEUTRAL,  # placeholder
            speed=round(speed, 6),
        )

    # -- Build preliminary chart so compute_dignity can access houses -----
    houses = _build_houses(asc_sign, planet_states)
    chart = Chart(
        variant="D1",
        birth=birth,
        ascendant_sign=asc_sign,
        ascendant_degree=round(asc_degree, 4),
        planets=planet_states,
        houses=houses,
    )

    # -- 4. Compute dignities (needs chart for temporary friendships) -----
    for planet, ps in planet_states.items():
        dignity = compute_dignity(planet, ps.sign, ps.degree_in_sign, chart)
        ps.dignity = dignity

    # Reassign updated planets and rebuild houses (occupants unchanged).
    chart.planets = planet_states
    chart.houses = houses

    return chart


# ---------------------------------------------------------------------------
# Divisional chart helpers
# ---------------------------------------------------------------------------

def _divisional_sign(
    rasi_sign: Sign,
    degree_in_sign: float,
    division: int,
    starting_sign_offset: int,
) -> Sign:
    """Generic divisional-chart sign computation.

    Parameters
    ----------
    rasi_sign : Sign
        The D1 sign the planet occupies.
    degree_in_sign : float
        Degree within that sign (0-30).
    division : int
        How many equal parts to split the 30 sign into.
    starting_sign_offset : int
        0-based offset added to *rasi_sign* to get the first divisional
        sign for that part of the zodiac.

    Returns
    -------
    Sign
        The sign in the divisional chart.
    """
    part_size = 30.0 / division
    part_index = int(degree_in_sign / part_size)
    part_index = min(part_index, division - 1)  # clamp edge case at 30.0

    start_sign_num = rasi_sign.value + starting_sign_offset
    result_num = start_sign_num + part_index
    return _sign_from_number(result_num)


def _build_divisional_chart(
    d1: Chart,
    variant: str,
    division: int,
    offset_func,
) -> Chart:
    """Build a generic divisional chart from the D1 chart.

    Parameters
    ----------
    d1 : Chart
        The natal (D1) chart.
    variant : str
        Label such as "D9" or "D10".
    division : int
        Number of equal parts per sign.
    offset_func : callable
        ``(Sign) -> int`` returning the starting-sign offset for a given
        rasi sign.
    """
    # Divisional ascendant
    d_asc_sign = _divisional_sign(
        d1.ascendant_sign,
        _degree_in_sign(d1.ascendant_degree),
        division,
        offset_func(d1.ascendant_sign),
    )
    d_asc_degree = d1.ascendant_degree  # keep original degree for reference

    # Build planet states in the divisional chart
    planet_states: dict[Planet, PlanetState] = {}
    for planet, d1_ps in d1.planets.items():
        d_sign = _divisional_sign(
            d1_ps.sign,
            d1_ps.degree_in_sign,
            division,
            offset_func(d1_ps.sign),
        )
        d_deg = d1_ps.degree_in_sign  # keep original degree within sign
        nak, pada = _nakshatra_from_longitude(d1_ps.longitude)
        house = _house_of_planet(d_sign, d_asc_sign)

        planet_states[planet] = PlanetState(
            planet=planet,
            longitude=d1_ps.longitude,  # raw longitude unchanged
            sign=d_sign,
            degree_in_sign=round(d_deg, 4),
            house=house,
            nakshatra=nak,
            pada=pada,
            retrograde=d1_ps.retrograde,
            combust=d1_ps.combust,
            dignity=Dignity.NEUTRAL,  # placeholder
            speed=d1_ps.speed,
        )

    houses = _build_houses(d_asc_sign, planet_states)

    chart = Chart(
        variant=variant,
        birth=d1.birth,
        ascendant_sign=d_asc_sign,
        ascendant_degree=round(d_asc_degree, 4),
        planets=planet_states,
        houses=houses,
    )

    # Recompute dignity in divisional context
    for planet, ps in planet_states.items():
        dignity = compute_dignity(planet, ps.sign, ps.degree_in_sign, chart)
        ps.dignity = dignity

    chart.planets = planet_states
    chart.houses = houses

    return chart


# ---------------------------------------------------------------------------
# D9 - Navamsa
# ---------------------------------------------------------------------------

def _navamsa_offset(sign: Sign) -> int:
    """Return the starting-sign offset for Navamsa (D9).

    Movable signs  (Aries, Cancer, Libra, Capricorn)   -> 0  (from itself)
    Fixed signs    (Taurus, Leo, Scorpio, Aquarius)     -> 8  (9th from it)
    Dual signs     (Gemini, Virgo, Sagittarius, Pisces) -> 4  (5th from it)
    """
    return _NAVAMSA_OFFSETS[sign]


def build_d9_chart(d1: Chart) -> Chart:
    """Build the Navamsa (D9) divisional chart from the D1 chart.

    Each 30-degree sign is divided into 9 parts of 3 20' (3.3333...) each.
    The starting sign depends on the modality of the rasi sign.
    """
    return _build_divisional_chart(d1, "D9", 9, _navamsa_offset)


# ---------------------------------------------------------------------------
# D10 - Dasamsa
# ---------------------------------------------------------------------------

def _dasamsa_offset(sign: Sign) -> int:
    """Return the starting-sign offset for Dasamsa (D10).

    Odd signs  (Aries=1, Gemini=3, ...) -> 0  (from the sign itself)
    Even signs (Taurus=2, Cancer=4, ...) -> 8  (9th from it)
    """
    if sign.value % 2 == 1:
        return 0
    return 8


def build_d10_chart(d1: Chart) -> Chart:
    """Build the Dasamsa (D10) divisional chart from the D1 chart.

    Each 30-degree sign is divided into 10 parts of 3 degrees each.
    Odd signs count from the sign itself; even signs from the 9th sign.
    """
    return _build_divisional_chart(d1, "D10", 10, _dasamsa_offset)
