"""Ephemeris wrapper using Skyfield (pure Python, NASA JPL data) for Vedic astrology."""
import math
from datetime import datetime, timezone, timedelta
from skyfield.api import load

from vedic_llm.models.enums import Planet

# Load timescale and ephemeris (cached after first download)
_ts = load.timescale()
_eph = load('de440s.bsp')

# Skyfield body references
_BODY_MAP = {
    Planet.SUN: 'sun',
    Planet.MOON: 'moon',
    Planet.MARS: 'mars barycenter',
    Planet.MERCURY: 'mercury',
    Planet.JUPITER: 'jupiter barycenter',
    Planet.VENUS: 'venus',
    Planet.SATURN: 'saturn barycenter',
}

# Lahiri ayanamsa reference: 23°51'11" on Jan 1, 2000 (J2000.0)
# Precession rate: ~50.29" per year
_LAHIRI_J2000 = 23.0 + 51.0/60.0 + 11.0/3600.0  # 23.8531°
_PRECESSION_RATE = 50.29 / 3600.0  # degrees per year
_J2000_JD = 2451545.0


def _to_skyfield_time(dt_utc: datetime):
    """Convert datetime to Skyfield Time object."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return _ts.from_datetime(dt_utc)


def julian_day(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day."""
    t = _to_skyfield_time(dt_utc)
    return t.tt  # Terrestrial Time as JD


def ayanamsa(jd: float, system: str = "lahiri") -> float:
    """Get ayanamsa value for given Julian Day.

    Uses linear approximation from Lahiri epoch.
    """
    if system != "lahiri":
        # For simplicity, only Lahiri is precisely implemented
        pass
    years_from_j2000 = (jd - _J2000_JD) / 365.25
    return _LAHIRI_J2000 + _PRECESSION_RATE * years_from_j2000


def _tropical_longitude(dt_utc: datetime, body_name: str) -> tuple[float, float]:
    """Compute tropical ecliptic longitude and speed for a body.

    Returns (longitude_degrees, speed_degrees_per_day).
    """
    t = _to_skyfield_time(dt_utc)
    earth = _eph['earth']
    body = _eph[body_name]

    # Get ecliptic coordinates as seen from Earth
    astrometric = earth.at(t).observe(body)
    lat, lon, dist = astrometric.ecliptic_latlon()

    # Compute speed by finite difference (1 hour interval)
    dt2 = dt_utc + timedelta(hours=1)
    t2 = _to_skyfield_time(dt2)
    astrometric2 = earth.at(t2).observe(body)
    lat2, lon2, dist2 = astrometric2.ecliptic_latlon()

    lon_deg = lon.degrees
    lon2_deg = lon2.degrees

    # Handle wraparound at 360°
    diff = lon2_deg - lon_deg
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360

    speed = diff * 24.0  # degrees per day

    return lon_deg % 360.0, speed


def _compute_mean_node(dt_utc: datetime) -> tuple[float, float]:
    """Compute Mean Lunar Node (Rahu) position.

    Uses the standard formula for mean ascending node.
    The node regresses ~19.355° per year.
    """
    t = _to_skyfield_time(dt_utc)
    # Julian centuries from J2000.0
    T = (t.tt - 2451545.0) / 36525.0

    # Mean longitude of ascending node (degrees) — Meeus formula
    omega = (125.04452
             - 1934.136261 * T
             + 0.0020708 * T * T
             + T * T * T / 450000.0)

    # Normalize to 0-360
    omega = omega % 360.0
    if omega < 0:
        omega += 360.0

    # Speed: approximately -0.05299° per day (retrograde)
    speed = -19.355 / 365.25  # degrees per day

    return omega, speed


def planet_longitude(jd: float, planet: Planet, sidereal: bool = True) -> tuple[float, float, bool]:
    """Return (longitude_deg, speed_deg_per_day, is_retrograde).

    If sidereal=True, subtracts Lahiri ayanamsa for sidereal longitude.
    """
    # Convert JD back to datetime for Skyfield
    # JD (TT) to approximate UTC datetime
    t = _ts.tt_jd(jd)
    dt_utc = t.utc_datetime()

    if planet == Planet.KETU:
        lon, speed, retro = planet_longitude(jd, Planet.RAHU, sidereal)
        ketu_lon = (lon + 180.0) % 360.0
        return ketu_lon, -speed, not retro

    if planet == Planet.RAHU:
        trop_lon, speed = _compute_mean_node(dt_utc)
        if sidereal:
            aya = ayanamsa(jd)
            trop_lon = (trop_lon - aya) % 360.0
        # Rahu is naturally retrograde; only rare direct motion is "retrograde" in Vedic terms
        retro = speed > 0
        return trop_lon, speed, retro

    body_name = _BODY_MAP[planet]
    trop_lon, speed = _tropical_longitude(dt_utc, body_name)

    if sidereal:
        aya = ayanamsa(jd)
        trop_lon = (trop_lon - aya) % 360.0

    retro = speed < 0
    return trop_lon, speed, retro


def ascendant(jd: float, lat: float, lon: float) -> float:
    """Compute sidereal ascendant degree.

    Uses the standard formula for the ascendant based on
    local sidereal time and obliquity of the ecliptic.
    """
    t = _ts.tt_jd(jd)
    dt_utc = t.utc_datetime()

    # Get Greenwich Sidereal Time
    gst = t.gast  # Greenwich Apparent Sidereal Time in hours

    # Local Sidereal Time
    lst_hours = (gst + lon / 15.0) % 24.0
    lst_deg = lst_hours * 15.0  # convert to degrees

    # Obliquity of ecliptic (approximate, J2000 epoch)
    T = (jd - 2451545.0) / 36525.0
    epsilon = 23.4392911 - 0.0130042 * T  # degrees
    epsilon_rad = math.radians(epsilon)
    lat_rad = math.radians(lat)
    lst_rad = math.radians(lst_deg)

    # Ascendant formula (Meeus, Astronomical Algorithms)
    # ASC = atan2(cos(RAMC), -(sin(RAMC)*cos(eps) + tan(lat)*sin(eps)))
    y = math.cos(lst_rad)
    x = -(math.sin(lst_rad) * math.cos(epsilon_rad) + math.tan(lat_rad) * math.sin(epsilon_rad))

    asc_tropical = math.degrees(math.atan2(y, x)) % 360.0

    # Subtract ayanamsa for sidereal
    aya = ayanamsa(jd)
    asc_sidereal = (asc_tropical - aya) % 360.0

    return asc_sidereal
