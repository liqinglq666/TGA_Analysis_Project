import numpy as np


def calculate_ch_content(tg_df, dtg_df, heating_rate=10.0, integration_width=40.0, search_range=(380, 480)):
    """
    纯计算函数：输入DataFrame，输出结果字典
    """
    # 1. 找峰
    roi = dtg_df[(dtg_df['Temp'] >= search_range[0]) & (dtg_df['Temp'] <= search_range[1])]

    if roi.empty:
        return None  # 没峰

    peak_idx = roi['DTG'].idxmin()
    t_peak = roi.loc[peak_idx, 'Temp']

    # 2. 积分区间
    t_start = t_peak - integration_width
    t_end = t_peak + integration_width

    # 3. 插值获取边界点
    tg_s = np.interp(t_start, tg_df['Temp'], tg_df['TG'])
    tg_e = np.interp(t_end, tg_df['Temp'], tg_df['TG'])
    dtg_s = np.interp(t_start, dtg_df['Temp'], dtg_df['DTG'])
    dtg_e = np.interp(t_end, dtg_df['Temp'], dtg_df['DTG'])

    # 4. 计算
    total_loss = tg_s - tg_e
    bg_rate = (abs(dtg_s) + abs(dtg_e)) / 2
    bg_loss = (bg_rate / heating_rate) * (t_end - t_start)

    net_loss = max(0, total_loss - bg_loss)

    factor = 74.09 / 18.02

    return {
        't_peak': t_peak,
        't_start': t_start,
        't_end': t_end,
        'val_start': (tg_s, dtg_s),  # 用于绘图
        'val_end': (tg_e, dtg_e),  # 用于绘图
        'ch_traditional': total_loss * factor,
        'ch_corrected': net_loss * factor,
        'bg_loss_ch_equiv': bg_loss * factor
    }