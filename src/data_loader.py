import pandas as pd
import os
from typing import Dict
from src.config import SAMPLE_NAME_ROW, DATA_START_ROW


def load_tga_data(file_path: str) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    智能 Excel 加载器：
    1. 自动适配紧凑格式。
    2. 解决合并单元格导致样品名“左右横跳”的问题。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")

    try:
        # 读取原始数据，不设表头，保留绝对行号
        raw_tg = pd.read_excel(file_path, sheet_name=0, header=None, engine='openpyxl')
        raw_dtg = pd.read_excel(file_path, sheet_name=1, header=None, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Excel 读取失败，请检查文件格式。错误: {e}")

    if raw_tg.shape[1] < 2:
        raise ValueError("格式错误: 至少需要两列数据 (温度, 数值)")

    num_samples = raw_tg.shape[1] // 2

    # 预先切片数据区
    df_tg_data = raw_tg.iloc[DATA_START_ROW:].copy()
    df_dtg_data = raw_dtg.iloc[DATA_START_ROW:].copy()

    parsed_data = {}

    for i in range(num_samples):
        col_temp = i * 2
        col_val = i * 2 + 1

        # --- 智能名字提取 ---
        sample_name = f"Sample_{i + 1}"
        try:
            # 同时检查数值列 (常规) 和温度列 (合并单元格残留)
            name_v = raw_tg.iloc[SAMPLE_NAME_ROW, col_val]
            name_t = raw_tg.iloc[SAMPLE_NAME_ROW, col_temp]

            if pd.notna(name_v) and str(name_v).strip():
                sample_name = str(name_v).strip()
            elif pd.notna(name_t) and str(name_t).strip():
                sample_name = str(name_t).strip()
        except IndexError:
            pass  # 越界则保持默认名

        # --- 提取数据块 ---
        def get_block(source_df, c_t, c_v, label):
            if c_v >= source_df.shape[1]: return None
            sub = source_df.iloc[:, [c_t, c_v]].copy()
            sub.columns = ['Temp', label]
            # 强制转数字，清洗非数字字符，去除空行
            sub = sub.apply(pd.to_numeric, errors='coerce').dropna()
            return sub.sort_values('Temp') if not sub.empty else None

        curr_tg = get_block(df_tg_data, col_temp, col_val, 'TG')
        curr_dtg = get_block(df_dtg_data, col_temp, col_val, 'DTG')

        if curr_tg is None or curr_dtg is None:
            continue

        # 自动修正 DTG 方向 (确保峰是向下的)
        if curr_dtg['DTG'].mean() > 0.01:
            curr_dtg['DTG'] = -curr_dtg['DTG']

        parsed_data[sample_name] = {
            'tg': curr_tg,
            'dtg': curr_dtg
        }

    return parsed_data