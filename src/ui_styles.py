# src/ui_styles.py

MODERN_STYLESHEET = """
QMainWindow { background-color: #f4f6f9; }
QWidget { font-family: 'Segoe UI', Arial, sans-serif; }
QMenuBar { background-color: #ffffff; border-bottom: 1px solid #e1e4e8; }
QMenuBar::item:selected { background-color: #f0f3f6; border-radius: 4px; }

QGroupBox { background-color: white; border: 1px solid #e1e4e8; border-radius: 8px; margin-top: 12px; padding-top: 24px; font-size: 13px; font-weight: bold; color: #2c3e50; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; color: #34495e; }

QLabel.result-label { color: #57606a; font-weight: normal; font-size: 12px; }
QLabel.result-value { color: #24292f; font-weight: bold; font-size: 14px; }
QLabel.result-highlight { color: #cf222e; font-weight: 800; font-size: 20px; }
QLabel.result-secondary { color: #0969da; font-weight: bold; font-size: 14px; }
QLabel.coord-label { color: #57606a; font-size: 11px; }
QLabel.coord-value { color: #0969da; font-weight: bold; font-family: 'Consolas', monospace; }

QDoubleSpinBox, QComboBox { border: 1px solid #d0d7de; border-radius: 4px; padding: 4px; background-color: white; min-height: 20px; }
QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #0969da; }

QPushButton { border-radius: 6px; padding: 6px 12px; font-weight: bold; border: 1px solid transparent; }
QPushButton:hover { opacity: 0.9; }
QPushButton.color-btn { border: 1px solid #d0d7de; border-radius: 4px; }
QPushButton.color-btn:hover { border: 1px solid #0969da; }

QProgressBar { border: none; background-color: #e1e4e8; border-radius: 4px; height: 6px; text-align: center; }
QProgressBar::chunk { background-color: #2da44e; border-radius: 4px; }
"""