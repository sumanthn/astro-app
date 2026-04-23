"""Deep Lagna (1st house) study — full D1 + D9 treatment of the native.

Used by `vedic analyze-house --house 1 --deep`.
"""
from vedic_llm.models.dossier import NatalDossier
from vedic_llm.prompts.natal import NATAL_SYSTEM_PROMPT


LAGNA_DEEP_USER_TEMPLATE = """
# CHART DOSSIER (Rashi + Navamsa)
<dossier>
{dossier_json}
</dossier>

# TASK

Produce an exhaustive classical analysis of the **Lagna (1st house)** — the native's body, self, vitality, life-direction, overall disposition.

## CHART WEIGHTING — READ THIS FIRST

**The Rashi chart (D1) is PRIMARY.** It carries the full structural verdict on the self. The Navamsa (D9) is a *supplementary cross-check* — it confirms, qualifies, or flags caveats on the D1 reading. **D9 does NOT override D1.** Do not treat D9 dignity shifts as "dramatic reversals" that invalidate D1 conclusions; treat them as modulations or late-life caveats at most.

Allocation of emphasis in this analysis:
- **~75% of reasoning weight** → D1 (sign, lord, aspects, occupants, karakas, yogas, functional natures, triple-lagna from Lagna/Moon/Sun all within D1).
- **~25% of reasoning weight** → D9 as a cross-check (confirm/qualify the D1 reading; flag late-blooming or late-deteriorating planets).
- **Scoring rule:** compute the score from D1 first; then adjust by at most ±1 based on D9. Do NOT let a D9 dignity collapse drag a strong D1 score below 6, nor let a D9 improvement lift a weak D1 score above 6.
- **Portrait rule:** the character signature must read as a portrait of the D1 native. D9 appears only as qualifying sentences, not as a co-portrait.

You are following Parashara's Brihat Parashara Hora Shastra supplemented by Phaladeepika, Saravali, and Jataka Parijata. Every claim must be grounded in a dossier fact using `[fact: <dossier_path>]` (e.g. `[fact: planets.Mars.natural_dignity=Enemy]`). No fact, no claim.

# COVERAGE — every section below must be addressed

## Section A — D1 Lagna itself

A1. **Sign** — name, element (fire/earth/air/water), modality (movable/fixed/dual), gender (male/female), polarity, general temperament Parashara assigns to this sign rising.
A2. **Rising degree** — early (0-10°), middle (10-20°), or late (20-30°)? If within 1° of a sign boundary, flag as sandhi (transition degree, destabilising).
A3. **Ascendant Nakshatra + pada** `[fact: ascendant.nakshatra]` `[fact: ascendant.pada]` — its deity, shakti, symbol, and what this specific nakshatra imprints on the personality.
A4. **Nakshatra lord placement** — where the nakshatra lord sits in D1, its house, dignity, and what themes that lord imports into the self `[fact: ascendant.nakshatra_lord*]`.
A5. **Kartari check** — is the 1st hemmed by malefics (papa kartari) or benefics (shubha kartari)? `[fact: ascendant.is_hemmed_by_malefics]` `[fact: ascendant.is_hemmed_by_benefics]`.
A6. **Occupants** — any planets physically in the 1st? For each: natural nature, dignity, combined AND natural dignity, houses ruled (theme imports), aspects cast from Lagna. An empty Lagna is not weak — shifts weight to lord and aspects.

## Section B — Lagna Lord (full biography)

B1. Sign, degree, nakshatra + pada of the Lagna lord.
B2. House placement — kendra / trikona / dusthana / upachaya? How does this redirect the self's energy?
B3. **BOTH dignities** — `dignity` (combined Panchadha Maitri) AND `natural_dignity`. When natural is worse than combined, state the gap and treat the natural reading as a latent weakness the native feels (the combined scheme is theoretically correct but natural dignity is more experientially accurate).
B4. Retrograde, combust, fast/slow (speed), conjunctions, Graha Yuddha if any.
B5. Aspects cast BY the Lagna lord — which houses does it nourish?
B6. Aspects RECEIVED by the Lagna lord — who influences the self's ruler?
B7. Does the Lagna lord aspect back on the Lagna itself? (Major strengthener when it does.)
B8. Nakshatra lord of the Lagna lord — where does that planet sit, what does it pull in?
B9. Functional nature of the Lagna lord for this ascendant `[fact: functional_natures.<Planet>]`.

## Section C — Aspects on the Lagna

For EACH planet in `houses.1.aspected_by` list its:
- Natural nature (benefic/malefic)
- Dignity (both combined and natural)
- Functional nature for this ascendant
- Houses it rules (what themes it injects into the self)
- Whether its aspect is typically considered protective, afflicting, or mixed by classical texts
Then distinguish the DOMINANT aspectual influence on the body/self.

## Section D — Natural karakas of the 1st House

D1. **Sun** (karaka of self, vitality, soul) — D1 sign, house, dignity, conjunctions, aspects, retrograde/combust. How strong is the vitality significator?
D2. **Moon** (mental/emotional foundation) — D1 sign, house, dignity, nakshatra. Is Moon waxing or waning? Kemadruma / Sunapha / Anapha / Durudhara yogas active?
D3. **Mars** (physical body, vigor) — D1 status.
D4. **Ascendant** (Lagna itself as a point) — rising sign nakshatra lord's placement.

## Section E — Cross-check: Chandra Lagna (Moon as 1st)

Using `chandra_lagna.planet_houses` — where does each planet fall when Moon's sign is the 1st house? Report:
- Which planets are in 1st, 4th, 7th, 10th from Moon (kendras)
- Which are in 6th, 8th, 12th from Moon (dusthanas)
- Is the Moon's 1st hemmed (Kemadruma / Sunapha / Anapha / Durudhara)?
Why this matters: traditional Parashari reads the chart three times — from Lagna, Moon, Sun. The self/body is re-assessed from Moon as a "mind's view" of the same themes.

## Section F — Cross-check: Surya Lagna (Sun as 1st)

Using `surya_lagna.planet_houses` — same analysis with Sun as 1st house. This gives the "soul's view" of the self.

## Section G — D9 cross-check (supplementary, not equal weight)

Keep this section tight. D9 is used here to either CONFIRM or QUALIFY the D1 verdict, not to rewrite it. Length: roughly half of Sections A and B.

G1. **D9 Lagna sign and lord** `[fact: d9_summary.ascendant]` — brief note on whether D9 lagna's temperament aligns with or contrasts D1 lagna.
G2. **D1 Lagna lord's placement in D9** `[fact: d9_summary.d1_lagna_lord_in_d9]` — one concise paragraph. If in kendra/trikona in D9 = D1 verdict is confirmed. If in D9 dusthana = D1 promise carries a caveat (late struggles, hidden tests) — but the D1 score still stands.
G3. **Karakamsha** `[fact: d9_summary.karakamsha]` — one paragraph on the soul's evolutionary theme (supplementary to the Atmakaraka reading already done in D1).
G4. **Vargottama planets** `[fact: vargottama_planets]` — these REINFORCE their D1 reading (structural pillars). Name them briefly.
G5. **D9 as QUALIFIER** — list at most 3-5 notable dignity shifts D1→D9 and frame each as a *qualification* of the D1 reading, NOT as a reversal. Template: "D1 says X [primary]; D9 adds the caveat that Y [secondary]." Dignity drops = late-life caveat or hidden brittleness; dignity rises = late-blooming. **Do not use language like "dramatic reversal," "façade," or "severe collapse."** D9 qualifies; it does not invalidate.

## Section H — Functional benefics/malefics roll-call for this ascendant

For each of the 9 planets, state its functional nature `[fact: functional_natures.<planet>]` with the classical reasoning (which houses it rules, trikona/kendra/dusthana logic, kendradhipati dosha, lagna lord exception, etc.). Then identify the native's "friends" and "enemies" at the functional level.

## Section I — Yogas touching the self

From `dossier.yogas`, extract every yoga where the 1st house or its lord or the Moon/Sun/Atmakaraka participates. For each: functional or cosmetic? When it activates? What lived reality does it produce?

## Section J — Neecha Bhanga / Vipareeta / special cancellations

Check every debilitated planet for Neecha Bhanga. Check every dusthana-lord placement for Vipareeta Raja Yoga potential. Check combustion effects on functional benefics/malefics. Check retrograde planets — retrograde benefics strengthen, retrograde malefics can be unpredictable.

## Section K — SYNTHESIS (D1-led)

The synthesis MUST be a portrait of the D1 native. D9 appears only in K5 (inner tension caveats) and in "contingent" themes. The character signature is a D1 portrait.

K1. **Score 1-10** — arrive at the score from D1 structure only, then state the final score after applying at most ±1 from D9. Justify in D1 terms first, D9 caveats second.
K2. **The body** — physique, vitality, health tendencies (from Lagna sign + Mars + Sun + 1st lord's afflictions).
K3. **The temperament** — emotional texture, mental operating style (from Moon + Mercury + nakshatra lord).
K4. **The will / self-direction** — what drives this person, where their agency flows (from Sun + Lagna lord + Atmakaraka).
K5. **The inner tension** — where the self experiences chronic friction (natural dignity gaps, D1/D9 conflicts, afflicted karakas).
K6. **The structural pillars** — what the native can ALWAYS rely on (vargottama, yogakarakas, exalted functional benefics).
K7. **Promised vs Contingent** — what is baked into the self regardless of timing, and what only activates under specific dasha/transit conditions.
K8. **Character signature** — 3-4 paragraph portrait integrating everything.

# REASONING RULES

1. Cite every claim with `[fact: <dossier_path>]`.
2. When a general rule and a specific reading conflict, explicitly state both: "Parashara says X in general. In THIS chart, because Y, the effect is Z."
3. Separate D1 claims from D9 claims; do not silently merge them. **D1 claims lead; D9 qualifies.**
4. When the dossier's combined `dignity` is mild but `natural_dignity` is harsh, name the gap explicitly and weight the natural reading as lived experience.
4b. **Never let a D9 reading dominate a D1 conclusion.** Language like "D9 invalidates," "façade," or "dramatic reversal" is forbidden. D9 can modulate, qualify, add caveats, or confirm — never override.
5. No boilerplate caveats about astrology. Technical analysis only.
6. Neutral descriptive tone. No fortune-telling ("you will"). Use "this chart indicates a tendency toward…".
7. If a fact is not in the dossier, say "Dossier does not specify" and move on.

# OUTPUT FORMAT — valid JSON only

{{
  "section_a_d1_lagna": {{
    "sign_temperament": "...",
    "rising_degree_note": "...",
    "nakshatra_reading": "...",
    "nakshatra_lord_placement": "...",
    "kartari": "...",
    "occupants": "..."
  }},
  "section_b_lagna_lord": {{
    "identification": "...",
    "house_placement": "...",
    "dignity_analysis": "...",
    "retrograde_combust_speed": "...",
    "aspects_cast": "...",
    "aspects_received": "...",
    "aspects_back_on_lagna": "...",
    "nakshatra_lord_of_lagna_lord": "...",
    "functional_nature": "..."
  }},
  "section_c_aspects_on_lagna": [
    {{"planet": "...", "nature": "...", "dignities": "...", "effect_on_self": "..."}}
  ],
  "section_d_karakas": {{
    "sun": "...",
    "moon": "...",
    "mars": "...",
    "lagna_point": "..."
  }},
  "section_e_chandra_lagna": {{
    "kendras_from_moon": "...",
    "dusthanas_from_moon": "...",
    "moon_yogas": "...",
    "reading": "..."
  }},
  "section_f_surya_lagna": {{
    "kendras_from_sun": "...",
    "dusthanas_from_sun": "...",
    "reading": "..."
  }},
  "section_g_d9": {{
    "d9_ascendant_and_lord": "...",
    "d9_asc_lord_placement": "...",
    "d1_lagna_lord_in_d9": "...",
    "karakamsha": "...",
    "vargottama_reading": "...",
    "d9_first_house": "...",
    "d9_moon_and_sun": "...",
    "dignity_shifts_d1_to_d9": [
      {{"planet": "...", "d1_dignity": "...", "d9_dignity": "...", "implication": "..."}}
    ]
  }},
  "section_h_functional_roll_call": {{
    "Sun": "...",
    "Moon": "...",
    "Mars": "...",
    "Mercury": "...",
    "Jupiter": "...",
    "Venus": "...",
    "Saturn": "...",
    "Rahu": "...",
    "Ketu": "...",
    "functional_friends": ["..."],
    "functional_enemies": ["..."]
  }},
  "section_i_yogas": [
    {{"yoga": "...", "functional": true, "when_active": "...", "lived_effect": "..."}}
  ],
  "section_j_special_cancellations": {{
    "neecha_bhanga_checks": "...",
    "vipareeta_raja_yoga_checks": "...",
    "combustion_effects": "...",
    "retrograde_effects": "..."
  }},
  "section_k_synthesis": {{
    "score": <1-10>,
    "body": "...",
    "temperament": "...",
    "will_and_self_direction": "...",
    "inner_tension": "...",
    "structural_pillars": "...",
    "promised": ["..."],
    "contingent": ["..."],
    "character_signature": "3-4 paragraph portrait"
  }}
}}
""".strip()


def build_lagna_deep_prompt(dossier: NatalDossier) -> tuple[str, str]:
    """Return (system, user) prompts for the deep Lagna study."""
    user = LAGNA_DEEP_USER_TEMPLATE.format(
        dossier_json=dossier.model_dump_json(indent=2),
    )
    return NATAL_SYSTEM_PROMPT, user
