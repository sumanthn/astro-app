"""Natal analysis prompt — Layer 1: baseline potential."""
from vedic_llm.models.dossier import NatalDossier


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
