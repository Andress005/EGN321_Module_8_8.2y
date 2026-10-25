import pytest

from tank_volume import calculate_volume_gallons


def test_calculates_volume_using_workbook_formula():
    result = calculate_volume_gallons(10, 5, 12, "in")
    assert result == pytest.approx(10 * 5 * (12 / 12) * 7.48052)


def test_one_foot_depth_matches_twelve_inches():
    inches = calculate_volume_gallons(8, 4, 12, "in")
    feet = calculate_volume_gallons(8, 4, 1, "ft")
    assert inches == pytest.approx(feet)


@pytest.mark.parametrize("bad_value", [0, -1, None, "abc", float("inf"), float("nan")])
def test_rejects_invalid_dimensions(bad_value):
    with pytest.raises(ValueError):
        calculate_volume_gallons(bad_value, 5, 12, "in")


@pytest.mark.parametrize("unit", ["", "cm", "inches", None])
def test_rejects_unsupported_depth_units(unit):
    with pytest.raises(ValueError):
        calculate_volume_gallons(10, 5, 12, unit)


def test_rejects_boolean_dimension():
    with pytest.raises(ValueError):
        calculate_volume_gallons(True, 5, 12, "in")


def test_rejects_conflicting_implicit_unit():
    # The caller must explicitly select a supported unit.
    with pytest.raises(ValueError):
        calculate_volume_gallons(10, 5, 2.5, "unknown")
