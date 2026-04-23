# Vedic Chart Analysis

A Python application that produces deep Vedic (Jyotish) chart readings by combining:

- **Deterministic compute** — Skyfield / JPL DE440s ephemeris handles all astronomy (positions, dashas, transits, divisional charts). No math is ever delegated to the LLM.
- **LLM reasoning** — Claude interprets the computed facts through carefully structured prompts. No chart values are ever invented.

Three analysis surfaces are exposed:

1. **Quick analysis** — one Claude call, all 12 houses, scored and summarised.
2. **Deep house analysis** — per-house D1-primary reading with D9 cross-check, aspects, karakas, yogas, and Chandra/Surya Lagna views.
3. **Running report** — each house analysis accumulates into a single Markdown report you can publish or hand to a reader.

Both a **CLI** (`vedic …`) and a **web UI** (FastAPI) ship in the same package.

---

## Requirements

- Python 3.11+
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- `de440s.bsp` — NASA JPL ephemeris (ships in the repo, ~32 MB)

---

## Install

Using [`uv`](https://docs.astral.sh/uv/) (recommended):

```bash
git clone <repo-url> vedic_llm
cd vedic_llm
uv venv
uv pip install -e '.[web,dev]'
```

Or with `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[web,dev]'
```

Set the API key:

```bash
cp .env.example .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

Verify:

```bash
pytest -q                                # 15 tests pass
vedic --help
```

---

## CLI

```bash
# 1. Save a chart once — no API calls, just computation.
vedic save-chart \
  --date 1983-07-25 --time 00:50 \
  --lat 12.9716 --lon 77.5946 \
  --tz Asia/Kolkata --place "Bangalore, India" \
  --name ravi

# 2. Quick 12-house overview (single LLM call, ~15-20K tokens).
vedic quick-analysis \
  --chart-file reports/chart_ravi.json \
  --key-file ~/.secrets/anthropic-key

# 3. Deep per-house reading (D1-primary + D9 cross-check, ~30K tokens).
vedic analyze-house \
  --chart-file reports/chart_ravi.json \
  --house 1 --deep \
  --key-file ~/.secrets/anthropic-key

# 4. Check progress, render the accumulated Markdown report.
vedic status --slug ravi
vedic build-report --slug ravi
# → reports/report_ravi.md

# 5. Positions-only table (no API calls).
vedic chart --date 1983-07-25 --time 00:50 --lat 12.9716 --lon 77.5946
```

---

## Web UI

Start the server:

```bash
vedic serve --host 0.0.0.0 --port 8000
# or directly:
uvicorn vedic_llm.web.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` — enter DOB, time, and place (a place name is enough; the server geocodes it and auto-detects the timezone). The POST computes the chart, saves it, optionally runs the quick analysis, and redirects to `/chart/<slug>`.

JSON endpoints for integration:

```
GET /health                 — liveness + config check
GET /api/chart/{slug}       — full natal dossier JSON
GET /api/report/{slug}      — running report JSON (chart + quick + deep)
```

Configuration (env vars, read on startup):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required** for any LLM call |
| `VEDIC_REPORTS_DIR` | `./reports` | Where chart/report files are written |

---

## Deploy

The app is a plain Python package with a FastAPI ASGI entrypoint. Deploy it like any other Python web service — **no Docker required**.

### Simplest: single-host with systemd

1. Copy the repo to your server (e.g. `/opt/vedic_llm`).
2. Create a venv and install:
   ```bash
   cd /opt/vedic_llm
   python -m venv .venv
   .venv/bin/pip install -e '.[web]'
   ```
3. Drop your API key in `/opt/vedic_llm/.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   VEDIC_REPORTS_DIR=/var/lib/vedic_llm/reports
   ```
4. Create `/etc/systemd/system/vedic_llm.service`:
   ```ini
   [Unit]
   Description=Vedic Chart Analysis web UI
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/vedic_llm
   EnvironmentFile=/opt/vedic_llm/.env
   ExecStart=/opt/vedic_llm/.venv/bin/uvicorn vedic_llm.web.app:app --host 127.0.0.1 --port 8000
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```
5. Enable + start:
   ```bash
   systemctl enable --now vedic_llm
   ```
6. Front with nginx/Caddy for TLS (optional but recommended).

### Zero-config PaaS (Fly.io / Render / Railway)

Any platform that accepts a Python project with a `pyproject.toml` works:

- **Build**: `pip install -e '.[web]'`
- **Run**: `uvicorn vedic_llm.web.app:app --host 0.0.0.0 --port $PORT`
- **Secret**: `ANTHROPIC_API_KEY`
- **Persistent volume** (if you want reports to survive restarts): mount at `/data/reports` and set `VEDIC_REPORTS_DIR=/data/reports`.
- **Health check**: `GET /health`

### Running behind HTTPS

`uvicorn` handles TLS natively if you supply certs:

```bash
uvicorn vedic_llm.web.app:app \
  --host 0.0.0.0 --port 443 \
  --ssl-keyfile /etc/letsencrypt/live/.../privkey.pem \
  --ssl-certfile /etc/letsencrypt/live/.../fullchain.pem
```

Or put nginx/Caddy in front and proxy to port 8000.

---

## Project layout

```
vedic_llm/
├── compute/           Ephemeris, D1/D9/D10 builders, dignity, aspects, dasha, yogas
├── extract/           Dossier construction (compute → LLM-ready facts)
├── models/            Pydantic chart, planet, house, dossier models
├── prompts/           natal, dasha, transit, synthesis, lagna, house_deep, quick
├── llm/               Claude client + orchestrator
├── web/               FastAPI app, Jinja2 templates, service layer, geocoding
├── report.py          Accumulating report (JSON + Markdown rendering)
├── geocode.py         Place name → (lat, lon, timezone) via Nominatim + timezonefinder
└── cli.py             Typer-based CLI: chart, save-chart, analyze-house,
                       quick-analysis, dossier, status, build-report, serve
reports/               Generated chart files + analyses (gitignored)
tests/                 Fixture-backed chart accuracy tests
astro-PLAN.md          The original 10-phase execution plan
de440s.bsp             JPL ephemeris (gitignored)
```

---

## Notes on accuracy & interpretation

- All positions are sidereal using Lahiri ayanamsa. Whole-sign houses.
- The Rashi chart (D1) is the primary verdict; D9 acts as a supplementary cross-check. This weighting is enforced in the prompt templates.
- Each claim in the LLM output is required to carry a `[fact: <dossier_path>]` citation; unsupported claims are a prompt violation.
- **This is not medical, financial, or legal advice.** The prompts explicitly instruct neutral technical tone.
