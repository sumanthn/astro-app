"""Focused single-house natal prompt — analyses one house at a time."""
from vedic_llm.models.dossier import NatalDossier
from vedic_llm.prompts.natal import NATAL_SYSTEM_PROMPT


HOUSE_TOPIC = {
    1: "THE NATIVE — body, self, vitality, life-direction, overall disposition",
    2: "Wealth, family of origin, speech, food, accumulated resources",
    3: "Courage, siblings, skills, short journeys, self-effort",
    4: "Mother, home, inner peace, land/vehicles, emotional foundation",
    5: "Intelligence, children, creativity, purva-punya, romance",
    6: "Enemies, disease, debts, service, daily work",
    7: "Spouse, partnerships, public, market",
    8: "Longevity, transformations, hidden matters, inheritance, occult",
    9: "Dharma, father, guru, fortune, higher learning",
    10: "Career, status, public action, authority",
    11: "Gains, elder siblings, networks, fulfilment of desires",
    12: "Losses, moksha, foreign lands, bed-pleasures, expenditures",
}


def build_house_prompt(dossier: NatalDossier, house_num: int) -> tuple[str, str]:
    """Return (system, user) prompts for a focused single-house reading."""
    topic = HOUSE_TOPIC[house_num]
    user = f"""
# CHART DOSSIER
<dossier>
{dossier.model_dump_json(indent=2)}
</dossier>

# TASK

Perform a focused natal analysis of **House {house_num}** only — {topic}.

**CHART WEIGHTING:** The Rashi (D1) is primary. D9 is a supplementary cross-check only — use it to confirm or qualify D1 findings, never to override them. ~75% of reasoning should be D1-grounded; the D9 cross-check (Step 7) is a concise qualifier, not a co-equal layer.

Use the classical 8-step method. Do not combine steps. Do not skip steps. Cite each claim with `[fact: <dossier_path>]` (e.g. `[fact: houses.1.lord=Mars]`).

## The 8-Step House Method

1. **House & Lord Identification** — the sign on the house and its lord (Bhavesh).
2. **Lord's Placement** — which house does the lord occupy? Kendra / trikona / dusthana / upachaya? How does this redirect the house's energy?
3. **Lord's Dignity** — exalted / moolatrikona / own / friend / neutral / enemy / debilitated; retrograde; combust. If debilitated, check for Neecha Bhanga. **IMPORTANT:** the dossier exposes BOTH `dignity` (Parashara's combined Panchadha Maitri = natural + temporary) AND `natural_dignity` (natural friendship only). When `natural_dignity` is worse than `dignity` (e.g. natural Enemy softened to combined Neutral via temporary friendship), state the gap explicitly: the combined scheme is classically correct, but the natural reading often predicts practical experience better — treat it as a latent weakness the native actually feels. Use the same rule for planetary occupants in Step 4.
4. **Occupants** — for each: natural nature (benefic/malefic), dignity, and which other houses it rules (it imports those themes).
5. **Aspects** — which planets aspect this house? Benefic vs malefic. Does the lord aspect back on its own house?
6. **Karaka** — natural significator of this house. Is it strong or afflicted?
7. **D9 Cross-Check** (brief — 2-3 sentences max) — the lord's Navamsa sign & dignity. D9 qualifies the D1 verdict; it does not veto or replace it.
8. **Synthesis** — score 1-10, 2-3 dominant themes, distinguish PROMISED (structural) from CONTINGENT (needs dasha/transit activation).

## Additional context for House {house_num}
{_house_extras(house_num)}

## REASONING RULES
- Cite every claim with `[fact: <dossier_path>]`. No citation = don't make the claim.
- If D1 and D9 conflict, state the conflict explicitly and how classical texts resolve it here.
- Separate general rule ("Parashara says X") from the specific reading ("in THIS chart, Y, so Z").
- If a fact is absent from the dossier, say "Dossier does not specify" and move on.
- Neutral, technical tone. No fortune-telling phrasing. No disclaimers about astrology.

## OUTPUT FORMAT

Return ONLY valid JSON in this schema:

{{
  "house": {house_num},
  "topic": "{topic}",
  "score": <1-10>,
  "eight_step": {{
    "step1_identification": "...",
    "step2_lord_placement": "...",
    "step3_lord_dignity": "...",
    "step4_occupants": "...",
    "step5_aspects": "...",
    "step6_karaka": "...",
    "step7_d9_crosscheck": "...",
    "step8_synthesis": "..."
  }},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "promised_themes": ["structural potential — 3-5 items"],
  "contingent_themes": ["need dasha/transit activation — 2-4 items"],
  "portrait": "2-3 paragraph character/life portrait of what this house expresses in the native"
}}
""".strip()
    return NATAL_SYSTEM_PROMPT, user


def _house_extras(house_num: int) -> str:
    """Extra instructions specific to each house — focus areas beyond the 8-step base."""
    if house_num == 1:
        return (
            "Since this is the Lagna, also address: (a) the Moon's condition as the "
            "emotional/mental foundation, (b) the Sun's condition as vitality and soul, "
            "(c) any vargottama planets and why they are structural pillars for this "
            "native, (d) functional benefics vs functional malefics for this ascendant, "
            "(e) the Atmakaraka and what its placement says about the soul's agenda."
        )
    return "Focus the reading on what the dossier reveals for this specific house only."
