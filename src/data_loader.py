import pandas as pd
import numpy as np
import os


def load_tga_data(file_path):
    """
    通用版加载器：自动识别样品数量，不限制个数。
    逻辑：Sheet1(TG), Sheet2(DTG)，每两列为一个样品。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")

    try:
        # 1. 全量读取，不跳过行（为了去抓表头里的样品名）
        # header=None 保证读入所有原始结构
        df_sheet1_raw = pd.read_excel(file_path, sheet_name=0, header=None, engine='openpyxl')
        df_sheet2_raw = pd.read_excel(file_path, sheet_name=1, header=None, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Excel 读取失败，请检查文件格式。\n错误信息: {str(e)}")

    # 2. 确定样品数量
    # 逻辑：总列数除以 2。例如 8 列就是 4 个样品。
    total_cols = df_sheet1_raw.shape[1]
    num_samples = total_cols // 2

    if num_samples == 0:
        raise ValueError("数据列数不足，无法解析（至少需要2列）")

    # 3. 尝试抓取样品名称
    # 根据之前的诊断，样品名在 Excel 的第 7 行 (index=6)，且位于奇数列 (1, 3, 5...)
    sample_names = []
    try:
        header_row_index = 6
        for i in range(num_samples):
            # 名字通常在数据的上方，对应 TG 列 (i*2+1)
            name_col = i * 2 + 1
            raw_name = df_sheet1_raw.iloc[header_row_index, name_col]

            if pd.notna(raw_name) and str(raw_name).strip() != "":
                sample_names.append(str(raw_name).strip())
            else:
                # 抓不到就用默认名
                sample_names.append(f"Sample_{i + 1}")
    except:
        # 如果出错，全部回退到默认名
        sample_names = [f"Sample_{i + 1}" for i in range(num_samples)]

    # 4. 切片获取纯数据（去掉前7行表头）
    # 注意：这里我们假设数据从第8行(index 7)开始
    df_sheet1 = df_sheet1_raw.iloc[7:].copy()
    df_sheet2 = df_sheet2_raw.iloc[7:].copy()

    parsed_data = {}

    # 5. 循环提取每个样品的数据
    for i in range(num_samples):
        name = sample_names[i]

        # 计算列索引
        col_idx_temp = i * 2
        col_idx_val = i * 2 + 1

        # --- 提取 TG ---
        # 越界保护
        if col_idx_val >= df_sheet1.shape[1]: break

        df_tg = df_sheet1.iloc[:, [col_idx_temp, col_idx_val]].copy()
        df_tg.columns = ['Temp', 'TG']
        df_tg = df_tg.apply(pd.to_numeric, errors='coerce').dropna().sort_values('Temp')

        # --- 提取 DTG ---
        # 越界保护
        if col_idx_val >= df_sheet2.shape[1]: break

        df_dtg = df_sheet2.iloc[:, [col_idx_temp, col_idx_val]].copy()
        df_dtg.columns = ['Temp', 'DTG']
        df_dtg = df_dtg.apply(pd.to_numeric, errors='coerce').dropna().sort_values('Temp')

        # 智能翻转 DTG (确保峰是向下的)
        if not df_dtg.empty and df_dtg['DTG'].mean() > 0.01:
            df_dtg['DTG'] = -df_dtg['DTG']

        parsed_data[name] = {
            'tg': df_tg,
            'dtg': df_dtg
        }

    return parsed_data