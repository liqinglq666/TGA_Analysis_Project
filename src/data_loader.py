# src/data_loader.py

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Union
from src.config import SAMPLE_NAME_ROW, DATA_START_ROW


def _extract_data_block(source_df: pd.DataFrame, col_temp_idx: int, col_val_idx: int, label: str) -> Optional[pd.DataFrame]:
    if col_temp_idx >= source_df.shape[1] or col_val_idx >= source_df.shape[1]: return None
    sub_df = source_df.iloc[:, [col_temp_idx, col_val_idx]].copy()
    sub_df.columns = ['Temp', label]
    sub_df = sub_df.apply(pd.to_numeric, errors='coerce').dropna()
    return sub_df.sort_values('Temp') if not sub_df.empty else None


def _deduplicate_sample_name(name: str, existing_names) -> str:
    """Return a stable unique sample name without silently overwriting data."""
    if name not in existing_names:
        return name
    idx = 2
    while f"{name}_{idx}" in existing_names:
        idx += 1
    return f"{name}_{idx}"


def load_tga_data(file_path: Union[str, Path]) -> Dict[str, Dict[str, pd.DataFrame]]:
    target_path = Path(file_path)
    if not target_path.exists(): raise FileNotFoundError(f"文件未找到: {target_path}")

    try:
        with pd.ExcelFile(target_path, engine='openpyxl') as xls:
            if len(xls.sheet_names) < 2:
                raise ValueError("格式无效：Excel 文件需包含 TG 和 DTG 两个 Sheet。")
            raw_tg = pd.read_excel(xls, sheet_name=0, header=None)
            raw_dtg = pd.read_excel(xls, sheet_name=1, header=None)
    except Exception as e: raise RuntimeError(f"Excel 读取失败: {e}")

    if raw_tg.shape[1] < 2: raise ValueError("格式无效：单一样本需包含 Temp 和 Value 两列。")
    if raw_dtg.shape[1] < 2: raise ValueError("格式无效：DTG Sheet 需包含 Temp 和 Value 两列。")
    if raw_tg.shape[1] != raw_dtg.shape[1]:
        raise ValueError("格式无效：TG 与 DTG Sheet 的列数不一致。")

    df_tg_data, df_dtg_data = raw_tg.iloc[DATA_START_ROW:].copy(), raw_dtg.iloc[DATA_START_ROW:].copy()
    parsed_data = {}

    for i in range(raw_tg.shape[1] // 2):
        col_t, col_v = i * 2, i * 2 + 1
        sample_name = f"Sample_{i + 1}"
        if col_v < raw_tg.shape[1]:
            name_v, name_t = raw_tg.iloc[SAMPLE_NAME_ROW, col_v], raw_tg.iloc[SAMPLE_NAME_ROW, col_t]
            if pd.notna(name_v) and str(name_v).strip(): sample_name = str(name_v).strip()
            elif pd.notna(name_t) and str(name_t).strip(): sample_name = str(name_t).strip()

        curr_tg, curr_dtg = _extract_data_block(df_tg_data, col_t, col_v, 'TG'), _extract_data_block(df_dtg_data, col_t, col_v, 'DTG')
        if curr_tg is None or curr_dtg is None: continue
        if curr_dtg['DTG'].mean() > 0.01: curr_dtg['DTG'] = -curr_dtg['DTG']
        sample_name = _deduplicate_sample_name(sample_name, parsed_data)
        parsed_data[sample_name] = {'tg': curr_tg, 'dtg': curr_dtg}

    if not parsed_data:
        raise ValueError("未解析到有效样品数据，请检查第 4 行起是否包含数值型 Temp/TG/DTG 数据。")

    return parsed_data
