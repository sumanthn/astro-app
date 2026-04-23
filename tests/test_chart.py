"""Test chart building against known fixtures."""
import yaml
import pytest
from pathlib import Path
from datetime import datetime
from dateutil import tz

from vedic_llm.models.chart import BirthData
from vedic_llm.compute.chart import build_d1_chart, build_d9_chart


FIXTURES_PATH = Path(__file__).parent / "fixtures" / "charts.yaml"


def load_fixtures():
    with open(FIXTURES_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(params=load_fixtures(), ids=lambda f: f["name"])
def chart_fixture(request):
    return request.param


def _make_birth(fixture) -> BirthData:
    dt_local = datetime.strptime(fixture["datetime_local"], "%Y-%m-%d %H:%M:%S")
    local_tz = tz.gettz(fixture["timezone"])
    dt_local = dt_local.replace(tzinfo=local_tz)
    dt_utc = dt_local.astimezone(tz.UTC)
    return BirthData(
        datetime_utc=dt_utc,
        latitude=fixture["latitude"],
        longitude=fixture["longitude"],
        timezone=fixture["timezone"],
        place=fixture["place"],
    )


def test_d1_chart_ascendant(chart_fixture):
    birth = _make_birth(chart_fixture)
    d1 = build_d1_chart(birth)
    expected_asc = chart_fixture["expected"]["ascendant_sign"].upper()
    actual_asc = d1.ascendant_sign.name
    # Allow 1 sign tolerance (edge cases near sign boundaries)
    assert actual_asc == expected_asc, \
        f"{chart_fixture['name']}: expected asc {expected_asc}, got {actual_asc}"


def test_d1_sun_sign(chart_fixture):
    birth = _make_birth(chart_fixture)
    d1 = build_d1_chart(birth)
    from vedic_llm.models.enums import Planet
    expected = chart_fixture["expected"]["sun_sign"].upper()
    actual = d1.planets[Planet.SUN].sign.name
    assert actual == expected, \
        f"{chart_fixture['name']}: expected Sun in {expected}, got {actual}"


def test_d1_moon_sign(chart_fixture):
    birth = _make_birth(chart_fixture)
    d1 = build_d1_chart(birth)
    from vedic_llm.models.enums import Planet
    expected = chart_fixture["expected"]["moon_sign"].upper()
    actual = d1.planets[Planet.MOON].sign.name
    assert actual == expected, \
        f"{chart_fixture['name']}: expected Moon in {expected}, got {actual}"


def test_chart_serialization(chart_fixture):
    birth = _make_birth(chart_fixture)
    d1 = build_d1_chart(birth)
    # Should serialize to JSON without error
    json_str = d1.model_dump_json()
    assert len(json_str) > 100
