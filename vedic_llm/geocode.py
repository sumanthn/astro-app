"""Place-name → (lat, lon, timezone) resolution.

Uses OpenStreetMap Nominatim (free, no API key, requires a User-Agent) plus
timezonefinder. Both libraries are pure-Python; timezonefinder ships a bundled
shape database, so no external calls are needed for timezone lookup.

Never raises on network failure — returns an error string in the result so the
web layer can display it and let the user fall back to manual entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


USER_AGENT = "vedic_llm/0.1 (https://github.com/anthropics/vedic_llm)"


@dataclass
class GeocodeResult:
    latitude: float
    longitude: float
    timezone: str
    display_name: str
    error: Optional[str] = None


def geocode(place: str, timeout: float = 10.0) -> GeocodeResult:
    """Resolve *place* to (lat, lon, tz). Returns a result with `error` set on failure."""
    if not place or not place.strip():
        return GeocodeResult(0.0, 0.0, "UTC", "", error="Place name is empty")

    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderServiceError, GeocoderTimedOut
    except ImportError:
        return GeocodeResult(0.0, 0.0, "UTC", "", error="geopy not installed")

    try:
        locator = Nominatim(user_agent=USER_AGENT, timeout=timeout)
        loc = locator.geocode(place, exactly_one=True)
    except (GeocoderServiceError, GeocoderTimedOut) as e:
        return GeocodeResult(0.0, 0.0, "UTC", "", error=f"Geocoder error: {e}")
    except Exception as e:  # network, dns, etc.
        return GeocodeResult(0.0, 0.0, "UTC", "", error=f"Geocode failed: {e}")

    if loc is None:
        return GeocodeResult(0.0, 0.0, "UTC", "", error=f"No match for '{place}'")

    tz = timezone_for(loc.latitude, loc.longitude)
    return GeocodeResult(
        latitude=float(loc.latitude),
        longitude=float(loc.longitude),
        timezone=tz,
        display_name=loc.address or place,
    )


def timezone_for(lat: float, lon: float) -> str:
    """Return IANA timezone name for (lat, lon). Falls back to 'UTC'."""
    try:
        from timezonefinder import TimezoneFinder
    except ImportError:
        return "UTC"
    try:
        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=lat, lng=lon)
        return tz or "UTC"
    except Exception:
        return "UTC"
