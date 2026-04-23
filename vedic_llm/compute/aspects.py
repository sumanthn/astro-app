"""Graha Drishti — planetary aspects by house count (Vedic / Parashari system)."""

from vedic_llm.models.enums import Planet
from vedic_llm.models.chart import Chart


# ---------------------------------------------------------------------------
# Aspect rules
# ---------------------------------------------------------------------------
# All planets cast a full aspect on the 7th house from their position.
# Mars additionally aspects the 4th and 8th houses.
# Jupiter additionally aspects the 5th and 9th houses.
# Saturn additionally aspects the 3rd and 10th houses.
# Rahu/Ketu aspect the 5th, 7th, and 9th houses (per Phaladeepika).
# ---------------------------------------------------------------------------

_SPECIAL_ASPECTS: dict[Planet, list[int]] = {
    Planet.MARS:    [4, 8],
    Planet.JUPITER: [5, 9],
    Planet.SATURN:  [3, 10],
    Planet.RAHU:    [5, 9],   # 7th is already universal
    Planet.KETU:    [5, 9],
}


def _house_offset(from_house: int, offset: int) -> int:
    """Return the house number that is *offset* houses away from *from_house*.

    Both *from_house* and the result are in the range 1-12.
    An offset of 1 means the same house; offset of 7 means the 7th from it.
    """
    return ((from_house - 1 + offset - 1) % 12) + 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def aspects_cast_by(planet: Planet, from_house: int) -> list[int]:
    """Return the list of house numbers (1-12) aspected by *planet* sitting
    in *from_house*.

    Every planet aspects the 7th house from itself.  Mars, Jupiter, Saturn,
    Rahu, and Ketu have additional special aspects.
    """
    aspected: list[int] = [_house_offset(from_house, 7)]

    for offset in _SPECIAL_ASPECTS.get(planet, []):
        h = _house_offset(from_house, offset)
        if h not in aspected:
            aspected.append(h)

    return sorted(aspected)


def aspects_on_house(chart: Chart, house: int) -> list[Planet]:
    """Return every planet that casts a Graha Drishti on *house*."""
    result: list[Planet] = []
    for planet, state in chart.planets.items():
        aspected_houses = aspects_cast_by(planet, state.house)
        if house in aspected_houses:
            result.append(planet)
    return result


def aspects_on_planet(chart: Chart, target: Planet) -> list[Planet]:
    """Return every planet that aspects the house where *target* is placed.

    The target planet itself is excluded from the result.
    """
    if target not in chart.planets:
        return []
    target_house = chart.planets[target].house
    return [p for p in aspects_on_house(chart, target_house) if p != target]


def populate_house_aspects(chart: Chart) -> None:
    """Fill in the ``aspected_by`` field for every house in the chart.

    Modifies the chart **in place**.
    """
    for house_num in chart.houses:
        chart.houses[house_num].aspected_by = aspects_on_house(chart, house_num)
