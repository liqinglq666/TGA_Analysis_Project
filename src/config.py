# src/config.py

# --- Thermodynamics & stoichiometry constants ---
M_H2O = 18.02
M_CO2 = 44.01

M_CAOH2 = 74.09
STOICHIOMETRIC_FACTOR = M_CAOH2 / M_H2O

M_CACO3 = 100.09
FACTOR_CACO3 = M_CACO3 / M_CO2

M_FS = 561.3
M_6H2O = 6 * M_H2O
FACTOR_FS = M_FS / M_6H2O

FACTOR_WATER_CO2 = M_H2O / M_CO2

# --- Analysis defaults ---
DEFAULT_HEATING_RATE = 10.0
DEFAULT_INTEGRATION_WIDTH = 40.0
# Portlandite / CH dehydroxylation may shift with binder chemistry, carbonation,
# atmosphere, and heating rate. Keep this wider than the old 380-480 °C window
# to avoid missing high-temperature shoulders while still excluding most CaCO3.
DEFAULT_CH_SEARCH_RANGE = (400.0, 520.0)
DEFAULT_REF_MODE = "as_input"
DEFAULT_BOUND_WATER_MODE = "exclude_co2"

# --- Data parsing protocol ---
SAMPLE_NAME_ROW = 2
DATA_START_ROW = 3

# --- Rendering config ---
DPI = 120
FONT_FAMILY = ["Arial", "SimHei", "Microsoft YaHei"]
