"""FastAPI app — chart computation + quick 12-house analysis over HTTP.

Run locally:
    vedic serve --host 127.0.0.1 --port 8000
or directly:
    uvicorn vedic_llm.web.app:app --host 0.0.0.0 --port 8000

Configuration:
    ANTHROPIC_API_KEY   (required)
    VEDIC_REPORTS_DIR   (default: ./reports)
"""
from __future__ import annotations

import json
import logging
import os
import traceback
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from vedic_llm.models.dossier import NatalDossier
from vedic_llm.report import load_report
from vedic_llm.web.service import (
    ResolvedBirth,
    compute_chart,
    make_slug,
    resolve_birth_input,
    run_quick_analysis,
    save_chart,
)

load_dotenv()

log = logging.getLogger("vedic_llm.web")
logging.basicConfig(level=logging.INFO)

REPORTS_DIR = Path(os.environ.get("VEDIC_REPORTS_DIR", "reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="Vedic Chart Analysis", version="0.1.0")


# ---------------------------------------------------------------------------
# Health + home form
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "anthropic_api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "reports_dir": str(REPORTS_DIR),
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "form.html", {"error": None})


# ---------------------------------------------------------------------------
# Analyse flow: POST form → compute → quick analysis → redirect to /chart/{slug}
# ---------------------------------------------------------------------------

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    date: str = Form(..., description="Birth date YYYY-MM-DD"),
    time: str = Form(..., description="Birth time HH:MM (24hr)"),
    place: str = Form("", description="Place name (used for geocoding if lat/lon empty)"),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    timezone: Optional[str] = Form(None),
    name: Optional[str] = Form(None, description="Short name for this chart (used in URL)"),
    run_analysis: Optional[str] = Form(None),  # checkbox
):
    lat = float(latitude) if latitude not in (None, "") else None
    lon = float(longitude) if longitude not in (None, "") else None

    try:
        resolved = resolve_birth_input(
            date=date,
            time=time,
            place=place,
            latitude=lat,
            longitude=lon,
            timezone=timezone or None,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "form.html",
            {
                "error": str(e),
                "form_values": {
                    "date": date, "time": time, "place": place,
                    "latitude": latitude, "longitude": longitude,
                    "timezone": timezone, "name": name,
                },
            },
            status_code=400,
        )

    slug = make_slug(name, date)

    try:
        dossier = compute_chart(resolved)
    except Exception as e:
        log.exception("chart computation failed")
        return templates.TemplateResponse(
            request,
            "form.html",
            {"error": f"Chart computation failed: {e}"},
            status_code=500,
        )

    save_chart(slug, dossier, REPORTS_DIR)

    quick_error = None
    if run_analysis:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            quick_error = ("ANTHROPIC_API_KEY is not configured on the server, so the "
                           "LLM analysis was skipped. The chart has been computed and saved.")
        else:
            try:
                run_quick_analysis(slug=slug, dossier=dossier, reports_dir=REPORTS_DIR)
            except Exception as e:
                log.exception("quick analysis failed")
                quick_error = f"Chart saved; quick analysis failed: {e}"

    target = f"/chart/{slug}"
    if quick_error:
        target += f"?notice={_url_encode(quick_error)}"
    return RedirectResponse(url=target, status_code=303)


def _url_encode(s: str) -> str:
    from urllib.parse import quote
    return quote(s)


# ---------------------------------------------------------------------------
# Saved chart view
# ---------------------------------------------------------------------------

# JSON endpoints declared FIRST so they win over the HTML page's {slug} path param.
@app.get("/api/chart/{slug}", response_class=JSONResponse)
async def chart_json(slug: str):
    chart_file = REPORTS_DIR / f"chart_{slug}.json"
    if not chart_file.exists():
        raise HTTPException(404, f"No saved chart for '{slug}'")
    return JSONResponse(content=json.loads(chart_file.read_text()))


@app.get("/api/report/{slug}", response_class=JSONResponse)
async def report_json(slug: str):
    report = load_report(slug, REPORTS_DIR)
    if not report.get("birth"):
        raise HTTPException(404, f"No report for '{slug}'")
    return JSONResponse(content=report)


@app.get("/chart/{slug}", response_class=HTMLResponse)
async def chart_page(request: Request, slug: str, notice: Optional[str] = None):
    chart_file = REPORTS_DIR / f"chart_{slug}.json"
    if not chart_file.exists():
        raise HTTPException(404, f"No saved chart for '{slug}'")

    dossier = NatalDossier.model_validate_json(chart_file.read_text())
    report = load_report(slug, REPORTS_DIR)
    quick = report.get("quick_analysis") or {}

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "slug": slug,
            "notice": notice,
            "birth": dossier.birth,
            "ascendant": dossier.ascendant,
            "planets": dossier.planets,
            "houses": dossier.houses,
            "atmakaraka": dossier.atmakaraka,
            "amatyakaraka": dossier.amatyakaraka,
            "vargottama": dossier.vargottama_planets,
            "functional_benefics": dossier.functional_benefics,
            "functional_malefics": dossier.functional_malefics,
            "yogas": dossier.yogas,
            "d9_ascendant": dossier.d9_summary.get("ascendant"),
            "d9_ascendant_nakshatra": dossier.d9_summary.get("ascendant_nakshatra"),
            "quick": quick.get("result") or {},
            "quick_tokens": quick.get("token_usage") or {},
            "has_quick": bool(quick),
        },
    )
