"""Dasha analysis prompt — Layer 2: activation window."""


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


def build_dasha_prompt(natal_result: dict, dasha_dossier) -> tuple[str, str]:
    import json
    user = DASHA_USER_PROMPT_TEMPLATE.format(
        natal_analysis_json=json.dumps(natal_result, indent=2),
        dasha_dossier_json=dasha_dossier.model_dump_json(indent=2),
        md_lord=dasha_dossier.current_md.get("lord", ""),
        ad_lord=dasha_dossier.current_ad.get("lord", ""),
        pd_lord=dasha_dossier.current_pd.get("lord", ""),
        ad_end_date=dasha_dossier.current_ad.get("end", ""),
    )
    return DASHA_SYSTEM_PROMPT, user
