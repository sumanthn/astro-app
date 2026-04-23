"""Pure-Python service layer used by the web app — no FastAPI, no HTTP here.

Keeping the compute + analysis glue separate from the transport makes it
testable and lets the same code back a CLI, a web form, or an async worker.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dateutil import tz as dtz

from vedic_llm.models.chart import BirthData
from vedic_llm.models.dossier import NatalDossier
from vedic_llm.compute.chart import build_d1_chart, build_d9_chart, build_d10_chart
from vedic_llm.compute.aspects import populate_house_aspects
from vedic_llm.extract.natal_facts import extract_natal_dossier
from vedic_llm.geocode import geocode, timezone_for
from vedic_llm.prompts.quick import build_quick_prompt
from vedic_llm.llm.client import ClaudeClient
from vedic_llm.report import (
    load_report,
    save_report,
    set_quick_analysis,
    _chart_summary,
)


SLUG_RE = re.compile(r"[^a-z0-9_\-]+")


def make_slug(name: str | None, date: str) -> str:
    """Create a filesystem- and URL-safe slug."""
    raw = (name or date or uuid.uuid4().hex[:8]).lower().replace(" ", "-")
    return SLUG_RE.sub("", raw) or uuid.uuid4().hex[:8]


@dataclass
class ResolvedBirth:
    """Normalised, validated birth input ready for chart construction."""
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    latitude: float
    longitude: float
    timezone: str
    place: str
    display_name: str
    warnings: list[str] = field(default_factory=list)


def resolve_birth_input(
    date: str,
    time: str,
    place: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[str] = None,
) -> ResolvedBirth:
    """Validate raw user inputs and fill in missing fields via geocoding."""
    if not date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("Birth date must be YYYY-MM-DD")
    if not time or not re.fullmatch(r"\d{2}:\d{2}", time):
        raise ValueError("Birth time must be HH:MM (24hr)")

    # Validate date is parseable
    try:
        datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError as e:
        raise ValueError(f"Invalid date/time: {e}") from e

    warnings: list[str] = []
    display_name = place

    # If lat/lon not provided (or 0,0 default), try geocoding
    if latitude is None or longitude is None or (latitude == 0.0 and longitude == 0.0):
        if not place:
            raise ValueError("Provide either (latitude, longitude) or a place name")
        gc = geocode(place)
        if gc.error:
            raise ValueError(f"Could not geocode place '{place}': {gc.error}. "
                             "Fill in latitude/longitude manually.")
        latitude = gc.latitude
        longitude = gc.longitude
        display_name = gc.display_name or place
        if not timezone:
            timezone = gc.timezone

    # Validate lat/lon ranges
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("Longitude must be between -180 and 180")

    if not timezone:
        timezone = timezone_for(latitude, longitude)
        warnings.append(f"Timezone auto-detected from coordinates: {timezone}")

    # Verify timezone is loadable
    if dtz.gettz(timezone) is None:
        raise ValueError(f"Unknown timezone: {timezone}")

    return ResolvedBirth(
        date=date,
        time=time,
        latitude=float(latitude),
        longitude=float(longitude),
        timezone=timezone,
        place=place,
        display_name=display_name or place,
        warnings=warnings,
    )


def compute_chart(birth_input: ResolvedBirth) -> NatalDossier:
    """Compute D1/D9/D10 and return the full natal dossier."""
    local_tz = dtz.gettz(birth_input.timezone)
    dt_local = datetime.strptime(
        f"{birth_input.date} {birth_input.time}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=local_tz)
    dt_utc = dt_local.astimezone(dtz.UTC)

    birth = BirthData(
        datetime_utc=dt_utc,
        latitude=birth_input.latitude,
        longitude=birth_input.longitude,
        timezone=birth_input.timezone,
        place=birth_input.display_name or birth_input.place
              or f"{birth_input.latitude},{birth_input.longitude}",
    )

    d1 = build_d1_chart(birth)
    populate_house_aspects(d1)
    d9 = build_d9_chart(d1)
    d10 = build_d10_chart(d1)
    for p in d1.planets:
        if p in d9.planets and d1.planets[p].sign == d9.planets[p].sign:
            d1.planets[p].vargottama = True

    return extract_natal_dossier(d1, d9, d10)


def save_chart(slug: str, dossier: NatalDossier,
               reports_dir: Path | str = "reports") -> Path:
    path = Path(reports_dir) / f"chart_{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dossier.model_dump_json(indent=2))

    # Also initialise the running report with birth + chart summary
    report = load_report(slug, reports_dir)
    report["slug"] = slug
    report["birth"] = dossier.birth
    report["chart_summary"] = _chart_summary(dossier)
    save_report(report, reports_dir)
    return path


def run_quick_analysis(
    slug: str,
    dossier: NatalDossier,
    model: Optional[str] = None,
    max_tokens: int = 16000,
    reports_dir: Path | str = "reports",
) -> dict:
    """Run the single-call 12-house quick analysis and persist it."""
    client = ClaudeClient(model=model) if model else ClaudeClient()
    sys_prompt, user_prompt = build_quick_prompt(dossier)
    result = client.analyze_json(sys_prompt, user_prompt, max_tokens=max_tokens)
    set_quick_analysis(
        slug=slug,
        dossier=dossier,
        quick_result=result if isinstance(result, dict) else {"raw": result},
        token_usage=client.token_usage(),
        reports_dir=reports_dir,
    )
    return {
        "result": result,
        "token_usage": client.token_usage(),
    }
