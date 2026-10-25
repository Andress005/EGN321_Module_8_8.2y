"""Tank volume calculations based on the legacy workbook formula."""

import math

GALLONS_PER_CUBIC_FOOT = 7.48052


def calculate_volume_gallons(length_ft, width_ft, depth, depth_unit):
    """Calculate rectangular tank volume in US gallons.

    Length and width must be in feet. Depth must explicitly be in
    inches ('in') or feet ('ft').
    """
    values = {
        "length": length_ft,
        "width": width_ft,
        "depth": depth,
    }

    converted = {}
    for name, value in values.items():
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a positive number.")

        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a positive number.") from None

        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{name} must be a positive finite number.")

        converted[name] = number

    if depth_unit not in ("in", "ft"):
        raise ValueError("depth_unit must be 'in' or 'ft'.")

    depth_ft = (
        converted["depth"] / 12
        if depth_unit == "in"
        else converted["depth"]
    )

    volume_cubic_feet = (
        converted["length"] * converted["width"] * depth_ft
    )
    return volume_cubic_feet * GALLONS_PER_CUBIC_FOOT
