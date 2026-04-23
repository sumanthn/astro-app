# Vedic Chart Analysis App — Claude Code Execution Plan

> **How to use this file:** Drop this into your repo root as `PLAN.md`. Point Claude Code at it and say "execute Phase 1" (then Phase 2, etc.). Each phase is self-contained with tasks, code scaffolds, acceptance criteria, and verification steps.

---

## Project Overview

Build a Python application that analyzes Vedic astrology charts by combining:
- **Deterministic compute** (Python does all math: positions, dignities, dashas, transits)
- **LLM reasoning** (Claude interprets the computed facts via carefully structured prompts)

**Three analysis layers:**
1. **Natal** — Rashi (D1) + Navamsa (D9) = baseline potential
2. **Dasha-Bhukti** — Vimshottari MD/AD/PD = activation window
3. **Gochara** — current transits = triggers

**Core principle:** Python never interprets. LLM never computes. Prompts are the product.

---

## Tech Stack

- Python 3.11+
- `pyswisseph` — Swiss Ephemeris (all astronomical compute)
- `pydantic` v2 — typed domain models
- `anthropic` — Claude API client
- `pytest` — testing with known-chart fixtures
- `typer` — CLI
- `rich` — pretty terminal output

---

## Repository Structure (target)

```
vedic_llm/
├── PLAN.md                          # this file
├── pyproject.toml
├── README.md
├── .env.example                     # ANTHROPIC_API_KEY
├── vedic_llm/
│   ├── __init__.py
│   ├── compute/
│   │   ├── ephemeris.py             # pyswisseph wrapper
│   │   ├── chart.py                 # D1, D9, D10 builders
│   │   ├── dignity.py               # exaltation, own, friend/enemy tables
│   │   ├── aspects.py               # graha drishti
│   │   ├── dasha.py                 # Vimshottari MD/AD/PD
│   │   ├── transit.py               # current positions over natal
│   │   └── yogas.py                 # Raja, Dhana, Neecha Bhanga detectors
│   ├── models/
│   │   ├── enums.py                 # Planet, Sign, Nakshatra, Dignity
│   │   ├── chart.py                 # Chart, PlanetState, House
│   │   └── dossier.py               # FactDossier (LLM-ready context)
│   ├── extract/
│   │   ├── natal_facts.py
│   │   ├── dasha_facts.py
│   │   └── transit_facts.py
│   ├── prompts/
│   │   ├── natal.py
│   │   ├── dasha.py
│   │   ├── transit.py
│   │   ├── synthesis.py
│   │   └── topics/
│   │       ├── career.py
│   │       ├── wealth.py
│   │       ├── health.py
│   │       └── relationships.py
│   ├── llm/
│   │   ├── client.py
│   │   └── orchestrator.py
│   └── cli.py
├── tests/
│   ├── fixtures/                    # known charts (YAML)
│   └── test_*.py
└── reports/                         # generated analysis outputs
```

---

# PHASE 0 — Project Bootstrap

**Goal:** Repo setup, dependencies, smoke test.

## Tasks

1. Create `pyproject.toml` with dependencies:
   ```toml
   [project]
   name = "vedic_llm"
   version = "0.1.0"
   requires-python = ">=3.11"
   dependencies = [
       "pyswisseph>=2.10",
       "pydantic>=2.5",
       "anthropic>=0.40",
       "typer>=0.12",
       "rich>=13.7",
       "python-dateutil>=2.8",
       "pytz>=2024.1",
       "pyyaml>=6.0",
   ]

   [project.optional-dependencies]
   dev = ["pytest>=8.0", "pytest-cov", "ruff", "mypy"]

   [project.scripts]
   vedic = "vedic_llm.cli:app"
   ```

2. Create `.env.example` with `ANTHROPIC_API_KEY=` and add `.env` to `.gitignore`.

3. Create `README.md` with install/run instructions.

4. Create package skeleton: all folders from the structure above with empty `__init__.py` files.

5. Write a smoke test `tests/test_smoke.py` that imports `swisseph` and prints the Sun's position for `2000-01-01 00:00 UTC`.

## Acceptance Criteria

- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `pytest tests/test_smoke.py` prints a valid Sun longitude (~280°)
- [ ] `vedic --help` shows a CLI stub

---

# PHASE 1 — Compute Layer: Ephemeris + D1 Chart

**Goal:** Given birth details, produce a complete, verified Rashi chart with all 9 grahas.

## Tasks

### 1.1 `vedic_llm/models/enums.py`

Define:
- `Planet` enum (SUN, MOON, MARS, MERCURY, JUPITER, VENUS, SATURN, RAHU, KETU)
- `Sign` enum (ARIES..PISCES with numeric values 1-12)
- `Nakshatra` enum (27 nakshatras with their lords)
- `Dignity` enum (EXALTED, MOOLATRIKONA, OWN, GREAT_FRIEND, FRIEND, NEUTRAL, ENEMY, GREAT_ENEMY, DEBILITATED)
- `HouseType` enum (KENDRA, TRIKONA, DUSTHANA, UPACHAYA, MARAKA, NEUTRAL)

### 1.2 `vedic_llm/compute/ephemeris.py`

Wrap Swiss Ephemeris. Functions:

```python
def julian_day(dt_utc: datetime) -> float: ...
def ayanamsa(jd: float, system: str = "lahiri") -> float: ...
def planet_longitude(jd: float, planet: Planet, sidereal: bool = True) -> tuple[float, float, bool]:
    """Returns (longitude_deg, speed_deg_per_day, retrograde)."""
def ascendant(jd: float, lat: float, lon: float) -> float: ...
```

Rahu/Ketu: use MEAN node by default, TRUE node as option. Ketu = Rahu + 180°.

### 1.3 `vedic_llm/compute/dignity.py`

Static tables:
- Exaltation degrees: Sun 10° Aries, Moon 3° Taurus, Mars 28° Capricorn, Mercury 15° Virgo, Jupiter 5° Cancer, Venus 27° Pisces, Saturn 20° Libra
- Debilitation: 180° opposite exaltation
- Own signs: Sun=Leo; Moon=Cancer; Mars=Aries,Scorpio; Mercury=Gemini,Virgo; Jupiter=Sagittarius,Pisces; Venus=Taurus,Libra; Saturn=Capricorn,Aquarius
- Moolatrikona degrees (per classical texts)
- Natural friendship table (3x3: friend/neutral/enemy for each pair)
- Temporary friendship rule (planets in 2,3,4,10,11,12 from each other)
- Combined friendship = natural + temporary

Function:
```python
def compute_dignity(planet: Planet, sign: Sign, degree: float, chart: 'Chart') -> Dignity: ...
```

### 1.4 `vedic_llm/compute/chart.py`

```python
def build_d1_chart(birth: BirthData) -> Chart:
    """Whole-sign houses. Ascendant sign = 1st house."""
```

Compute for each planet: sign, degree in sign, house (whole sign), nakshatra, pada, retrograde, combust (within 8° of Sun, excluding Sun itself and Moon), dignity.

### 1.5 `vedic_llm/models/chart.py`

Pydantic models:

```python
class BirthData(BaseModel):
    datetime_utc: datetime
    latitude: float
    longitude: float
    timezone: str
    place: str

class PlanetState(BaseModel):
    planet: Planet
    longitude: float
    sign: Sign
    degree_in_sign: float
    house: int
    nakshatra: Nakshatra
    pada: int
    retrograde: bool
    combust: bool
    dignity: Dignity
    speed: float

class House(BaseModel):
    number: int
    sign: Sign
    lord: Planet
    occupants: list[Planet]
    aspected_by: list[Planet]

class Chart(BaseModel):
    variant: str  # "D1", "D9", "D10"
    birth: BirthData
    ascendant_sign: Sign
    ascendant_degree: float
    planets: dict[Planet, PlanetState]
    houses: dict[int, House]

    def lord_of(self, house: int) -> Planet: ...
    def planets_in_house(self, house: int) -> list[Planet]: ...
    def planets_in_sign(self, sign: Sign) -> list[Planet]: ...
```

### 1.6 Test fixtures

Create `tests/fixtures/charts.yaml` with 2-3 verified public charts (pick from Astro-Databank or published Jyotish texts with exact birth data). Include expected ascendant sign, Sun sign, Moon sign, and Moon nakshatra for each.

Example:
```yaml
- name: "Mahatma Gandhi"
  datetime_local: "1869-10-02 07:12:00"
  timezone: "Asia/Kolkata"
  latitude: 21.6417
  longitude: 69.6293
  place: "Porbandar, India"
  expected:
    ascendant_sign: "Libra"
    sun_sign: "Virgo"
    moon_sign: "Scorpio"
    moon_nakshatra: "Anuradha"
```

### 1.7 Tests

Write `tests/test_chart.py` that builds D1 for each fixture and asserts expected positions within 1° tolerance.

## Acceptance Criteria

- [ ] All fixture charts match expected positions
- [ ] `Chart` model serializes to JSON cleanly
- [ ] Dignity computation matches classical texts for all 7 planets

---

# PHASE 2 — Divisional Charts (D9 Navamsa, D10 Dasamsa)

**Goal:** Build Navamsa (critical for natal verdict) and Dasamsa (critical for career).

## Tasks

### 2.1 `vedic_llm/compute/chart.py` — extend

D9 construction rule: each 30° sign is divided into 9 parts of 3°20' each.
- Movable signs (Aries, Cancer, Libra, Capricorn): navamsa starts from the sign itself
- Fixed signs (Taurus, Leo, Scorpio, Aquarius): navamsa starts from the 9th sign from it
- Dual signs (Gemini, Virgo, Sagittarius, Pisces): navamsa starts from the 5th sign from it

```python
def build_d9_chart(d1: Chart) -> Chart: ...
def build_d10_chart(d1: Chart) -> Chart: ...
```

D10 rule:
- Odd signs: dasamsa counted from the sign itself
- Even signs: dasamsa counted from the 9th sign from it
Each sign split into 10 parts of 3° each.

### 2.2 Vargottama detection

A planet is vargottama if it occupies the same sign in D1 and D9. Add this flag to `PlanetState` (extend model).

### 2.3 Tests

For each fixture chart, verify D9 ascendant and D9 positions of Moon against reference computations (cross-check with JHora or a published ephemeris).

## Acceptance Criteria

- [ ] D9 positions match reference within 1 sign for all fixtures
- [ ] Vargottama planets correctly flagged
- [ ] D10 ascendant verified against reference

---

# PHASE 3 — Aspects, Yogas, Afflictions

**Goal:** Compute every inter-planetary relationship the LLM will need.

## Tasks

### 3.1 `vedic_llm/compute/aspects.py`

Graha drishti (planetary aspects by house count from planet's house):
- All planets: 7th house aspect
- Mars: additional 4th and 8th
- Jupiter: additional 5th and 9th
- Saturn: additional 3rd and 10th
- Rahu/Ketu: classical texts vary — use 5th, 7th, 9th per Phaladeepika (make this configurable)

```python
def aspects_cast_by(planet_state: PlanetState) -> list[int]:
    """Returns house numbers aspected."""

def aspects_on_house(chart: Chart, house: int) -> list[Planet]:
    """Returns planets aspecting this house."""

def aspects_on_planet(chart: Chart, planet: Planet) -> list[Planet]: ...
```

### 3.2 `vedic_llm/compute/yogas.py`

Detect classical yogas. Start with the essentials:

- **Gajakesari** — Jupiter in kendra from Moon
- **Raja Yoga** — kendra lord conjunct/aspected by trikona lord
- **Dhana Yoga** — 2nd/5th/9th/11th lord associations
- **Neecha Bhanga Raja Yoga** — debilitated planet with cancellation (dispositor in kendra, or exaltation lord of debilitation sign in kendra)
- **Vipareeta Raja Yoga** — 6/8/12 lord in another 6/8/12 house
- **Budhaditya** — Sun + Mercury conjunction
- **Chandra-Mangala** — Moon + Mars conjunction
- **Kemadruma** — Moon with no planets in 2nd or 12th from it (and no aspect)
- **Kala Sarpa** — all 7 planets between Rahu and Ketu

```python
@dataclass
class Yoga:
    name: str
    planets_involved: list[Planet]
    houses_activated: list[int]
    strength: str  # "strong", "moderate", "weak", "cosmetic"
    reason: str

def detect_yogas(chart: Chart) -> list[Yoga]: ...
```

### 3.3 Afflictions

- Combust (done in Phase 1)
- Papa kartari — malefics in both 12th and 2nd from a house/planet
- Shubha kartari — benefics in both 12th and 2nd from a house/planet
- Planetary war (graha yuddha) — two non-luminary planets within 1° of each other

```python
def papa_kartari(chart: Chart, target_house: int) -> bool: ...
def shubha_kartari(chart: Chart, target_house: int) -> bool: ...
def planetary_war(chart: Chart) -> list[tuple[Planet, Planet, Planet]]:
    """Returns (p1, p2, winner) for each war."""
```

## Acceptance Criteria

- [ ] Aspects correctly computed for all planets in fixtures
- [ ] At least 8 yoga types detectable
- [ ] Papa/shubha kartari verified on 3+ hand-traced charts

---

# PHASE 4 — Vimshottari Dasha

**Goal:** Given birth moment, compute current MD/AD/PD and upcoming transitions.

## Tasks

### 4.1 `vedic_llm/compute/dasha.py`

Vimshottari cycle (120 years total):
```
Ketu: 7, Venus: 20, Sun: 6, Moon: 10, Mars: 7,
Rahu: 18, Jupiter: 16, Saturn: 19, Mercury: 17
```

Each nakshatra maps to a starting dasha lord:
- Ashwini, Magha, Mula → Ketu
- Bharani, Purva Phalguni, Purvashadha → Venus
- Krittika, Uttara Phalguni, Uttarashadha → Sun
- Rohini, Hasta, Shravana → Moon
- Mrigashira, Chitra, Dhanishta → Mars
- Ardra, Swati, Shatabhisha → Rahu
- Punarvasu, Vishakha, Purva Bhadrapada → Jupiter
- Pushya, Anuradha, Uttara Bhadrapada → Saturn
- Ashlesha, Jyeshtha, Revati → Mercury

```python
@dataclass
class DashaPeriod:
    lord: Planet
    level: str  # "MD", "AD", "PD", "SPD"
    start: datetime
    end: datetime
    parent: Optional['DashaPeriod'] = None

def compute_dasha_balance_at_birth(moon_longitude: float) -> tuple[Planet, timedelta]:
    """Returns (starting MD lord, remaining time in that MD)."""

def compute_mahadasha_sequence(birth: BirthData) -> list[DashaPeriod]: ...
def compute_antardasha(md: DashaPeriod) -> list[DashaPeriod]: ...
def compute_pratyantardasha(ad: DashaPeriod) -> list[DashaPeriod]: ...

def current_dasha_stack(birth: BirthData, at: datetime) -> dict:
    """Returns {'MD': period, 'AD': period, 'PD': period}."""

def upcoming_transitions(birth: BirthData, at: datetime, years_ahead: int = 5) -> list[DashaPeriod]: ...
```

### 4.2 Tests

Verify dasha start/end dates against a reference tool (JHora, Parashara's Light) for all fixture charts. Within 1 day tolerance.

## Acceptance Criteria

- [ ] MD sequence matches reference for all fixtures
- [ ] Current AD and PD computation accurate to the day
- [ ] Upcoming transitions listed correctly

---

# PHASE 5 — Transits (Gochara)

**Goal:** Overlay current planetary positions onto the natal chart.

## Tasks

### 5.1 `vedic_llm/compute/transit.py`

```python
@dataclass
class TransitSnapshot:
    timestamp: datetime
    transit_planets: dict[Planet, PlanetState]  # positions now
    natal_house_occupancy: dict[int, list[Planet]]  # which transit planets in each natal house
    transit_over_natal_planets: list[tuple[Planet, Planet, float]]
    # (transit_planet, natal_planet, orb_degrees) for conjunctions within 3°

def snapshot(natal: Chart, at: datetime) -> TransitSnapshot: ...

def saturn_sade_sati(natal: Chart, at: datetime) -> dict:
    """Returns {'phase': 'pre'/'peak'/'post'/'none', 'start': ..., 'end': ...}.
    Sade Sati = Saturn transiting 12th, 1st, 2nd from natal Moon."""

def jupiter_transit_from_moon(natal: Chart, at: datetime) -> int:
    """House number (1-12) that transit Jupiter is in counted from natal Moon."""

def rahu_ketu_axis_activation(natal: Chart, at: datetime) -> list[int]:
    """Which natal houses are currently on the Rahu-Ketu axis."""
```

### 5.2 Ashtakavarga (optional but recommended)

Compute each planet's bindu count in each sign. A transit over a sign with ≥4 bindus is supportive; <3 indicates weakness.

```python
def sarvashtakavarga(chart: Chart) -> dict[Sign, int]: ...
def bhinnashtakavarga(chart: Chart, planet: Planet) -> dict[Sign, int]: ...
```

## Acceptance Criteria

- [ ] Current transits computed correctly
- [ ] Sade Sati detection verified on 2+ known cases
- [ ] Ashtakavarga bindu totals = 337 (sum of all planets' totals, classical check)

---

# PHASE 6 — Fact Extraction Layer (Dossier Builder)

**Goal:** Convert raw chart data into LLM-ready JSON "dossiers." This is the critical bridge to the LLM layer.

## Tasks

### 6.1 `vedic_llm/models/dossier.py`

Define `FactDossier` models. These are the exact structures that feed into prompts — design them so the LLM has zero ambiguity.

```python
class PlanetFacts(BaseModel):
    planet: str
    sign: str
    degree: str  # formatted "18°42'"
    house: int
    nakshatra: str
    pada: int
    dignity: str
    retrograde: bool
    combust: bool
    vargottama: bool
    aspects_cast_on_houses: list[int]
    conjunctions: list[str]  # other planet names within 5° in same sign
    rules_houses: list[int]  # which houses this planet owns
    functional_nature: str  # "yogakaraka", "benefic", "malefic", "neutral"
    d9_sign: str
    d9_dignity: str
    d9_house_from_d9_lagna: int
    d10_sign: str
    d10_house: int

class HouseFacts(BaseModel):
    number: int
    sign: str
    lord: str
    lord_sign: str
    lord_house: int
    lord_dignity: str
    lord_is_combust: bool
    lord_is_retrograde: bool
    occupants: list[str]
    aspected_by: list[str]
    is_hemmed_by_malefics: bool  # papa kartari
    is_hemmed_by_benefics: bool  # shubha kartari
    karaka: str  # natural significator
    karaka_state: str  # "strong"/"afflicted"/"neutral" (one-word summary)

class NatalDossier(BaseModel):
    birth: dict
    ascendant: dict
    planets: dict[str, PlanetFacts]
    houses: dict[int, HouseFacts]
    yogas: list[dict]
    afflictions: list[dict]
    vargottama_planets: list[str]
    atmakaraka: str  # highest-degree planet
    amatyakaraka: str  # second-highest degree
    functional_benefics: list[str]
    functional_malefics: list[str]
    d9_summary: dict

class DashaDossier(BaseModel):
    current_md: dict
    current_ad: dict
    current_pd: dict
    md_ad_relationship: str
    ad_pd_relationship: str
    doubly_activated_houses: list[int]
    upcoming_transitions: list[dict]

class TransitDossier(BaseModel):
    timestamp: str
    transit_positions: dict[str, dict]
    transit_overlays: list[dict]  # transit planet → natal house
    sade_sati: dict
    jupiter_from_moon: int
    active_natal_houses: list[int]  # houses receiving major transit attention
```

### 6.2 `vedic_llm/extract/*.py`

Write three extractors:
- `extract_natal_dossier(chart_d1: Chart, chart_d9: Chart, chart_d10: Chart) -> NatalDossier`
- `extract_dasha_dossier(birth: BirthData, natal: Chart, at: datetime) -> DashaDossier`
- `extract_transit_dossier(natal: Chart, at: datetime) -> TransitDossier`

Each extractor pulls data from the compute layer and formats it for LLM consumption.

### 6.3 Snapshot tests

For each fixture chart, generate the dossier and save to `tests/fixtures/dossiers/<name>.json`. Add snapshot tests to detect regressions.

## Acceptance Criteria

- [ ] Dossier JSON is human-readable and complete
- [ ] No field is ever null without explanation
- [ ] A human astrologer reading the dossier has everything needed to analyze

---

# PHASE 7 — LLM Client + Prompt Library

**Goal:** Build the reasoning layer. This phase is where the quality of the app is determined.

## Tasks

### 7.1 `vedic_llm/llm/client.py`

```python
class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-opus-4-7"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyze(self, system: str, user: str, max_tokens: int = 8000) -> str: ...

    def analyze_json(self, system: str, user: str, schema: dict) -> dict:
        """Force JSON output using tool use or prefill."""
```

Use `claude-opus-4-7` for maximum reasoning quality on natal analysis. Consider `claude-sonnet-4-6` for cheaper stages.

### 7.2 `vedic_llm/prompts/natal.py`

The master natal prompt. Copy this verbatim — it is designed so the LLM cannot skip steps.

```python
NATAL_SYSTEM_PROMPT = """
You are a senior Vedic astrologer with 40 years of experience in classical Parashari Jyotish. You have deeply studied Brihat Parashara Hora Shastra, Phaladeepika, Jataka Parijata, Saravali, and Uttara Kalamrita. You reason step by step, never skip a factor, and never invent positions — you work only from the facts provided in the chart dossier.

You produce Layer 1 of a three-layer analysis. Your job is to establish the BASELINE POTENTIAL of the chart — what is structurally possible, what is blocked, what themes dominate. You do NOT predict timing; that is handled by the dasha and transit layers separately.
"""

NATAL_USER_PROMPT_TEMPLATE = """
# CHART DOSSIER
<dossier>
{dossier_json}
</dossier>

# ANALYTICAL METHOD — FOLLOW EXACTLY

For each of the 12 houses, you MUST complete this 8-step analysis. Do not combine steps. Do not skip steps. Cite the specific dossier fact that supports each claim using the format `[fact: planets.Jupiter.house=4]`.

## The 8-Step House Method

**Step 1 — House & Lord Identification**
State the sign on the house and its lord (the Bhavesh).

**Step 2 — Lord's Placement**
Which house does the lord occupy? Is that a kendra (1,4,7,10), trikona (1,5,9), dusthana (6,8,12), or upachaya (3,6,10,11)? How does this placement redirect the house's energy?

**Step 3 — Lord's Dignity**
What is the lord's dignity (exalted, moolatrikona, own, great friend, friend, neutral, enemy, great enemy, debilitated)? Is it retrograde? Is it combust? If debilitated, check the dossier for Neecha Bhanga cancellation conditions.

**Step 4 — Occupants**
Who sits in the house? For each occupant: (a) its natural nature (benefic/malefic), (b) its own dignity, (c) which other houses it rules (because it imports those themes). An empty house is not weak — it shifts weight onto the lord.

**Step 5 — Aspects**
Which planets aspect this house? Distinguish benefic aspects (Jupiter, Venus, waxing Moon, unafflicted Mercury) from malefic aspects (Saturn, Mars, Rahu, Ketu, debilitated Sun). Note if the lord itself aspects back on its own house — this is a major strengthener.

**Step 6 — Karaka**
What is the natural karaka of this house (e.g., Sun for 10th, Jupiter for 5th, Venus for 7th, Saturn for 8th/12th)? Is the karaka strong or afflicted? A weak karaka undermines the house even if other factors look good.

**Step 7 — D9 Cross-Check**
What is the lord's placement and dignity in Navamsa (D9)? D9 is the veto layer. A lord strong in D1 but debilitated or in dusthana in D9 loses 40-60% of its D1 promise. A lord weak in D1 but exalted in D9 often delivers more than D1 suggests, especially after age 36.

**Step 8 — Synthesis**
On a scale of 1-10, rate the house's strength. State 2-3 dominant themes this house will express in the native's life. Distinguish what is PROMISED (structural potential) from what is CONTINGENT (requires dasha/transit activation — to be assessed in later layers).

## Houses to Analyze — IN THIS ORDER

1, 10, 2, 11, 5, 9, 4, 7, 3, 6, 8, 12

(Lagna first — it is the foundation. Then the Arth trikona — career/wealth. Then Dharma/Sukha houses. Dusthanas last so you have full chart context.)

## After All 12 Houses — Additional Analysis

### Yoga Evaluation
For each yoga listed in `dossier.yogas`, evaluate:
- Is it FUNCTIONAL (the planets involved are strong) or COSMETIC (planets are weak/afflicted)?
- Which houses does it activate?
- What concrete life theme does it produce?

### Special Planets
- **Atmakaraka** (`{atmakaraka}`): the soul's agenda. Where is it placed? What is its D9 house (Karakamsha)?
- **Amatyakaraka** (`{amatyakaraka}`): vocational indicator. What career direction does it suggest?
- **Vargottama planets**: any planet that is vargottama is a pillar of the chart — treat as structurally reinforced.

### The Triple 10th (for career pre-read)
Evaluate the 10th house THREE times: from Lagna, from Moon, from Sun. If all three 10ths are strong, career is robust. If only one is strong, career is one-dimensional.

## MANDATORY COMPLETENESS CHECKLIST

Before you output, verify you have explicitly addressed every item below. If any item is missing, your answer is incomplete.

- [ ] Lagna sign, Lagna lord placement, Lagna lord dignity
- [ ] All 12 houses analyzed with the full 8-step method
- [ ] Moon's condition (mental/emotional foundation) explicitly discussed
- [ ] Sun's condition (vitality, authority, soul) explicitly discussed
- [ ] Every debilitated planet checked for Neecha Bhanga
- [ ] Every planet in 6/8/12 checked for Vipareeta potential
- [ ] Every retrograde planet's implications discussed
- [ ] Every combust planet's functional loss discussed
- [ ] Papa kartari / Shubha kartari noted for every affected house
- [ ] All conjunctions interpreted (what each fuses together)
- [ ] All yogas in the dossier evaluated as functional or cosmetic
- [ ] Atmakaraka discussed with Karakamsha
- [ ] Amatyakaraka discussed for vocation
- [ ] Vargottama planets noted as structural pillars
- [ ] Functional benefics and malefics considered for this ascendant
- [ ] D9 state of every major planet explicitly cross-checked
- [ ] Triple 10th assessed (from Lagna, Moon, Sun)

## REASONING RULES

1. **Cite every claim** with `[fact: <dossier_path>]`. If you cannot cite a fact, do not make the claim.
2. **Conflicting signals**: when D1 says one thing and D9 another, explicitly state the conflict and explain how classical texts resolve it for this specific case.
3. **Distinguish classical rule from specific reading**: "Parashara says X in general. In THIS chart, because Y, it means Z."
4. **No hallucination**: if a fact is not in the dossier, say "Dossier does not specify" and proceed.
5. **Neutral tone**: describe tendencies and themes, not fortune-telling. Avoid "you will" — prefer "this chart indicates a tendency toward..."
6. **No boilerplate caveats**: skip the disclaimers about astrology. This is a technical analysis.

## OUTPUT FORMAT

Return ONLY valid JSON in this schema:

```json
{{
  "lagna_assessment": {{
    "score": 7,
    "summary": "2-3 sentence summary",
    "reasoning": "Full 8-step trace with cited facts"
  }},
  "houses": {{
    "1": {{"score": <1-10>, "themes": [...], "strengths": [...], "weaknesses": [...], "reasoning": "..."}},
    "2": {{...}},
    ...
    "12": {{...}}
  }},
  "moon_assessment": {{ "score": ..., "reasoning": "..." }},
  "sun_assessment": {{ "score": ..., "reasoning": "..." }},
  "yogas_evaluated": [
    {{"name": "...", "functional": true, "houses_activated": [...], "effect": "..."}}
  ],
  "special_planets": {{
    "atmakaraka": {{"planet": "...", "reading": "..."}},
    "amatyakaraka": {{"planet": "...", "vocation_indication": "..."}},
    "vargottama": [...]
  }},
  "triple_tenth": {{
    "from_lagna": {{"score": ..., "reasoning": "..."}},
    "from_moon": {{"score": ..., "reasoning": "..."}},
    "from_sun": {{"score": ..., "reasoning": "..."}}
  }},
  "key_strengths": ["Top 5 standout strengths"],
  "key_vulnerabilities": ["Top 5 standout vulnerabilities"],
  "character_signature": "2-3 paragraph portrait of the native's fundamental nature",
  "life_themes": ["4-6 dominant life themes this chart will play out"]
}}
```
"""

def build_natal_prompt(dossier: NatalDossier) -> tuple[str, str]:
    """Returns (system, user) prompts."""
    user = NATAL_USER_PROMPT_TEMPLATE.format(
        dossier_json=dossier.model_dump_json(indent=2),
        atmakaraka=dossier.atmakaraka,
        amatyakaraka=dossier.amatyakaraka,
    )
    return NATAL_SYSTEM_PROMPT, user
```

### 7.3 `vedic_llm/prompts/dasha.py`

```python
DASHA_SYSTEM_PROMPT = """
You are the same senior Vedic astrologer from Stage 1. You now analyze the ACTIVATION layer — which parts of the natal potential are being unlocked by the current Vimshottari dasha sequence.

Your reasoning depends on Stage 1 (natal analysis). Where Stage 1 established what is POSSIBLE, you now determine what is LIVE RIGHT NOW.

Core principle: A dasha lord's effects come from, in priority order:
1. The houses it owns (primary — 70% of the theme)
2. The house it sits in (secondary — 20%)
3. The houses it aspects (tertiary — 10%)
4. Its dignity modulates all of the above (strong lord = full expression; weak lord = distorted expression)
"""

DASHA_USER_PROMPT_TEMPLATE = """
# NATAL ANALYSIS (Stage 1 output)
<natal>
{natal_analysis_json}
</natal>

# DASHA DOSSIER
<dasha>
{dasha_dossier_json}
</dasha>

# ANALYTICAL METHOD

## For the MAHADASHA lord (`{md_lord}`)
Complete all 7 steps:

1. **Natal strength recap**: From Stage 1, what is this planet's baseline strength and dignity?
2. **House ownership effects**: Which houses does this planet rule? Those themes dominate the entire MD (many years).
3. **House occupation effects**: Which house does it sit in? That life area gets direct activation.
4. **Aspects cast**: Which houses does it aspect? Those get indirect activation.
5. **D9 confirmation**: Does the D9 placement support or undermine what D1 promises during this MD?
6. **Functional nature**: Is this planet a yogakaraka, functional benefic, or functional malefic for the ascendant? This flips meaning.
7. **Karaka roles**: What life areas does this planet naturally signify? Those themes are live.

## For the ANTARDASHA lord (`{ad_lord}`)
Repeat all 7 steps.

## For the PRATYANTARDASHA lord (`{pd_lord}`)
Repeat all 7 steps (more briefly — this is a short window).

## Interaction Analysis

- **MD-AD compatibility**: Are they friends, neutral, or enemies? Do they mutually aspect each other? Is there an exchange (parivartana)? Do they sit in kendra/trikona from each other (yoga-forming)? A hostile MD-AD combination produces internal conflict in the life theme.
- **Doubly-activated houses**: Which houses are activated by BOTH the MD and AD lord? Those themes are the DOMINANT focus of this year.
- **Triply-activated houses**: Any house activated by MD, AD, AND PD? That is the urgent immediate theme of this month.

## Timeline Reading

- What is the trajectory of this MD overall? (Begin → middle → end)
- What will shift when the current AD ends (`{ad_end_date}`)?
- What upcoming transitions in the next 2 years need flagging?

## MANDATORY COMPLETENESS CHECKLIST

- [ ] MD lord's 7-point analysis
- [ ] AD lord's 7-point analysis
- [ ] PD lord's 7-point analysis
- [ ] MD-AD compatibility discussed
- [ ] AD-PD compatibility discussed
- [ ] Doubly-activated houses identified
- [ ] Triply-activated houses identified (if any)
- [ ] Current AD's position within the MD (early/middle/late) noted
- [ ] Next 3 major transitions identified with their themes
- [ ] Functional nature of each active lord for this ascendant

## OUTPUT FORMAT

```json
{{
  "mahadasha": {{
    "lord": "...",
    "natal_strength": "...",
    "houses_owned_effects": "...",
    "house_occupation_effects": "...",
    "aspects_effects": "...",
    "d9_confirmation": "...",
    "functional_nature": "...",
    "karaka_roles": "...",
    "overall_quality": "<1-10>",
    "dominant_themes": [...]
  }},
  "antardasha": {{...same structure...}},
  "pratyantardasha": {{...same structure...}},
  "interactions": {{
    "md_ad_relationship": "...",
    "ad_pd_relationship": "...",
    "doubly_activated_houses": [...],
    "triply_activated_houses": [...]
  }},
  "current_period_verdict": {{
    "quality": "<1-10>",
    "dominant_life_themes": [...],
    "supportive_areas": [...],
    "challenging_areas": [...],
    "summary": "2-3 paragraph summary of what this period is really about"
  }},
  "upcoming_shifts": [
    {{"date": "...", "change": "...", "expected_effect": "..."}}
  ]
}}
```
"""
```

### 7.4 `vedic_llm/prompts/transit.py`

```python
TRANSIT_SYSTEM_PROMPT = """
You are the senior Vedic astrologer. You now analyze the TRIGGER layer — current planetary transits as they interact with the natal chart and active dasha.

Principle: Transits alone do not create events. They TRIGGER what the natal chart promises AND what the current dasha has activated. A transit over a natally strong house that is also dasha-activated = event. A transit over a natally weak or dasha-inactive area = minor mood shift at most.

Weight transits by speed:
- Saturn, Rahu, Ketu, Jupiter: structural, months-to-years impact. Primary.
- Mars: trigger, weeks. Catalyzes Saturn/Jupiter setups.
- Sun, Mercury, Venus: monthly flavor. Fine-tune timing.
- Moon: daily — use only for muhurta, not for predictions.
"""

TRANSIT_USER_PROMPT_TEMPLATE = """
# NATAL ANALYSIS
<natal>
{natal_analysis_json}
</natal>

# DASHA ANALYSIS
<dasha>
{dasha_analysis_json}
</dasha>

# TRANSIT DOSSIER
<transits>
{transit_dossier_json}
</transits>

# ANALYTICAL METHOD

## For each SLOW transit planet (Saturn, Jupiter, Rahu, Ketu):
1. Which natal house is it currently transiting?
2. What is that house's natal strength (from Stage 1)?
3. Is that house activated by the current dasha (from Stage 2)?
4. What natal planets is it conjoining or aspecting?
5. What Ashtakavarga bindu count does that sign have? (≥4 supportive, ≤3 weak)
6. Verdict: is this transit producing a real event or just background noise?

## Sade Sati check
If Saturn is in sade sati (12th/1st/2nd from natal Moon), discuss the phase and its implications.

## Jupiter-from-Moon
Jupiter's house count from natal Moon indicates the general mood of the year for wellbeing. State the count and classical interpretation.

## Rahu-Ketu axis
Which natal houses currently sit on the Rahu-Ketu axis? Those houses are in "eclipse" — amplified, unstable, and karmically urgent.

## Trigger Analysis
For the top 3 active themes from Stage 2 (dasha analysis), determine:
- Is there a current transit triggering this theme? (YES/NO)
- If YES: what is the trigger, and when does it peak?
- If NO: this theme is "armed" but not yet firing.

## MANDATORY CHECKLIST

- [ ] Saturn transit analyzed (it is the biggest)
- [ ] Jupiter transit analyzed
- [ ] Rahu-Ketu axis analyzed
- [ ] Sade Sati status checked
- [ ] Jupiter-from-Moon reading done
- [ ] Each of Stage 2's top themes checked for transit trigger
- [ ] Ashtakavarga bindus consulted for major transits

## OUTPUT FORMAT

```json
{{
  "slow_transits": {{
    "saturn": {{"sign": "...", "house": ..., "natal_house_strength": "...", "dasha_activation": "...", "aspects_on_natal": [...], "verdict": "..."}},
    "jupiter": {{...}},
    "rahu": {{...}},
    "ketu": {{...}}
  }},
  "sade_sati": {{"active": bool, "phase": "...", "impact": "..."}},
  "jupiter_from_moon": {{"house": ..., "reading": "..."}},
  "rahu_ketu_axis_natal_houses": [...],
  "trigger_analysis": [
    {{"theme": "...", "triggered": bool, "trigger_source": "...", "peak_window": "..."}}
  ],
  "active_windows": [
    {{"start": "...", "end": "...", "theme": "...", "intensity": "high/medium/low"}}
  ]
}}
```
"""
```

### 7.5 `vedic_llm/prompts/synthesis.py`

```python
SYNTHESIS_SYSTEM_PROMPT = """
You are the senior Vedic astrologer producing the FINAL integrated reading. You have three layers of analysis: natal potential (baseline), dasha activation (what's live), and transit triggers (what's firing now).

Your job is to integrate them into a coherent, actionable portrait of the native's life right now and the next 2 years.

Governing principle:
MANIFESTATION = NATAL PROMISE × DASHA ACTIVATION × TRANSIT TRIGGER
If any factor is zero-ish, the event does not fire. All three must cooperate.
"""

SYNTHESIS_USER_PROMPT_TEMPLATE = """
<natal>{natal_analysis_json}</natal>
<dasha>{dasha_analysis_json}</dasha>
<transits>{transit_analysis_json}</transits>

# SYNTHESIS METHOD

## For each major life area (career, wealth, health, relationships, family, spiritual):

1. What does NATAL promise? (strong / moderate / weak)
2. What is DASHA doing to this area? (activating / neutral / obstructing)
3. What are TRANSITS doing? (triggering / dormant / adverse)
4. **Verdict**: Combine using the principle above. If all three align favorably → active and positive. If natal strong but dasha dormant → dormant potential. If dasha active but natal weak → effortful but limited results. Etc.

## Current Life Chapter
What is the 1-2 sentence headline of what this native is living RIGHT NOW?

## The Next 12 Months
Walk the user through the next 12 months in 3-month chunks, calling out:
- Peak opportunity windows
- Caution windows
- Major dasha or transit shifts

## The Next 24 Months
Wider-lens view: what is the overall arc?

## Three Priorities
What are the three things this chart is telling the native to focus on RIGHT NOW?

## OUTPUT FORMAT

```json
{{
  "current_life_chapter": "1-2 sentence headline",
  "area_verdicts": {{
    "career": {{"natal": "...", "dasha": "...", "transit": "...", "integrated": "...", "score": <1-10>}},
    "wealth": {{...}},
    "health": {{...}},
    "relationships": {{...}},
    "family": {{...}},
    "spiritual": {{...}}
  }},
  "next_12_months": [
    {{"window": "Months 1-3", "theme": "...", "opportunities": [...], "cautions": [...]}},
    {{"window": "Months 4-6", ...}},
    {{"window": "Months 7-9", ...}},
    {{"window": "Months 10-12", ...}}
  ],
  "next_24_months_arc": "...",
  "three_priorities": ["...", "...", "..."],
  "final_portrait": "4-6 paragraph integrated reading"
}}
```
"""
```

### 7.6 Topic-specific prompts — `vedic_llm/prompts/topics/career.py`

```python
CAREER_SYSTEM_PROMPT = """
You are a Vedic career astrologer. You answer the specific question: what does this chart indicate about the native's career?

Focus houses: 10 (primary), 6, 2, 11 (secondary), 1, 9 (supporting).
Focus karakas: Sun (authority), Saturn (work), Mercury (skill), Jupiter (wisdom).
Focus divisional: D10 (Dasamsa) is the career chart — give it heavy weight.
"""

CAREER_USER_PROMPT_TEMPLATE = """
<natal>{natal_analysis_json}</natal>
<dasha>{dasha_analysis_json}</dasha>
<transits>{transit_analysis_json}</transits>
<d10_dossier>{d10_dossier_json}</d10_dossier>

# CAREER-SPECIFIC ANALYSIS

## Step 1 — Strength of Career Houses
Re-read the 10th, 6th, 2nd, 11th house assessments from the natal stage. Summarize each.

## Step 2 — Career Karakas
For Sun, Saturn, Mercury, Jupiter: state their natal strength and how that shapes career.

## Step 3 — Career Flavor
Based on the 10th house sign, 10th lord's placement, and occupants of the 10th, describe the TYPE of career this chart indicates. Reference:
- Sun → authority, government, leadership, politics
- Saturn → service, labor, systems, law, mining, oil, old/traditional industries
- Mercury → commerce, communication, IT, writing, analysis, trading
- Jupiter → teaching, advisory, finance, law, counseling, publishing
- Venus → arts, design, luxury, entertainment, diplomacy, beauty
- Mars → engineering, military, surgery, real estate, sports, competitive fields
- Moon → public-facing, hospitality, food, women/children-related
- Rahu → foreign, tech, unconventional, mass-media, aviation
- Ketu → research, spirituality, niche expertise, healing, occult

## Step 4 — Amatyakaraka
The Amatyakaraka's sign and D9 placement (Karakamsha's 10th) reveals the TRUE professional calling. Analyze.

## Step 5 — D10 Analysis
Analyze the D10 chart's ascendant, 10th house, 10th lord, and Sun/Saturn placement in D10.

## Step 6 — Triple 10th
Re-check the 10th from Lagna, Moon, and Sun.

## Step 7 — Current Period Impact
Is the current MD/AD activating career houses? What about transits?

## Step 8 — Verdict
1. What career(s) best match this chart?
2. When is the current/next career peak window?
3. What obstacles or blind spots should the native watch for?
4. If the native asks "should I change jobs / start a business / ask for promotion NOW" — what do the current dasha and transits say?

## OUTPUT FORMAT

```json
{{
  "career_house_summary": {{"10th": "...", "6th": "...", "2nd": "...", "11th": "..."}},
  "career_karakas": {{"sun": "...", "saturn": "...", "mercury": "...", "jupiter": "..."}},
  "career_flavor": {{"primary": "...", "secondary": "...", "reasoning": "..."}},
  "amatyakaraka_reading": "...",
  "d10_verdict": "...",
  "triple_tenth": {{...}},
  "current_period_impact": "...",
  "recommended_careers": [...],
  "peak_windows": [...],
  "obstacles": [...],
  "immediate_advice": "..."
}}
```
"""
```

Similar structure for `wealth.py`, `health.py`, `relationships.py` — each with its own focus houses, karakas, divisional charts (D2 for wealth, D6/D30 for health, D7/D9 for marriage), and 8-step method.

### 7.7 `vedic_llm/llm/orchestrator.py`

```python
class AnalysisOrchestrator:
    def __init__(self, client: ClaudeClient):
        self.client = client
        self.cache = {}  # simple in-memory cache keyed by (chart_hash, stage)

    def run_full_analysis(
        self,
        birth: BirthData,
        at: datetime = None,
        topics: list[str] = None,
    ) -> dict:
        at = at or datetime.utcnow()

        # Compute layer
        d1 = build_d1_chart(birth)
        d9 = build_d9_chart(d1)
        d10 = build_d10_chart(d1)

        # Extract dossiers
        natal_dossier = extract_natal_dossier(d1, d9, d10)
        dasha_dossier = extract_dasha_dossier(birth, d1, at)
        transit_dossier = extract_transit_dossier(d1, at)

        # Stage 1: Natal
        natal_sys, natal_user = build_natal_prompt(natal_dossier)
        natal_result = self.client.analyze_json(natal_sys, natal_user, schema=NATAL_SCHEMA)

        # Stage 2: Dasha
        dasha_sys, dasha_user = build_dasha_prompt(natal_result, dasha_dossier)
        dasha_result = self.client.analyze_json(dasha_sys, dasha_user, schema=DASHA_SCHEMA)

        # Stage 3: Transit
        transit_sys, transit_user = build_transit_prompt(natal_result, dasha_result, transit_dossier)
        transit_result = self.client.analyze_json(transit_sys, transit_user, schema=TRANSIT_SCHEMA)

        # Stage 4: Synthesis
        synthesis = self.client.analyze_json(*build_synthesis_prompt(natal_result, dasha_result, transit_result), schema=SYNTHESIS_SCHEMA)

        # Stage 5: Topics (optional)
        topic_results = {}
        if topics:
            for topic in topics:
                topic_results[topic] = self._run_topic(topic, natal_result, dasha_result, transit_result, d10)

        return {
            "layers": {
                "natal": natal_result,
                "dasha": dasha_result,
                "transits": transit_result,
            },
            "synthesis": synthesis,
            "topics": topic_results,
            "dossiers": {  # keep for debugging
                "natal": natal_dossier.model_dump(),
                "dasha": dasha_dossier.model_dump(),
                "transits": transit_dossier.model_dump(),
            },
        }
```

## Acceptance Criteria

- [ ] Each stage produces valid JSON matching its schema
- [ ] Stages chain correctly (each consumes the previous)
- [ ] A full analysis completes end-to-end on a fixture chart
- [ ] Cost tracking: log tokens per stage

---

# PHASE 8 — CLI

**Goal:** User-friendly command line interface.

## Tasks

### 8.1 `vedic_llm/cli.py`

```python
import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer()
console = Console()

@app.command()
def analyze(
    date: str = typer.Option(..., help="Birth date YYYY-MM-DD"),
    time: str = typer.Option(..., help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude"),
    place: str = typer.Option(""),
    topic: list[str] = typer.Option([], help="career, wealth, health, relationships"),
    output: str = typer.Option("report.json"),
    at: str = typer.Option(None, help="Analysis timestamp, defaults to now"),
):
    """Run full analysis."""
    ...

@app.command()
def dossier(...):
    """Dump just the dossier JSON without calling LLM (for debugging prompts)."""

@app.command()
def chart(...):
    """Print a text chart (Lagna, planet positions, houses) — no LLM."""
```

### 8.2 Pretty report rendering

Add a `reports/formatter.py` that converts the JSON output to a readable Markdown report:
- Header with birth details
- Lagna + chart summary table
- Natal section
- Dasha section
- Transit section
- Synthesis section
- Topic sections

## Acceptance Criteria

- [ ] `vedic analyze --date 1985-07-15 --time 04:30 --lat 12.97 --lon 77.59 --topic career` produces a full report
- [ ] `vedic dossier ...` prints the dossier for prompt debugging
- [ ] `vedic chart ...` shows positions without API calls

---

# PHASE 9 — Evaluation & Quality Loop

**Goal:** Verify analytical quality on known charts.

## Tasks

### 9.1 Golden charts

Pick 5 well-known public figures with verifiable life events (e.g., published biographies). Create detailed expectations:
- What the natal should say about career
- What the dasha should say about the period when a major event happened
- Whether the synthesis correctly identifies known life themes

### 9.2 Evaluation script

```python
# tests/eval.py
def evaluate_against_golden(chart_id: str) -> EvalReport:
    """Run full analysis, compare against known facts, score each claim."""
```

### 9.3 Prompt iteration log

Maintain `docs/prompt_iterations.md` — every time you tune a prompt, log:
- What was wrong
- What you changed
- How the fixture outputs shifted

This becomes institutional knowledge.

## Acceptance Criteria

- [ ] 5 golden charts analyzed
- [ ] Quality checklist score ≥80% on each
- [ ] Prompt iteration log documented

---

# PHASE 10 — Polish & Extensibility

## Tasks

### 10.1 Additional divisional charts
D2 (wealth), D3 (siblings), D4 (home), D7 (children), D12 (parents), D24 (education), D30 (misfortunes). Each extends the topic prompts.

### 10.2 Remedial measures prompt (optional)
Add a `remedies.py` prompt that suggests classical remedies (gemstones, mantras, charitable acts) based on afflictions — clearly framed as classical tradition, not Claude's medical advice.

### 10.3 Caching
Hash (birth_data + analysis_datetime + stage_name) and cache results to disk in `cache/`. Full analyses cost real money — cache aggressively during development.

### 10.4 Comparison charts
Synastry (relationship compatibility) — requires two charts. Future phase.

### 10.5 Web UI (optional)
FastAPI backend exposing the orchestrator; simple React/Next.js frontend.

---

# Execution Order for Claude Code

Run phases sequentially. Do not start a phase until the previous one passes acceptance criteria.

```
Phase 0  → bootstrap
Phase 1  → compute D1
Phase 2  → compute D9, D10
Phase 3  → aspects, yogas
Phase 4  → dasha
Phase 5  → transits
Phase 6  → dossiers
Phase 7  → LLM + prompts (the critical phase)
Phase 8  → CLI
Phase 9  → evaluation loop
Phase 10 → polish
```

Estimated timeline if executing with Claude Code: Phases 0-5 are mechanical (1-2 days); Phase 6-7 require careful prompt design (2-3 days of iteration); Phases 8-9 another day. Total: roughly a week of focused work.

---

# Critical Design Decisions (Do Not Change Without Thinking)

1. **Python computes, LLM reasons.** Never blur this line.
2. **Prompts are code.** Version them. Test them. Iterate on them like you iterate on code.
3. **Dossiers are the contract** between the compute layer and the LLM. If the LLM is missing something, fix the dossier, not the prompt.
4. **Cite every claim** in LLM output. No hallucination tolerated.
5. **D9 is the veto layer.** A D1-strong verdict without D9 cross-check is incomplete.
6. **The geometric AND** — natal × dasha × transit. Any weak factor drags down the result.
7. **JSON output everywhere.** Strict schemas. No prose-only stages before synthesis.

---

# When You (Claude Code) Get Stuck

- **Astronomical disagreement with reference tool**: verify ayanamsa (Lahiri vs Raman), verify timezone handling (convert local → UTC before calling ephemeris).
- **D9 positions wrong**: re-check movable/fixed/dual sign starting rule.
- **Dasha dates off by years**: check if Moon longitude is sidereal (it must be).
- **LLM output not valid JSON**: use prefill (`assistant: {`) and/or tool-use forcing.
- **LLM skipping checklist items**: make the checklist longer and more explicit. Consider splitting into sub-stages.
- **Hallucinated planet positions**: tighten prompt rule about citing `[fact: ...]`; fail loud if citations missing.

---

**End of Plan.**
