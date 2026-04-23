"""Smoke test — verify ephemeris works."""
from datetime import datetime, timezone
from vedic_llm.compute.ephemeris import julian_day, ayanamsa, planet_longitude
from vedic_llm.models.enums import Planet


def test_sun_position():
    """Sun on 2000-01-01 sidereal should be around 256° (280° tropical - 24° ayanamsa)."""
    dt = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    jd = julian_day(dt)
    lon, speed, retro = planet_longitude(jd, Planet.SUN, sidereal=True)
    assert 250 < lon < 265, f"Sun sidereal longitude {lon} not in expected range"
    assert not retro, "Sun should not be retrograde"


def test_ayanamsa():
    """Lahiri ayanamsa around 2000 should be ~23.85°."""
    dt = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    jd = julian_day(dt)
    aya = ayanamsa(jd)
    assert 23.5 < aya < 24.2, f"Ayanamsa {aya} not in expected range"


def test_moon_speed():
    """Moon should move ~12-15° per day."""
    dt = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    jd = julian_day(dt)
    lon, speed, retro = planet_longitude(jd, Planet.MOON, sidereal=True)
    assert 10 < abs(speed) < 16, f"Moon speed {speed} not in expected range"
