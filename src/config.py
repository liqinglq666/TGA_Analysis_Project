# src/config.py

# --- 物理/化学常数 ---
M_CAOH2 = 74.09
M_H2O = 18.02
STOICHIOMETRIC_FACTOR = M_CAOH2 / M_H2O

# --- 分析参数默认值 ---
DEFAULT_HEATING_RATE = 10.0   # K/min
DEFAULT_SEARCH_RANGE = (380, 480)
DEFAULT_INTEGRATION_WIDTH = 40.0

# --- Excel 读取设置 (根据最新截图) ---
# Row 1: 表头 (Temp/TG)
# Row 2: 单位 (°C/%)
# Row 3: 样品名 (目标行) -> Index 2
# Row 4: 数据开始 -> Index 3
SAMPLE_NAME_ROW = 2
DATA_START_ROW = 3

# --- 绘图设置 (科研风格) ---
DPI = 120
FONT_FAMILY = ['Arial', 'SimHei', 'Microsoft YaHei'] # 优先 Arial