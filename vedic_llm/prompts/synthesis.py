"""Synthesis prompt — Final integrated reading."""


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


def build_synthesis_prompt(natal_result: dict, dasha_result: dict, transit_result: dict) -> tuple[str, str]:
    import json
    user = SYNTHESIS_USER_PROMPT_TEMPLATE.format(
        natal_analysis_json=json.dumps(natal_result, indent=2),
        dasha_analysis_json=json.dumps(dasha_result, indent=2),
        transit_analysis_json=json.dumps(transit_result, indent=2),
    )
    return SYNTHESIS_SYSTEM_PROMPT, user
