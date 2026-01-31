# src/config.py

# --- 化学/物理常量 ---
M_CAOH2 = 74.09
M_H2O = 18.02
STOICHIOMETRIC_FACTOR = M_CAOH2 / M_H2O

# --- 分析参数默认值 ---
DEFAULT_HEATING_RATE = 10.0
DEFAULT_SEARCH_RANGE = (380, 480)
DEFAULT_INTEGRATION_WIDTH = 40.0

# --- Excel 读取设置 (关键修改) ---
# 根据你的截图 (image_e83864.png):
# 第 1 行 (Index 0): Temperature / TG (表头)
# 第 2 行 (Index 1): 单位
# 第 3 行 (Index 2): 样品名称 (FSC, GSC...) <--- 名字在这里
# 第 4 行 (Index 3): 数据开始

SAMPLE_NAME_ROW = 2  # 告诉程序：名字在 Excel 的第 3 行
DATA_START_ROW = 3   # 告诉程序：数据从 Excel 的第 4 行开始

# --- UI 设置 ---
DPI = 100
FONT_FAMILY = ['SimHei', 'Microsoft YaHei', 'Arial']