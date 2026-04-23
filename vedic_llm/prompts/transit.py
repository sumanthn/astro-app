"""Transit analysis prompt — Layer 3: triggers."""


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


def build_transit_prompt(natal_result: dict, dasha_result: dict, transit_dossier) -> tuple[str, str]:
    import json
    user = TRANSIT_USER_PROMPT_TEMPLATE.format(
        natal_analysis_json=json.dumps(natal_result, indent=2),
        dasha_analysis_json=json.dumps(dasha_result, indent=2),
        transit_dossier_json=transit_dossier.model_dump_json(indent=2),
    )
    return TRANSIT_SYSTEM_PROMPT, user
