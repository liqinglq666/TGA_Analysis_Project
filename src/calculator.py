import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
from src.config import STOICHIOMETRIC_FACTOR


def calculate_ch_content(
        tg_df: pd.DataFrame,
        dtg_df: pd.DataFrame,
        heating_rate: float = 10.0,
        integration_width: float = 40.0,
        search_range: Tuple[float, float] = (380, 480)
) -> Optional[Dict]:
    """
    Core logic for Tangent Method (切线法) calculation.
    Returns None if no valid peak is found in ROI.
    """

    # 1. ROI Selection
    mask = (dtg_df['Temp'] >= search_range[0]) & (dtg_df['Temp'] <= search_range[1])
    roi = dtg_df[mask]

    # Sanity check: no peak, no talk
    if roi.empty:
        return None

    # Find local minimum (DTG peak is negative)
    peak_idx = roi['DTG'].idxmin()
    t_peak = roi.loc[peak_idx, 'Temp']

    # 2. Integration Bounds
    t_start = t_peak - integration_width
    t_end = t_peak + integration_width

    # 3. Interpolation (Critical step)
    # Native index lookup is risky due to discrete steps, using linear interp instead.
    tg_s = np.interp(t_start, tg_df['Temp'], tg_df['TG'])
    tg_e = np.interp(t_end, tg_df['Temp'], tg_df['TG'])

    dtg_s = np.interp(t_start, dtg_df['Temp'], dtg_df['DTG'])
    dtg_e = np.interp(t_end, dtg_df['Temp'], dtg_df['DTG'])

    # 4. Content Calculation
    total_mass_loss = tg_s - tg_e

    # Baseline correction: assumes linear drift between start and end points
    avg_bg_rate = (abs(dtg_s) + abs(dtg_e)) / 2
    bg_loss = (avg_bg_rate / heating_rate) * (t_end - t_start)

    # Clamp to 0 to avoid negative physics
    net_loss = max(0, total_mass_loss - bg_loss)

    return {
        't_peak': t_peak,
        't_start': t_start,
        't_end': t_end,
        'val_start': (tg_s, dtg_s),  # For visualization
        'val_end': (tg_e, dtg_e),
        'ch_traditional': total_mass_loss * STOICHIOMETRIC_FACTOR,
        'ch_corrected': net_loss * STOICHIOMETRIC_FACTOR,
        'bg_loss_ch_equiv': bg_loss * STOICHIOMETRIC_FACTOR
    }