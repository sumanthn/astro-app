"""Classical Yoga detection for Vedic astrology charts."""

from __future__ import annotations

from dataclasses import dataclass, field
from vedic_llm.models.enums import Planet, Sign, Dignity
from vedic_llm.models.chart import Chart
from vedic_llm.compute.dignity import SIGN_LORD, EXALTATION, DEBILITATION
from vedic_llm.compute.aspects import aspects_on_house


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Yoga:
    name: str
    planets_involved: list[Planet] = field(default_factory=list)
    houses_activated: list[int] = field(default_factory=list)
    strength: str = "moderate"   # "strong", "moderate", "weak", "cosmetic"
    reason: str = ""


# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

KENDRAS = (1, 4, 7, 10)
TRIKONAS = (1, 5, 9)
DUSTHANAS = (6, 8, 12)
DHANA_HOUSES = (2, 5, 9, 11)

NATURAL_MALEFICS = {Planet.SUN, Planet.MARS, Planet.SATURN, Planet.RAHU, Planet.KETU}
NATURAL_BENEFICS = {Planet.JUPITER, Planet.VENUS}
# For simplified benefic/malefic classification Moon and Mercury are context-
# dependent.  We treat Jupiter and Venus as definite benefics (as specified)
# and Sun, Mars, Saturn, Rahu, Ketu as definite malefics.


def _house_of(chart: Chart, planet: Planet) -> int | None:
    """Return the house number (1-12) the planet occupies, or None."""
    state = chart.planets.get(planet)
    return state.house if state else None


def _planets_in_house(chart: Chart, house: int) -> list[Planet]:
    """Planets occupying *house*."""
    return chart.planets_in_house(house)


def _house_from(base: int, offset: int) -> int:
    """House that is *offset* houses from *base* (1-indexed, inclusive)."""
    return ((base - 1 + offset - 1) % 12) + 1


def _is_in_kendra_from(house: int, ref_house: int) -> bool:
    """True when *house* is in a kendra (1, 4, 7, 10) counted from *ref_house*."""
    diff = ((house - ref_house) % 12)
    return diff in (0, 3, 6, 9)


def _lords_associated(chart: Chart, lord_a: Planet, lord_b: Planet) -> bool:
    """Two lords are 'associated' when they are conjunct (same house) or
    mutually aspecting (each aspects the other's house)."""
    if lord_a == lord_b:
        return False
    ha = _house_of(chart, lord_a)
    hb = _house_of(chart, lord_b)
    if ha is None or hb is None:
        return False
    # Conjunction
    if ha == hb:
        return True
    # Mutual aspect
    if lord_a in aspects_on_house(chart, hb) or lord_b in aspects_on_house(chart, ha):
        return True
    return False


# ---------------------------------------------------------------------------
# Yoga checks
# ---------------------------------------------------------------------------


def _check_gajakesari(chart: Chart) -> list[Yoga]:
    """Gajakesari Yoga: Jupiter in a kendra (1, 4, 7, 10) from Moon."""
    yogas: list[Yoga] = []
    moon_house = _house_of(chart, Planet.MOON)
    jup_house = _house_of(chart, Planet.JUPITER)
    if moon_house is None or jup_house is None:
        return yogas

    if _is_in_kendra_from(jup_house, moon_house):
        yogas.append(Yoga(
            name="Gajakesari Yoga",
            planets_involved=[Planet.JUPITER, Planet.MOON],
            houses_activated=[moon_house, jup_house],
            strength="strong",
            reason=(
                f"Jupiter in house {jup_house} is in a kendra from "
                f"Moon in house {moon_house}."
            ),
        ))
    return yogas


def _check_raja_yogas(chart: Chart) -> list[Yoga]:
    """Raja Yoga: lord of a kendra conjunct with or aspecting lord of a
    trikona (excluding the 1st house paired with itself, since house 1 is
    both kendra and trikona)."""
    yogas: list[Yoga] = []
    seen_pairs: set[tuple[Planet, Planet]] = set()

    for k in KENDRAS:
        for t in TRIKONAS:
            if k == t:
                continue  # house 1 is both kendra and trikona
            kl = chart.lord_of(k)
            tl = chart.lord_of(t)
            if kl == tl:
                # Same planet lords both — yoga still forms (it lords a
                # kendra and a trikona simultaneously).
                h = _house_of(chart, kl)
                if h is None:
                    continue
                pair = (kl, tl)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                yogas.append(Yoga(
                    name="Raja Yoga",
                    planets_involved=[kl],
                    houses_activated=[k, t],
                    strength="strong",
                    reason=(
                        f"{kl.value} lords both kendra {k} and trikona {t}."
                    ),
                ))
                continue

            pair = tuple(sorted((kl, tl), key=lambda p: p.value))
            if pair in seen_pairs:
                continue

            if _lords_associated(chart, kl, tl):
                seen_pairs.add(pair)
                kl_h = _house_of(chart, kl)
                tl_h = _house_of(chart, tl)
                houses = [h for h in (k, t, kl_h, tl_h) if h is not None]
                yogas.append(Yoga(
                    name="Raja Yoga",
                    planets_involved=[kl, tl],
                    houses_activated=sorted(set(houses)),
                    strength="strong",
                    reason=(
                        f"Kendra lord {kl.value} (house {k}) associated "
                        f"with trikona lord {tl.value} (house {t})."
                    ),
                ))
    return yogas


def _check_dhana_yogas(chart: Chart) -> list[Yoga]:
    """Dhana Yoga: lords of houses 2, 5, 9, 11 associated (same house or
    mutual aspect) with each other."""
    yogas: list[Yoga] = []
    seen_pairs: set[tuple[Planet, Planet]] = set()
    dhana_lords = {h: chart.lord_of(h) for h in DHANA_HOUSES}

    for h1 in DHANA_HOUSES:
        for h2 in DHANA_HOUSES:
            if h2 <= h1:
                continue
            l1 = dhana_lords[h1]
            l2 = dhana_lords[h2]
            pair = tuple(sorted((l1, l2), key=lambda p: p.value))
            if pair in seen_pairs:
                continue
            if _lords_associated(chart, l1, l2):
                seen_pairs.add(pair)
                l1_h = _house_of(chart, l1)
                l2_h = _house_of(chart, l2)
                houses = [h for h in (h1, h2, l1_h, l2_h) if h is not None]
                yogas.append(Yoga(
                    name="Dhana Yoga",
                    planets_involved=[l1, l2],
                    houses_activated=sorted(set(houses)),
                    strength="moderate",
                    reason=(
                        f"Lord of {h1} ({l1.value}) associated with "
                        f"lord of {h2} ({l2.value})."
                    ),
                ))
    return yogas


def _check_neecha_bhanga(chart: Chart) -> list[Yoga]:
    """Neecha Bhanga Raja Yoga: a debilitated planet whose:
      (a) dispositor (lord of the sign it occupies) is in a kendra from
          the lagna (house 1), OR
      (b) the planet that gets exalted in the debilitated planet's current
          sign is in a kendra from lagna.
    """
    yogas: list[Yoga] = []
    lagna_house = 1

    # Build reverse map: sign -> planet exalted there
    exalted_in_sign: dict[Sign, Planet] = {}
    for p, (s, _) in EXALTATION.items():
        exalted_in_sign[s] = p

    for planet, state in chart.planets.items():
        if state.dignity != Dignity.DEBILITATED:
            continue

        planet_house = state.house
        dispositor = SIGN_LORD.get(state.sign)

        # Condition (a): dispositor in kendra from lagna
        condition_a = False
        if dispositor is not None:
            disp_house = _house_of(chart, dispositor)
            if disp_house is not None and _is_in_kendra_from(disp_house, lagna_house):
                condition_a = True

        # Condition (b): planet exalted in that sign is in kendra
        condition_b = False
        exalted_planet = exalted_in_sign.get(state.sign)
        if exalted_planet is not None and exalted_planet != planet:
            ex_house = _house_of(chart, exalted_planet)
            if ex_house is not None and _is_in_kendra_from(ex_house, lagna_house):
                condition_b = True

        if condition_a or condition_b:
            involved = [planet]
            reason_parts: list[str] = [
                f"{planet.value} is debilitated in {state.sign.name} (house {planet_house})."
            ]
            if condition_a and dispositor is not None:
                involved.append(dispositor)
                disp_house = _house_of(chart, dispositor)
                reason_parts.append(
                    f"Dispositor {dispositor.value} is in kendra "
                    f"(house {disp_house}) from lagna."
                )
            if condition_b and exalted_planet is not None:
                if exalted_planet not in involved:
                    involved.append(exalted_planet)
                ex_house = _house_of(chart, exalted_planet)
                reason_parts.append(
                    f"{exalted_planet.value} (exalted in {state.sign.name}) "
                    f"is in kendra (house {ex_house}) from lagna."
                )

            yogas.append(Yoga(
                name="Neecha Bhanga Raja Yoga",
                planets_involved=involved,
                houses_activated=[planet_house],
                strength="strong",
                reason=" ".join(reason_parts),
            ))
    return yogas


def _check_vipareeta_raja(chart: Chart) -> list[Yoga]:
    """Vipareeta Raja Yoga: lord of 6th, 8th, or 12th placed in another of
    these dusthana houses (6, 8, 12)."""
    yogas: list[Yoga] = []
    for src in DUSTHANAS:
        lord = chart.lord_of(src)
        lord_house = _house_of(chart, lord)
        if lord_house is None:
            continue
        if lord_house in DUSTHANAS and lord_house != src:
            yogas.append(Yoga(
                name="Vipareeta Raja Yoga",
                planets_involved=[lord],
                houses_activated=[src, lord_house],
                strength="moderate",
                reason=(
                    f"Lord of dusthana {src} ({lord.value}) placed in "
                    f"dusthana {lord_house}."
                ),
            ))
    return yogas


def _check_budhaditya(chart: Chart) -> list[Yoga]:
    """Budhaditya Yoga: Sun and Mercury in the same house."""
    yogas: list[Yoga] = []
    sun_h = _house_of(chart, Planet.SUN)
    mer_h = _house_of(chart, Planet.MERCURY)
    if sun_h is not None and mer_h is not None and sun_h == mer_h:
        yogas.append(Yoga(
            name="Budhaditya Yoga",
            planets_involved=[Planet.SUN, Planet.MERCURY],
            houses_activated=[sun_h],
            strength="moderate",
            reason=f"Sun and Mercury conjunct in house {sun_h}.",
        ))
    return yogas


def _check_chandra_mangala(chart: Chart) -> list[Yoga]:
    """Chandra-Mangala Yoga: Moon and Mars in the same house."""
    yogas: list[Yoga] = []
    moon_h = _house_of(chart, Planet.MOON)
    mars_h = _house_of(chart, Planet.MARS)
    if moon_h is not None and mars_h is not None and moon_h == mars_h:
        yogas.append(Yoga(
            name="Chandra-Mangala Yoga",
            planets_involved=[Planet.MOON, Planet.MARS],
            houses_activated=[moon_h],
            strength="moderate",
            reason=f"Moon and Mars conjunct in house {moon_h}.",
        ))
    return yogas


def _check_kemadruma(chart: Chart) -> list[Yoga]:
    """Kemadruma Yoga: no planets (except Sun, Rahu, Ketu) in the 2nd or
    12th house from Moon.

    This is an inauspicious yoga indicating poverty / hardship.
    """
    yogas: list[Yoga] = []
    moon_h = _house_of(chart, Planet.MOON)
    if moon_h is None:
        return yogas

    excluded = {Planet.SUN, Planet.RAHU, Planet.KETU, Planet.MOON}
    h2 = _house_from(moon_h, 2)
    h12 = _house_from(moon_h, 12)

    planets_2 = [p for p in _planets_in_house(chart, h2) if p not in excluded]
    planets_12 = [p for p in _planets_in_house(chart, h12) if p not in excluded]

    if not planets_2 and not planets_12:
        yogas.append(Yoga(
            name="Kemadruma Yoga",
            planets_involved=[Planet.MOON],
            houses_activated=[moon_h, h2, h12],
            strength="weak",
            reason=(
                f"No planets (excluding Sun, Rahu, Ketu) in houses "
                f"{h2} (2nd) or {h12} (12th) from Moon in house {moon_h}."
            ),
        ))
    return yogas


def _check_kala_sarpa(chart: Chart) -> list[Yoga]:
    """Kala Sarpa Yoga: all seven planets (Sun through Saturn) are
    hemmed between Rahu and Ketu (i.e., they all lie on one side of
    the Rahu-Ketu axis)."""
    yogas: list[Yoga] = []
    rahu_h = _house_of(chart, Planet.RAHU)
    ketu_h = _house_of(chart, Planet.KETU)
    if rahu_h is None or ketu_h is None:
        return yogas

    seven = [
        Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY,
        Planet.JUPITER, Planet.VENUS, Planet.SATURN,
    ]

    # Check if all planets are between Rahu -> Ketu (going forward in
    # house order).  We test both directions and accept either.
    def _all_between(start: int, end: int) -> bool:
        """True when every planet house lies strictly between *start* and
        *end* going clockwise (houses increase 1..12..1)."""
        for p in seven:
            ph = _house_of(chart, p)
            if ph is None:
                return False
            if ph == start or ph == end:
                # Planet on the axis — some traditions still count this.
                # We accept it as inside.
                continue
            # Clockwise distance from start to ph
            dist_p = (ph - start) % 12
            dist_end = (end - start) % 12
            if dist_end == 0:
                dist_end = 12
            if dist_p == 0 or dist_p >= dist_end:
                return False
        return True

    if _all_between(rahu_h, ketu_h) or _all_between(ketu_h, rahu_h):
        yogas.append(Yoga(
            name="Kala Sarpa Yoga",
            planets_involved=[Planet.RAHU, Planet.KETU] + seven,
            houses_activated=[rahu_h, ketu_h],
            strength="strong",
            reason=(
                f"All seven planets are hemmed between Rahu (house "
                f"{rahu_h}) and Ketu (house {ketu_h})."
            ),
        ))
    return yogas


# ---------------------------------------------------------------------------
# Master detector
# ---------------------------------------------------------------------------


def detect_yogas(chart: Chart) -> list[Yoga]:
    """Detect all applicable classical yogas in the chart."""
    yogas: list[Yoga] = []
    yogas.extend(_check_gajakesari(chart))
    yogas.extend(_check_raja_yogas(chart))
    yogas.extend(_check_dhana_yogas(chart))
    yogas.extend(_check_neecha_bhanga(chart))
    yogas.extend(_check_vipareeta_raja(chart))
    yogas.extend(_check_budhaditya(chart))
    yogas.extend(_check_chandra_mangala(chart))
    yogas.extend(_check_kemadruma(chart))
    yogas.extend(_check_kala_sarpa(chart))
    return yogas


# ---------------------------------------------------------------------------
# Affliction helpers
# ---------------------------------------------------------------------------


def papa_kartari(chart: Chart, target_house: int) -> bool:
    """Return True when natural malefics (Sun, Mars, Saturn, Rahu, Ketu)
    occupy BOTH the 12th and 2nd houses from *target_house*
    (Papa Kartari Yoga — hemming by malefics).
    """
    h_prev = _house_from(target_house, 12)   # 12th from target
    h_next = _house_from(target_house, 2)    # 2nd from target

    malefic_prev = any(p in NATURAL_MALEFICS for p in _planets_in_house(chart, h_prev))
    malefic_next = any(p in NATURAL_MALEFICS for p in _planets_in_house(chart, h_next))

    return malefic_prev and malefic_next


def shubha_kartari(chart: Chart, target_house: int) -> bool:
    """Return True when natural benefics (Jupiter, Venus — and, for a
    simplified model, only these two definite benefics) occupy BOTH the
    12th and 2nd houses from *target_house*
    (Shubha Kartari Yoga — hemming by benefics).
    """
    h_prev = _house_from(target_house, 12)
    h_next = _house_from(target_house, 2)

    benefic_prev = any(p in NATURAL_BENEFICS for p in _planets_in_house(chart, h_prev))
    benefic_next = any(p in NATURAL_BENEFICS for p in _planets_in_house(chart, h_next))

    return benefic_prev and benefic_next


def planetary_war(chart: Chart) -> list[tuple[Planet, Planet, Planet]]:
    """Detect planetary wars: two non-luminary, non-shadow planets within
    1 degree of each other.

    Returns a list of ``(planet_1, planet_2, winner)`` tuples.
    The winner is the planet with the **lower** longitude (ahead in the
    zodiac).  Sun, Moon, Rahu, and Ketu are excluded.
    """
    excluded = {Planet.SUN, Planet.MOON, Planet.RAHU, Planet.KETU}
    eligible = [
        (p, s) for p, s in chart.planets.items() if p not in excluded
    ]

    wars: list[tuple[Planet, Planet, Planet]] = []
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            p1, s1 = eligible[i]
            p2, s2 = eligible[j]
            diff = abs(s1.longitude - s2.longitude)
            # Handle wrap-around at 360 degrees
            if diff > 180:
                diff = 360 - diff
            if diff <= 1.0:
                winner = p1 if s1.longitude <= s2.longitude else p2
                wars.append((p1, p2, winner))
    return wars
