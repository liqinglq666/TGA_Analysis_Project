import pandas as pd
import os
from typing import Dict
from src.config import SAMPLE_NAME_ROW, DATA_START_ROW


def load_tga_data(file_path: str) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    智能加载器：
    1. 自动处理合并单元格带来的名字位置不确定问题。
    2. 同时检查 '温度列' 和 '数值列' 来寻找样品名。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        # 读取整个 Sheet，不设表头，保留原始位置信息
        raw_tg = pd.read_excel(file_path, sheet_name=0, header=None, engine='openpyxl')
        raw_dtg = pd.read_excel(file_path, sheet_name=1, header=None, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Excel 读取失败，请检查格式。\n错误信息: {e}")

    # 至少要有2列数据
    if raw_tg.shape[1] < 2:
        raise ValueError("格式错误：Excel 至少需要包含两列数据（温度+数值）")

    # 样品数量 = 总列数 / 2
    num_samples = raw_tg.shape[1] // 2

    # 预先切片出纯数据区域，提高循环效率
    # 从配置的 DATA_START_ROW 开始截取
    df_tg_clean = raw_tg.iloc[DATA_START_ROW:].copy()
    df_dtg_clean = raw_dtg.iloc[DATA_START_ROW:].copy()

    parsed_data = {}

    for i in range(num_samples):
        # 计算当前样品的列索引
        col_temp = i * 2  # 偶数列 (0, 2, 4...)
        col_val = i * 2 + 1  # 奇数列 (1, 3, 5...)

        # --- 核心修改：智能名字提取 ---
        sample_name = f"Sample_{i + 1}"  # 默认兜底名字

        try:
            # 获取指定行 (SAMPLE_NAME_ROW) 的两个单元格的值
            name_candidate_1 = raw_tg.iloc[SAMPLE_NAME_ROW, col_temp]  # 温度列那格
            name_candidate_2 = raw_tg.iloc[SAMPLE_NAME_ROW, col_val]  # 数值列那格

            # 策略：优先信赖非空的字符串
            # 1. 如果数值列有名字 (通常在这里)，就用它
            if pd.notna(name_candidate_2) and str(name_candidate_2).strip() != "":
                sample_name = str(name_candidate_2).strip()
            # 2. 如果数值列是空的（可能是合并单元格导致名字跑到了温度列），就用温度列的
            elif pd.notna(name_candidate_1) and str(name_candidate_1).strip() != "":
                sample_name = str(name_candidate_1).strip()

        except IndexError:
            pass  # 如果行号超出了范围，就保持默认名

        # --- 提取数据块 (TG & DTG) ---
        def extract_block(source_df, c_temp, c_val, label):
            if c_val >= source_df.shape[1]: return None

            # 按列提取
            sub = source_df.iloc[:, [c_temp, c_val]].copy()
            sub.columns = ['Temp', label]

            # 清洗：转数字 -> 丢弃空值 -> 排序
            sub = sub.apply(pd.to_numeric, errors='coerce').dropna()

            if sub.empty: return None
            return sub.sort_values('Temp')

        curr_tg = extract_block(df_tg_clean, col_temp, col_val, 'TG')
        curr_dtg = extract_block(df_dtg_clean, col_temp, col_val, 'DTG')

        # 如果数据有问题，跳过该样品
        if curr_tg is None or curr_dtg is None:
            continue

        # DTG 方向自动修正 (确保峰是向下的)
        if not curr_dtg.empty and curr_dtg['DTG'].mean() > 0.01:
            curr_dtg['DTG'] = -curr_dtg['DTG']

        parsed_data[sample_name] = {
            'tg': curr_tg,
            'dtg': curr_dtg
        }

    return parsed_data