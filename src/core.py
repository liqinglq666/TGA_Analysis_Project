from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from src.config import (
    DEFAULT_BOUND_WATER_MODE,
    DEFAULT_CH_SEARCH_RANGE,
    DEFAULT_REF_MODE,
    FACTOR_CACO3,
    FACTOR_FS,
    FACTOR_WATER_CO2,
    STOICHIOMETRIC_FACTOR,
)


VALID_REF_MODES = {"as_input", "normalize_105", "normalize_600"}
VALID_BOUND_WATER_MODES = {"exclude_co2", "bhatty"}
VALID_DTG_BASES = {"per_minute", "per_degree", "per_second"}


def safe_smooth(data_series: pd.Series, window_len: int = 15, polyorder: int = 3) -> pd.Series:
    n = len(data_series)
    if n <= polyorder + 1:
        return data_series

    real_window = min(window_len, n)
    if real_window % 2 == 0:
        real_window -= 1
    if real_window <= polyorder:
        return data_series

    try:
        return pd.Series(
            savgol_filter(data_series, real_window, polyorder),
            index=data_series.index,
            name=data_series.name,
        )
    except Exception:
        return data_series


def _interp_value(df: pd.DataFrame, column: str, temperature: float) -> float:
    clean = df[["Temp", column]].dropna().sort_values("Temp")
    if clean.empty:
        raise ValueError(f"No valid {column} data.")

    temp_min = float(clean["Temp"].min())
    temp_max = float(clean["Temp"].max())
    if temperature < temp_min or temperature > temp_max:
        raise ValueError(f"Temperature {temperature} is outside data range {temp_min}-{temp_max}.")

    return float(np.interp(temperature, clean["Temp"], clean[column]))


def _reference_mass(tg_df: pd.DataFrame, ref_mode: str) -> float:
    if ref_mode == "as_input":
        return 100.0
    if ref_mode == "normalize_105":
        return _interp_value(tg_df, "TG", 105.0)
    if ref_mode == "normalize_600":
        return _interp_value(tg_df, "TG", 600.0)
    raise ValueError(f"Unsupported ref_mode: {ref_mode}")


def _calculate_mass_loss(
    tg_df: pd.DataFrame,
    t_start: float,
    t_end: float,
    ref_mode: str = DEFAULT_REF_MODE,
    strict: bool = False,
) -> float:
    if ref_mode not in VALID_REF_MODES:
        raise ValueError(f"ref_mode must be one of {sorted(VALID_REF_MODES)}")

    try:
        m_start = _interp_value(tg_df, "TG", t_start)
        m_end = _interp_value(tg_df, "TG", t_end)
        loss = m_start - m_end
        if ref_mode == "as_input":
            return float(loss)

        m_ref = _reference_mass(tg_df, ref_mode)
        if m_ref <= 0:
            raise ValueError("Reference mass must be positive.")
        return float(loss / m_ref * 100.0)
    except Exception as exc:
        if strict:
            raise ValueError(
                f"Cannot calculate mass loss for {t_start}-{t_end} °C "
                f"with ref_mode={ref_mode!r}: {exc}"
            ) from exc
        return float("nan")


def _resolve_dtg_basis(dtg_df: pd.DataFrame, dtg_basis: Optional[str]) -> str:
    basis = dtg_basis or str(dtg_df.attrs.get("dtg_basis", "per_minute"))
    if basis not in VALID_DTG_BASES:
        raise ValueError(f"dtg_basis must be one of {sorted(VALID_DTG_BASES)}")
    return basis


def _background_mass_loss(
    avg_rate: float,
    delta_temp: float,
    heating_rate: float,
    dtg_basis: str,
) -> float:
    if dtg_basis == "per_degree":
        return avg_rate * delta_temp
    if heating_rate <= 0:
        raise ValueError("Heating rate must be positive for time-based DTG units.")
    if dtg_basis == "per_second":
        return avg_rate * (delta_temp / heating_rate) * 60.0
    return avg_rate * (delta_temp / heating_rate)


def _nonnegative_or_nan(value: float) -> float:
    if not np.isfinite(value):
        return float("nan")
    return max(0.0, float(value))


def calculate_ch_content(
    tg_df: pd.DataFrame,
    dtg_df: pd.DataFrame,
    heating_rate: float,
    integration_width: float,
    search_range: Tuple[float, float] = DEFAULT_CH_SEARCH_RANGE,
    ref_mode: str = DEFAULT_REF_MODE,
    dtg_basis: Optional[str] = None,
) -> Optional[Dict]:
    mask = (dtg_df["Temp"] >= search_range[0]) & (dtg_df["Temp"] <= search_range[1])
    roi = dtg_df[mask]
    if roi.empty or roi["DTG"].dropna().empty:
        return None

    t_peak = float(roi.loc[roi["DTG"].idxmin(), "Temp"])
    t_start = max(float(tg_df["Temp"].min()), t_peak - integration_width)
    t_end = min(float(tg_df["Temp"].max()), t_peak + integration_width)
    if t_end <= t_start:
        return None

    try:
        tg_s = _interp_value(tg_df, "TG", t_start)
        tg_e = _interp_value(tg_df, "TG", t_end)
        dtg_s = _interp_value(dtg_df, "DTG", t_start)
        dtg_e = _interp_value(dtg_df, "DTG", t_end)
        basis = _resolve_dtg_basis(dtg_df, dtg_basis)
        total_loss = _calculate_mass_loss(tg_df, t_start, t_end, ref_mode=ref_mode, strict=True)
        avg_bg_rate = (abs(dtg_s) + abs(dtg_e)) / 2.0
        bg_loss_raw = _background_mass_loss(avg_bg_rate, t_end - t_start, heating_rate, basis)

        if ref_mode == "as_input":
            bg_loss = bg_loss_raw
        else:
            bg_loss = bg_loss_raw / _reference_mass(tg_df, ref_mode) * 100.0
    except Exception:
        return None

    net_loss = max(0.0, total_loss - bg_loss)
    return {
        "t_peak": t_peak,
        "t_start": float(t_start),
        "t_end": float(t_end),
        "val_start": (float(tg_s), float(dtg_s)),
        "val_end": (float(tg_e), float(dtg_e)),
        "mass_loss_total": float(total_loss),
        "mass_loss_background": float(bg_loss),
        "mass_loss_net": float(net_loss),
        "ch_traditional": float(total_loss * STOICHIOMETRIC_FACTOR),
        "ch_corrected": float(net_loss * STOICHIOMETRIC_FACTOR),
        "bg_loss": float(bg_loss * STOICHIOMETRIC_FACTOR),
        "ref_mode": ref_mode,
        "dtg_basis": basis,
        "method": "DTG-guided endpoint baseline correction",
    }


def calculate_carbonation(
    tg_df: pd.DataFrame,
    search_range: Tuple[float, float] = (600.0, 800.0),
    ref_mode: str = DEFAULT_REF_MODE,
    strict: bool = False,
) -> float:
    loss_co2 = _calculate_mass_loss(
        tg_df,
        search_range[0],
        search_range[1],
        ref_mode=ref_mode,
        strict=strict,
    )
    return _nonnegative_or_nan(loss_co2 * FACTOR_CACO3)


def calculate_bound_water(
    tg_df: pd.DataFrame,
    loss_co2: float = 0.0,
    mode: str = DEFAULT_BOUND_WATER_MODE,
    ref_mode: str = DEFAULT_REF_MODE,
    strict: bool = False,
) -> float:
    if mode not in VALID_BOUND_WATER_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_BOUND_WATER_MODES)}")

    end_temp = min(1000.0, float(tg_df["Temp"].max()))
    total_loss = _calculate_mass_loss(tg_df, 105.0, end_temp, ref_mode=ref_mode, strict=strict)
    if not np.isfinite(total_loss) or not np.isfinite(loss_co2):
        return float("nan")

    if mode == "exclude_co2":
        corrected = total_loss - loss_co2
    else:
        corrected = total_loss - loss_co2 + FACTOR_WATER_CO2 * loss_co2
    return _nonnegative_or_nan(corrected)


def calculate_friedels_salt(
    tg_df: pd.DataFrame,
    search_range: Tuple[float, float] = (300.0, 380.0),
    ref_mode: str = DEFAULT_REF_MODE,
    strict: bool = False,
) -> float:
    loss_h2o = _calculate_mass_loss(
        tg_df,
        search_range[0],
        search_range[1],
        ref_mode=ref_mode,
        strict=strict,
    )
    return _nonnegative_or_nan(loss_h2o * FACTOR_FS)


def calculate_csh_estimation(
    tg_df: pd.DataFrame,
    search_range: Tuple[float, float] = (50.0, 200.0),
    ref_mode: str = DEFAULT_REF_MODE,
    strict: bool = False,
) -> float:
    loss = _calculate_mass_loss(
        tg_df,
        search_range[0],
        search_range[1],
        ref_mode=ref_mode,
        strict=strict,
    )
    return _nonnegative_or_nan(loss)


def calculate_sample_summary(
    tg_df: pd.DataFrame,
    dtg_df: pd.DataFrame,
    heating_rate: float,
    integration_width: float,
    ch_search_range: Tuple[float, float] = DEFAULT_CH_SEARCH_RANGE,
    caco3_range: Tuple[float, float] = (600.0, 800.0),
    friedels_range: Tuple[float, float] = (300.0, 380.0),
    csh_range: Tuple[float, float] = (50.0, 200.0),
    ref_mode: str = DEFAULT_REF_MODE,
    bound_water_mode: str = DEFAULT_BOUND_WATER_MODE,
    strict: bool = False,
) -> Dict[str, float]:
    ch_result = calculate_ch_content(
        tg_df,
        dtg_df,
        heating_rate=heating_rate,
        integration_width=integration_width,
        search_range=ch_search_range,
        ref_mode=ref_mode,
    )
    co2_loss = calculate_co2_loss(tg_df, caco3_range, ref_mode=ref_mode, strict=strict)
    return {
        "Peak Temp (°C)": ch_result["t_peak"] if ch_result else np.nan,
        "CH Total (%)": ch_result["ch_traditional"] if ch_result else np.nan,
        "CH Net (%)": ch_result["ch_corrected"] if ch_result else np.nan,
        "CH Background (%)": ch_result["bg_loss"] if ch_result else np.nan,
        "Wn (%)": calculate_bound_water(
            tg_df,
            co2_loss,
            mode=bound_water_mode,
            ref_mode=ref_mode,
            strict=strict,
        ),
        "CO2 Loss (%)": co2_loss,
        "CaCO3 (%)": calculate_carbonation(tg_df, caco3_range, ref_mode=ref_mode, strict=strict),
        "Fs (%)": calculate_friedels_salt(tg_df, friedels_range, ref_mode=ref_mode, strict=strict),
        "Hydrate Index (%)": calculate_csh_estimation(tg_df, csh_range, ref_mode=ref_mode, strict=strict),
        "ref_mode": ref_mode,
        "bound_water_mode": bound_water_mode,
        "dtg_basis": ch_result["dtg_basis"] if ch_result else str(dtg_df.attrs.get("dtg_basis", "unknown")),
    }


def calculate_co2_loss(
    tg_df: pd.DataFrame,
    search_range: Tuple[float, float] = (600.0, 800.0),
    ref_mode: str = DEFAULT_REF_MODE,
    strict: bool = False,
) -> float:
    loss = _calculate_mass_loss(
        tg_df,
        search_range[0],
        search_range[1],
        ref_mode=ref_mode,
        strict=strict,
    )
    return _nonnegative_or_nan(loss)
