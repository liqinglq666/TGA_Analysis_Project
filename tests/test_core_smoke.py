import math

import numpy as np
import pandas as pd
import pytest

from src.config import FACTOR_CACO3, FACTOR_WATER_CO2, STOICHIOMETRIC_FACTOR
from src.core import (
    calculate_bound_water,
    calculate_carbonation,
    calculate_ch_content,
    calculate_co2_loss,
    calculate_sample_summary,
)


def make_tg():
    temps = np.array([50, 105, 380, 400, 440, 480, 600, 800, 1000], dtype=float)
    tg = np.array([100, 99, 98, 97.5, 96.8, 96.5, 95.5, 94.5, 94.0], dtype=float)
    return pd.DataFrame({"Temp": temps, "TG": tg})


def make_dtg():
    temps = np.array([380, 400, 440, 480], dtype=float)
    dtg = np.array([-0.02, -0.06, -0.20, -0.06], dtype=float)
    return pd.DataFrame({"Temp": temps, "DTG": dtg})


def test_carbonation_uses_co2_stoichiometry():
    tg = make_tg()
    co2_loss = calculate_co2_loss(tg, (600, 800))
    assert math.isclose(co2_loss, 1.0)
    assert math.isclose(calculate_carbonation(tg, (600, 800)), FACTOR_CACO3)


def test_bound_water_modes_are_distinct_and_documented():
    tg = make_tg()
    co2_loss = calculate_co2_loss(tg, (600, 800))
    total_loss_105_1000 = 99.0 - 94.0
    assert math.isclose(calculate_bound_water(tg, co2_loss, mode="exclude_co2"), total_loss_105_1000 - co2_loss)
    assert math.isclose(
        calculate_bound_water(tg, co2_loss, mode="bhatty"),
        total_loss_105_1000 - co2_loss + FACTOR_WATER_CO2 * co2_loss,
    )


def test_ch_result_exposes_mass_loss_details():
    result = calculate_ch_content(make_tg(), make_dtg(), heating_rate=10.0, integration_width=40.0)
    assert result is not None
    assert result["mass_loss_total"] > result["mass_loss_net"] >= 0
    assert math.isclose(result["ch_corrected"], result["mass_loss_net"] * STOICHIOMETRIC_FACTOR)


def test_normalize_105_converts_absolute_mass_to_percent_basis():
    tg = make_tg()
    co2_loss = calculate_co2_loss(tg, (600, 800), ref_mode="normalize_105")
    assert math.isclose(co2_loss, (95.5 - 94.5) / 99.0 * 100.0)


def test_default_ch_search_range_keeps_high_temperature_peak():
    tg = pd.DataFrame({
        "Temp": [400.0, 440.0, 480.0, 500.0, 520.0, 560.0],
        "TG": [100.0, 99.7, 99.0, 98.6, 98.2, 98.0],
    })
    dtg = pd.DataFrame({
        "Temp": [400.0, 440.0, 480.0, 500.0, 520.0, 560.0],
        "DTG": [-0.02, -0.04, -0.08, -0.22, -0.07, -0.03],
    })
    result = calculate_ch_content(tg, dtg, heating_rate=10.0, integration_width=30.0)
    assert result is not None
    assert math.isclose(result["t_peak"], 500.0)


def test_strict_mass_loss_reports_out_of_range_temperature():
    tg = make_tg()
    assert calculate_co2_loss(tg, (600, 1200)) == 0.0
    with pytest.raises(ValueError, match="outside data range"):
        calculate_co2_loss(tg, (600, 1200), strict=True)


def test_sample_summary_matches_individual_core_calculations():
    tg = make_tg()
    dtg = make_dtg()
    summary = calculate_sample_summary(tg, dtg, heating_rate=10.0, integration_width=40.0)
    ch = calculate_ch_content(tg, dtg, heating_rate=10.0, integration_width=40.0)
    co2_loss = calculate_co2_loss(tg, (600, 800))
    assert ch is not None
    assert math.isclose(summary["CH Net (%)"], ch["ch_corrected"])
    assert math.isclose(summary["CO2 Loss (%)"], co2_loss)
    assert math.isclose(summary["CaCO3 (%)"], calculate_carbonation(tg, (600, 800)))
    assert summary["ref_mode"] == "as_input"
