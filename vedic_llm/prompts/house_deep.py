"""Deep per-house study — any house 2-12 (house 1 uses lagna.py).

Structure mirrors the Lagna deep prompt: A-K sections, D1-primary, D9 as cross-check.
"""
from vedic_llm.models.dossier import NatalDossier
from vedic_llm.prompts.natal import NATAL_SYSTEM_PROMPT


# Per-house metadata — topic, karakas, classical focus, maraka/dusthana notes.
HOUSE_META: dict[int, dict] = {
    2: {
        "topic": "Wealth (Dhana), family of origin (Kutumba), speech (Vak), face, food, accumulated resources, learning (Vidya)",
        "karakas": ["Jupiter (natural karaka of wealth)", "Mercury (speech)", "Venus (refinement of speech and taste)"],
        "classical_focus": "Saraswati's house — learning, speech, and family inheritance. Also maraka (death-dealing) in Parashari scheme.",
        "special_checks": (
            "2nd is a MARAKA house: planets here — especially the 2nd lord and natural malefics — can threaten "
            "longevity in their dasha. Speech quality is read from the 2nd lord's nakshatra and any afflictions. "
            "Food/taste preferences flow from 2nd sign's nature + occupants. Wealth is read not only from the 2nd "
            "but also from the 11th (gains) and the Dhana Yogas in the dossier."
        ),
        "subhouse_notes": "2nd from Moon = material fulfilment. 2nd from Sun = soul's resources. 2nd from 2nd (= 3rd) = siblings, effort-based income.",
    },
    3: {
        "topic": "Courage (Parakrama), younger siblings, skills, short journeys, self-effort, hands, communication",
        "karakas": ["Mars (courage, effort)", "Mercury (skills, communication)"],
        "classical_focus": "Upachaya + dusthana-lite in some schemes. Malefics here are classically welcomed (they give fighting spirit).",
        "special_checks": (
            "3rd house malefics are FAVOURABLE (reverse of usual rule). Check specifically: siblings' welfare (3rd "
            "lord + Mars), courage levels, skill acquisition, short-travel patterns. The 3rd house is also read for "
            "subordinate effort / self-made success."
        ),
        "subhouse_notes": "3rd from Moon = emotional courage. 3rd from Sun = self-expression energy.",
    },
    4: {
        "topic": "Mother, home, inner peace, land/vehicles, emotional foundation, schooling, happiness (Sukha)",
        "karakas": ["Moon (mother, emotional foundation)", "Mercury (schooling)", "Venus (comforts, vehicles)", "Mars (land, property)"],
        "classical_focus": "The Sukha Bhava — seat of inner contentment. Strength here correlates with psychological security and capacity for peace.",
        "special_checks": (
            "Check Moon's condition FIRST — it is the primary karaka and directly describes the mother and inner "
            "world. Also assess the 4th lord, any planets in the 4th (benefic = happiness, malefic = unrest), and "
            "aspects on the 4th. The Chandra Lagna view is especially important for this house since Moon IS the "
            "karaka."
        ),
        "subhouse_notes": "4th from Moon = mother's mother / inner peace squared. 4th from Sun = soul's foundation.",
    },
    5: {
        "topic": "Intelligence (Buddhi), children (Putra), creativity, Purva Punya (past-life merit), romance, mantra, speculation",
        "karakas": ["Jupiter (children, wisdom, Purva Punya)", "Sun (intelligence, royal favour)", "Mercury (analytical mind)"],
        "classical_focus": "Purva Punya Bhava — stored merit from past lives manifests here. A strong 5th = a fortunate life with natural gifts.",
        "special_checks": (
            "Children indication: 5th lord + Jupiter + any benefic in 5th (afflictions by malefics, esp. Saturn/Rahu, "
            "delay or deny). Intelligence type is read from the 5th sign, 5th lord's sign, and Mercury's state. "
            "Karakamsha (AK's D9 sign) cross-references here because Jaimini uses D9 5th for spiritual vidya."
        ),
        "subhouse_notes": "5th from Moon = emotional creativity/children. 5th from Sun = soul's creative dharma (often what the person ACTUALLY does).",
    },
    6: {
        "topic": "Enemies (Shatru), disease (Roga), debts (Rina), service, daily work, litigation, maternal uncle",
        "karakas": ["Mars (enemies, conflict)", "Saturn (disease, service, chronic afflictions)"],
        "classical_focus": "Dusthana + upachaya. Malefics here produce Vipareeta Raja Yoga potential — enemies become victories.",
        "special_checks": (
            "Vipareeta Raja Yoga: 6th lord in 8 or 12, OR 6th lord conjunct/aspects 8th or 12th lord without being "
            "linked to a benefic — produces dramatic elevation through apparent adversity. Also check for chronic "
            "health tendencies (6th lord + Mars/Saturn). Service-orientation comes from 6th lord's house placement."
        ),
        "subhouse_notes": "6th from Moon = mental enemies/anxieties. 6th from Sun = soul-level enemies (often internal).",
    },
    7: {
        "topic": "Spouse (Kalatra), partnerships, business dealings, public reputation, travel, trade",
        "karakas": ["Venus (spouse for a man, relationship quality)", "Jupiter (husband for a woman, classical)"],
        "classical_focus": "Kendra + maraka. The spouse is read from 7th sign, 7th lord, and Venus/Jupiter condition. 7th house maraka quality activates in its dasha.",
        "special_checks": (
            "Spouse's character: 7th sign + 7th lord's sign + aspects on 7th + Venus (for male natives) / Jupiter "
            "(for female natives classically). Marital happiness: 7th lord's dignity, benefic vs malefic aspects "
            "on 7th, Venus's condition, Navamsa 7th cross-check. Check also for Mangal Dosha (Mars in 1/2/4/7/8/12)."
        ),
        "subhouse_notes": "7th from Moon = public/partnership mind. 7th from Venus = romantic prospects.",
    },
    8: {
        "topic": "Longevity (Ayu), transformations, hidden matters, inheritance, occult, chronic conditions, accidents, research",
        "karakas": ["Saturn (longevity, chronic)", "Rahu (occult, sudden transformations)"],
        "classical_focus": "Ayushsthana — the primary longevity house (with 3rd as Bhadaka). Also Mrityusthana (death-inflicting).",
        "special_checks": (
            "Longevity classical method: combine 8th lord's placement + lagna lord + Saturn + Moon. Check for "
            "alpha/madhya/poorna ayu yogas. Vipareeta Raja Yoga from 8th lord also possible. The 8th is ALSO "
            "the house of research, occult, and hidden knowledge — benefic placement here can mean depth of insight."
        ),
        "subhouse_notes": "8th from Moon = emotional crises. 8th from Sun = soul-level transformations.",
    },
    9: {
        "topic": "Dharma, father (Pitra), guru, fortune (Bhagya), higher learning, long journeys, publishing",
        "karakas": ["Jupiter (guru, dharma, fortune)", "Sun (father)"],
        "classical_focus": "Bhagya Bhava — the most fortunate house. A strong 9th = natural grace and protection.",
        "special_checks": (
            "Father's condition: 9th lord + Sun + 9th sign. Guru/dharma: 9th lord + Jupiter + 9th occupants. "
            "Fortune strength: Lakshmi Yoga (9th lord exalted, moolatrikona, or own sign in kendra/trikona) is "
            "a major Raja Yoga. Long journeys and foreign fortune: 9th + 12th lord interaction."
        ),
        "subhouse_notes": "9th from Moon = emotional dharma. 9th from Sun = soul's dharma path.",
    },
    10: {
        "topic": "Career (Karma), status (Rajya), public action, authority, profession, reputation with superiors",
        "karakas": ["Sun (authority, royal favour)", "Jupiter (wisdom in action)", "Saturn (sustained work)", "Mercury (skilled work)"],
        "classical_focus": "Karma Bhava + strongest kendra. Triple 10th principle: read 10th from Lagna, Moon, AND Sun for a complete career picture.",
        "special_checks": (
            "MANDATORY — read TRIPLE 10TH (from Lagna, Moon, Sun). Also cross-check D10 (Dasamsa) where available. "
            "Career flavour = 10th sign + 10th lord's sign + Amatyakaraka + karakas in 10th. Career events time "
            "from 10th lord's dasha, Saturn/Jupiter transits over 10th, 10th lord's transit."
        ),
        "subhouse_notes": "10th from Moon = public emotional role. 10th from Sun = soul's dharma-in-action (often the true calling).",
    },
    11: {
        "topic": "Gains (Labha), elder siblings, networks, friends, fulfilment of desires, income",
        "karakas": ["Jupiter (gains of wisdom)", "Saturn (gains through effort)"],
        "classical_focus": "Upachaya + the house of all gains. Malefics here are strong; 11th is read as fruit of all other houses' work.",
        "special_checks": (
            "11th lord + planets in 11th + Jupiter's aspect = gain quality. Network/friends: 11th sign + 11th lord "
            "placement. Income sources: 11th from 10th (= 8th) + 11th + 2nd. Fulfilment: 11th lord's strength and "
            "its relation to the Lagna lord."
        ),
        "subhouse_notes": "11th from Moon = emotional/mental gains, social network. 11th from Sun = soul-recognition.",
    },
    12: {
        "topic": "Losses (Vyaya), moksha, foreign lands, bed-pleasures, expenditure, hidden enemies, isolation, spirituality",
        "karakas": ["Saturn (losses, isolation)", "Ketu (moksha, detachment)"],
        "classical_focus": "Dusthana + Mokshasthana. Strong 12th = spiritual attainment. Afflicted 12th = chronic losses or hidden troubles.",
        "special_checks": (
            "Moksha potential: 12th lord + Ketu + Jupiter interaction. Foreign settlement: 12th lord in kendra/trikona "
            "or linked to 9th. Hidden enemies / imprisonment (in extreme cases): 12th occupants + 6th/8th links. "
            "Bed-pleasures (Shayya Sukha): Venus's relation to 12th."
        ),
        "subhouse_notes": "12th from Moon = emotional losses/retreats. 12th from Sun = soul's dissolution / spiritual home.",
    },
}


HOUSE_DEEP_USER_TEMPLATE = """
# CHART DOSSIER (Rashi + Navamsa)
<dossier>
{dossier_json}
</dossier>

# TASK

Produce an exhaustive classical analysis of **House {house_num}** — {topic}.

## CHART WEIGHTING — READ THIS FIRST

**The Rashi chart (D1) is PRIMARY.** It carries the full structural verdict. The Navamsa (D9) is a *supplementary cross-check* — it confirms, qualifies, or flags caveats on the D1 reading. **D9 does NOT override D1.**

- **~75% of reasoning weight** → D1 (sign, lord, aspects, occupants, karakas, yogas, functional natures, Chandra/Surya Lagna views — all within D1).
- **~25% of reasoning weight** → D9 as a cross-check (confirm/qualify, flag late-blooming or late-deteriorating planets).
- **Scoring:** compute from D1 first; adjust at most ±1 from D9.
- **Portrait:** reads as a D1 portrait. D9 appears only as qualifying sentences.

You are following Parashara's Brihat Parashara Hora Shastra supplemented by Phaladeepika, Saravali, and Jataka Parijata. Cite every claim with `[fact: <dossier_path>]`. No fact, no claim.

## House-specific focus

**Classical framing:** {classical_focus}

**Natural karakas of this house:** {karakas_str}

**Special checks for this house:**
{special_checks}

**Subhouse/alternate-lagna notes:** {subhouse_notes}

# COVERAGE — every section below must be addressed

## Section A — D1 House {house_num} itself

A1. **Sign on the house** — name, element, modality, gender, and what these qualities mean for {topic}.
A2. **Degree span** — which portion of the sign is rising on the cusp? (Whole-sign houses use the whole sign; note if any occupants are in sandhi.)
A3. **Occupants** `[fact: houses.{house_num}.occupants]` — for EACH: natural nature, combined AND natural dignity, functional nature for this ascendant, houses ruled (theme imports), aspects cast. Note combustion, retrograde, vargottama status.
A4. **Kartari check** — is the house hemmed by malefics (papa kartari) or benefics (shubha kartari)? `[fact: houses.{house_num}.is_hemmed_by_malefics]` `[fact: houses.{house_num}.is_hemmed_by_benefics]`.
A5. **Nakshatras falling in this house** — which nakshatras span this sign, and their lords. Note any occupant's nakshatra for sub-themes.

## Section B — House {house_num} Lord (full biography)

B1. Lord identity, sign, degree, nakshatra + pada.
B2. House placement — kendra / trikona / dusthana / upachaya? How does this redirect the house's energy?
B3. **BOTH dignities** — combined `dignity` AND `natural_dignity`. When natural is worse than combined, name the gap; it's lived experience.
B4. Retrograde, combust, conjunctions, Graha Yuddha if any.
B5. Aspects cast BY the house lord — which houses does it nourish?
B6. Aspects RECEIVED by the house lord.
B7. Does the house lord aspect back on its own house? (Major strengthener.)
B8. Nakshatra lord of the house lord — where does that planet sit, what does it pull in?
B9. Functional nature of the house lord `[fact: functional_natures.<Planet>]`.

## Section C — Aspects on House {house_num}

For EACH planet in `houses.{house_num}.aspected_by`: natural nature, dignity, functional nature for this ascendant, houses ruled, and whether the aspect is protective / afflicting / mixed for *this specific house topic*. Then state the DOMINANT aspectual influence on {topic}.

## Section D — Natural karakas of house {house_num}

For each karaka listed above ({karakas_str}): D1 sign, house, dignity, conjunctions, aspects, functional nature. How strong is the karaka? A weak karaka undermines this house even if other factors look good.

## Section E — Chandra Lagna view (house {house_num} from Moon)

Using `chandra_lagna.planet_houses` and `chandra_lagna.houses`: which planets fall in the {house_num}th from Moon? What is the sign on the {house_num}th from Moon and its lord? Parashara reads every house twice — once from Lagna, once from Moon. The Moon's view = the mind's lived perception of this house's themes.

## Section F — Surya Lagna view (house {house_num} from Sun)

Using `surya_lagna.planet_houses` and `surya_lagna.houses`: same analysis with Sun as 1st house. The soul's perception of this house.

## Section G — D9 cross-check (supplementary, not equal weight)

Keep this section tight — roughly half of Section B.

G1. **D9 sign on this house from D9 lagna** — brief note (note that D9 houses are numbered from D9 lagna, not the D1 house number; the dossier's `d9_summary.houses.N` uses D9 lagna numbering).
G2. **D1 house {house_num}'s lord placement in D9** — one concise paragraph. Kendra/trikona = D1 verdict confirmed. Dusthana = D1 promise with a caveat. D1 score stands.
G3. **Karakas' D9 state** — briefly note dignity shifts of the karakas for this house. Rises = late-blooming; falls = late-life qualification.
G4. **Vargottama planets touching this house topic** (as occupants, lord, or karaka) — structural pillars; name them.
G5. Frame every finding as "D1 says X [primary]; D9 adds the caveat Y [secondary]." No language like "reversal", "façade", or "collapse".

## Section H — Functional roll-call (abbreviated — just the 3-4 planets most relevant to this house)

From `functional_natures`, state each relevant planet's functional nature and what it means for this house's delivery.

## Section I — Yogas touching House {house_num}

From `dossier.yogas`, extract every yoga where house {house_num}, its lord, its karakas, or its occupants participate. For each: functional or cosmetic? When activates? Lived effect on {topic}?

## Section J — Special cancellations

Neecha Bhanga checks on debilitated planets touching this house. Vipareeta Raja Yoga if dusthana. Combustion, retrograde effects, Graha Yuddha. (Keep concise — only what applies here.)

## Section K — SYNTHESIS (D1-led)

K1. **Score 1-10** — D1-first, then at most ±1 from D9.
K2. **What this house DELIVERS** — the concrete life themes the native will experience around {topic}.
K3. **Strengths** — 4-6 specific items with citations.
K4. **Weaknesses** — 4-6 specific items with citations.
K5. **Promised vs Contingent** — baked-in structural promise vs. what needs dasha/transit activation.
K6. **House portrait** — 2-3 paragraphs, D1-led, reading the native's lived experience of {topic}.

# REASONING RULES

1. Cite every claim with `[fact: <dossier_path>]`.
2. When general rule and specific reading conflict, state both: "Parashara says X. In THIS chart, because Y, it means Z."
3. Separate D1 claims from D9 claims; D1 leads, D9 qualifies.
4. Combined `dignity` vs `natural_dignity`: name any gap; natural dignity = lived experience.
5. **Never let D9 dominate D1.** Language like "D9 invalidates", "façade", "reversal" is forbidden.
6. Neutral technical tone. No fortune-telling. No boilerplate astrology caveats.
7. If a fact is absent from the dossier, say "Dossier does not specify" and move on.

# OUTPUT FORMAT — valid JSON only

{{
  "house": {house_num},
  "topic": "{topic}",
  "section_a_house_itself": {{
    "sign_on_house": "...",
    "degree_span_note": "...",
    "occupants": "...",
    "kartari": "...",
    "nakshatras_in_house": "..."
  }},
  "section_b_house_lord": {{
    "identification": "...",
    "house_placement": "...",
    "dignity_analysis": "...",
    "retrograde_combust": "...",
    "aspects_cast": "...",
    "aspects_received": "...",
    "aspects_back_on_house": "...",
    "nakshatra_lord_of_house_lord": "...",
    "functional_nature": "..."
  }},
  "section_c_aspects_on_house": [
    {{"planet": "...", "nature": "...", "dignities": "...", "effect_on_house_topic": "..."}}
  ],
  "section_d_karakas": {{
    "<karaka_name>": "..."
  }},
  "section_e_chandra_lagna_view": "...",
  "section_f_surya_lagna_view": "...",
  "section_g_d9": {{
    "d9_sign_on_house": "...",
    "house_lord_in_d9": "...",
    "karakas_d9_state": "...",
    "vargottama_pillars": "...",
    "net_qualification": "..."
  }},
  "section_h_functional_roll_call": {{
    "<Planet>": "..."
  }},
  "section_i_yogas": [
    {{"yoga": "...", "functional": true, "when_active": "...", "lived_effect": "..."}}
  ],
  "section_j_special_cancellations": "...",
  "section_k_synthesis": {{
    "score": <1-10>,
    "delivers": "...",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "promised": ["..."],
    "contingent": ["..."],
    "portrait": "2-3 paragraph D1-led portrait of lived experience"
  }}
}}
""".strip()


def build_house_deep_prompt(dossier: NatalDossier, house_num: int) -> tuple[str, str]:
    """Return (system, user) prompts for a deep house analysis (house 2-12).

    House 1 should use `prompts.lagna.build_lagna_deep_prompt` instead — the
    Lagna has additional Bharani-specific structure (nakshatra lord of Lagna,
    Atmakaraka's relation to self, etc.) that this generic template omits.
    """
    if house_num == 1:
        raise ValueError("Use build_lagna_deep_prompt for house 1.")
    if house_num not in HOUSE_META:
        raise ValueError(f"Unknown house {house_num}.")

    meta = HOUSE_META[house_num]
    karakas_str = "; ".join(meta["karakas"])
    user = HOUSE_DEEP_USER_TEMPLATE.format(
        dossier_json=dossier.model_dump_json(indent=2),
        house_num=house_num,
        topic=meta["topic"],
        karakas_str=karakas_str,
        classical_focus=meta["classical_focus"],
        special_checks=meta["special_checks"],
        subhouse_notes=meta["subhouse_notes"],
    )
    return NATAL_SYSTEM_PROMPT, user
