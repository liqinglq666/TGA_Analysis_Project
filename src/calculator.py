import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from typing import Optional, Dict, Tuple
from src.config import STOICHIOMETRIC_FACTOR


def safe_smooth(data_series: pd.Series, window_len: int = 15, polyorder: int = 3) -> pd.Series:
    """
    安全平滑包装器：防止因数据点少于窗口长度导致的 crash。
    """
    n = len(data_series)
    if n <= polyorder + 1:
        return data_series

    real_window = min(window_len, n)
    if real_window % 2 == 0:
        real_window -= 1

    if real_window <= polyorder:
        return data_series

    try:
        return savgol_filter(data_series, real_window, polyorder)
    except:
        return data_series


def calculate_ch_content(
        tg_df: pd.DataFrame,
        dtg_df: pd.DataFrame,
        heating_rate: float,
        integration_width: float,
        search_range: Tuple[float, float] = (380, 480)
) -> Optional[Dict]:
    """
    核心逻辑：动态基线扣除法 (DBS)
    """
    # 1. 锁定 ROI
    mask = (dtg_df['Temp'] >= search_range[0]) & (dtg_df['Temp'] <= search_range[1])
    roi = dtg_df[mask]

    if roi.empty: return None

    # 找峰
    peak_idx = roi['DTG'].idxmin()
    t_peak = roi.loc[peak_idx, 'Temp']

    # 2. 定义积分区间
    t_start = t_peak - integration_width
    t_end = t_peak + integration_width

    # 3. 线性插值
    try:
        tg_s = np.interp(t_start, tg_df['Temp'], tg_df['TG'])
        tg_e = np.interp(t_end, tg_df['Temp'], tg_df['TG'])
        dtg_s = np.interp(t_start, dtg_df['Temp'], dtg_df['DTG'])
        dtg_e = np.interp(t_end, dtg_df['Temp'], dtg_df['DTG'])
    except:
        return None

        # 4. 热力学计算
    total_loss = tg_s - tg_e

    # Background Drift
    avg_bg_rate = (abs(dtg_s) + abs(dtg_e)) / 2
    bg_loss = (avg_bg_rate / heating_rate) * (t_end - t_start)

    net_loss = max(0, total_loss - bg_loss)

    return {
        't_peak': t_peak,
        't_start': t_start,
        't_end': t_end,
        'val_start': (tg_s, dtg_s),
        'val_end': (tg_e, dtg_e),
        'ch_traditional': total_loss * STOICHIOMETRIC_FACTOR,
        'ch_corrected': net_loss * STOICHIOMETRIC_FACTOR,
        'bg_loss': bg_loss * STOICHIOMETRIC_FACTOR
    }