from __future__ import annotations

import numpy as np
import pandas as pd

from src.core import _calculate_mass_loss, calculate_ch_content
from src.data_loader import _detect_dtg_basis


def test_invalid_temperature_range_returns_nan():
    tg = pd.DataFrame({"Temp": [100.0, 200.0], "TG": [100.0, 95.0]})

    result = _calculate_mass_loss(tg, 600.0, 800.0)

    assert np.isnan(result)


def test_per_degree_dtg_is_not_divided_by_heating_rate():
    tg = pd.DataFrame({"Temp": [400.0, 450.0, 500.0], "TG": [100.0, 95.0, 90.0]})
    dtg = pd.DataFrame({"Temp": [400.0, 450.0, 500.0], "DTG": [-0.1, -1.0, -0.1]})

    dtg.attrs["dtg_basis"] = "per_minute"
    per_minute = calculate_ch_content(tg, dtg, heating_rate=10.0, integration_width=50.0)

    dtg.attrs["dtg_basis"] = "per_degree"
    per_degree = calculate_ch_content(tg, dtg, heating_rate=10.0, integration_width=50.0)

    assert per_minute is not None
    assert per_degree is not None
    assert per_minute["mass_loss_background"] == 1.0
    assert per_degree["mass_loss_background"] == 10.0


def test_dtg_header_detection():
    raw = pd.DataFrame(
        [
            ["Temperature (°C)", "DTG (%/°C)"],
            [None, None],
            ["Sample", "Sample"],
            [400.0, -0.1],
        ]
    )

    assert _detect_dtg_basis(raw, 0, 1) == "per_degree"
