# src/config.py

# --- 实验参数 (根据您的实验设置修改) ---
HEATING_RATE = 10.0        # 升温速率 (°C/min)
SEARCH_RANGE = (380, 480)  # 寻找 CH 峰的温度范围
INTEGRATION_WIDTH = 40     # 积分宽度：峰值 ± 40°C

# --- 化学常量 ---
M_CAOH2 = 74.09
M_H2O = 18.02
STOICHIOMETRIC_FACTOR = M_CAOH2 / M_H2O  # ≈ 4.11

# --- 绘图参数 ---
DPI = 300
FIGURE_SIZE = (12, 10)