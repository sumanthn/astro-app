"""Career-specific analysis prompt."""


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


def build_career_prompt(
    natal_result: dict,
    dasha_result: dict,
    transit_result: dict,
    d10_dossier,
) -> tuple[str, str]:
    import json
    user = CAREER_USER_PROMPT_TEMPLATE.format(
        natal_analysis_json=json.dumps(natal_result, indent=2),
        dasha_analysis_json=json.dumps(dasha_result, indent=2),
        transit_analysis_json=json.dumps(transit_result, indent=2),
        d10_dossier_json=d10_dossier.model_dump_json(indent=2) if hasattr(d10_dossier, 'model_dump_json') else json.dumps(d10_dossier, indent=2),
    )
    return CAREER_SYSTEM_PROMPT, user
