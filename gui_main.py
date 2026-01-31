import sys
import os
import pandas as pd
import numpy as np
import traceback

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFileDialog, QDoubleSpinBox,
    QMessageBox, QGroupBox, QCheckBox, QProgressBar, QStatusBar,
    QColorDialog, QFrame, QGridLayout, QSlider, QAbstractSpinBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QColor, QIcon, QAction

# Matplotlib integration
import matplotlib

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Project modules
from src.data_loader import load_tga_data
from src.calculator import calculate_ch_content, safe_smooth
from src.config import *

# === 🎨 CSS 样式表 (Dashboard Style) ===
MODERN_STYLESHEET = """
QMainWindow { background-color: #f4f6f9; }
QWidget { font-family: 'Segoe UI', Arial, sans-serif; }

QGroupBox {
    background-color: white;
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    margin-top: 12px; 
    padding-top: 24px;
    font-size: 13px;
    font-weight: bold;
    color: #2c3e50;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
    color: #34495e;
}

QLabel.result-label { color: #57606a; font-weight: normal; font-size: 12px; }
QLabel.result-value { color: #24292f; font-weight: bold; font-size: 14px; }
QLabel.result-highlight { color: #cf222e; font-weight: 800; font-size: 24px; }

QLabel.coord-label { color: #57606a; font-size: 11px; }
QLabel.coord-value { color: #0969da; font-weight: bold; font-family: 'Consolas', monospace; }

QDoubleSpinBox {
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 4px 25px 4px 4px;
    background-color: white;
    min-height: 20px;
}
QDoubleSpinBox:focus { border: 1px solid #0969da; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    width: 20px;
    background: #f6f8fa;
    border-left: 1px solid #d0d7de;
}
QDoubleSpinBox::up-button {
    subcontrol-position: top right;
    border-top-right-radius: 4px;
    border-bottom: 1px solid #d0d7de;
}
QDoubleSpinBox::down-button {
    subcontrol-position: bottom right;
    border-bottom-right-radius: 4px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #0969da; }

QComboBox {
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 4px;
    background-color: white;
    min-height: 20px;
}
QComboBox:focus { border: 1px solid #0969da; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 0px;
}
QComboBox QAbstractItemView {
    background-color: white;
    border: 1px solid #d0d7de;
    selection-background-color: #0969da;
    selection-color: white;
}

QPushButton {
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
    border: 1px solid transparent;
}
QPushButton:hover { opacity: 0.9; }

QPushButton.color-btn {
    border: 1px solid #d0d7de;
    border-radius: 4px;
}
QPushButton.color-btn:hover { border: 1px solid #0969da; }

QProgressBar {
    border: none;
    background-color: #e1e4e8;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk { background-color: #2da44e; border-radius: 4px; }
"""


class DataLoaderThread(QThread):
    finished = pyqtSignal(dict, list)
    error = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.path = file_path

    def run(self):
        try:
            data = load_tga_data(self.path)
            samples = list(data.keys())
            self.finished.emit(data, samples)
        except Exception as e:
            self.error.emit(traceback.format_exc())


class CustomToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        actions_to_remove = ['Customize', 'Subplots']
        for action in self.actions():
            if action.text() in actions_to_remove:
                self.removeAction(action)
            if action.toolTip() and ('configuration' in action.toolTip() or 'parameters' in action.toolTip()):
                self.removeAction(action)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=DPI):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        fig.tight_layout()
        super().__init__(fig)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGA-CH Analysis Pro (Dashboard Edition)")
        self.resize(1450, 950)
        self.setStyleSheet(MODERN_STYLESHEET)

        self.settings = QSettings("MyLab", "TGA_Analyzer")
        self.data_store = {}
        self.sample_list = []
        self.current_result = None
        self.current_dtg = None

        self.style_cfg = {
            'line_color': self.settings.value("line_color", "#2c3e50"),
            'line_style': self.settings.value("line_style", "-"),
            'line_width': float(self.settings.value("line_width", 1.8)),
            'base_color': self.settings.value("base_color", "#e74c3c"),
            'base_style': self.settings.value("base_style", "--"),
            'area_color': self.settings.value("area_color", "#3498db"),
            'area_alpha': float(self.settings.value("area_alpha", 0.3))
        }
        self.line_styles_map = ['-', '--', ':', '-.']

        self._setup_plot_defaults()
        self.init_ui()
        self._load_config()

    def _setup_plot_defaults(self):
        plt.rcParams.update({
            'font.family': FONT_FAMILY,
            'font.size': 10,
            'axes.linewidth': 1.2,
            'xtick.direction': 'in', 'ytick.direction': 'in',
            'xtick.top': True, 'ytick.right': True
        })

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ==========================
        # 🟢 LEFT SIDEBAR
        # ==========================
        left_widget = QWidget()
        left_widget.setFixedWidth(340)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 1. Data Source
        gb_data = QGroupBox("📁 1. Data Source")
        v_data = QVBoxLayout()
        self.btn_load = QPushButton(" Load Excel File")
        self.btn_load.setStyleSheet("background-color: #2da44e; color: white; padding: 10px;")
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.clicked.connect(self.on_load_click)
        self.pbar = QProgressBar()
        self.pbar.hide()
        self.lbl_status = QLabel("No Data")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_data.addWidget(self.btn_load)
        v_data.addWidget(self.pbar)
        v_data.addWidget(self.lbl_status)
        gb_data.setLayout(v_data)
        left_layout.addWidget(gb_data)

        # 2. Params
        gb_param = QGroupBox("⚙️ 2. Analysis Params")
        v_param = QVBoxLayout()
        self.spin_rate = self._make_spin("Heating Rate (°C/min):", v_param, 1, 100, DEFAULT_HEATING_RATE)
        self.spin_width = self._make_spin("Integration Width (±°C):", v_param, 5, 100, DEFAULT_INTEGRATION_WIDTH)
        self.chk_smooth = QCheckBox("Enable SG Smoothing")
        self.chk_smooth.toggled.connect(self.run_analysis)
        v_param.addWidget(self.chk_smooth)

        # === ✨ 新增：更新按钮 ===
        self.btn_update = QPushButton("⚡ Update Calculation")
        self.btn_update.setStyleSheet("""
            background-color: #0969da; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            margin-top: 5px;
        """)
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self.run_analysis)
        v_param.addWidget(self.btn_update)
        # =======================

        gb_param.setLayout(v_param)
        left_layout.addWidget(gb_param)

        # 3. Sample
        gb_sample = QGroupBox("🔍 3. Sample Selection")
        v_sample = QVBoxLayout()
        self.combo_samples = QComboBox()
        self.combo_samples.currentIndexChanged.connect(self.run_analysis)
        v_sample.addWidget(self.combo_samples)
        gb_sample.setLayout(v_sample)
        left_layout.addWidget(gb_sample)

        # 4. Results
        gb_res = QGroupBox("📊 Quantification Result")
        gb_res.setStyleSheet("QGroupBox { border: 1px solid #0969da; }")
        res_grid = QGridLayout()
        res_grid.setVerticalSpacing(10)

        # Helper for styled labels
        def create_res_lbl(text, style_class):
            l = QLabel(text)
            l.setProperty("class", style_class)
            return l

        res_grid.addWidget(QLabel("Peak Temperature:", objectName="result_label"), 0, 0)
        self.lbl_peak = create_res_lbl("-", "result-value")
        self.lbl_peak.setAlignment(Qt.AlignmentFlag.AlignRight)
        res_grid.addWidget(self.lbl_peak, 0, 1)

        res_grid.addWidget(QLabel("CH Content (Net):", objectName="result_label"), 1, 0)
        self.lbl_ch_net = create_res_lbl("-", "result-highlight")
        self.lbl_ch_net.setAlignment(Qt.AlignmentFlag.AlignRight)
        res_grid.addWidget(self.lbl_ch_net, 1, 1)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        res_grid.addWidget(line, 2, 0, 1, 2)

        res_grid.addWidget(QLabel("CH Content (Raw):", objectName="result_label"), 3, 0)
        self.lbl_ch_raw = create_res_lbl("-", "result-value")
        self.lbl_ch_raw.setAlignment(Qt.AlignmentFlag.AlignRight)
        res_grid.addWidget(self.lbl_ch_raw, 3, 1)

        res_grid.addWidget(QLabel("Background Loss:", objectName="result_label"), 4, 0)
        self.lbl_bg_loss = create_res_lbl("-", "result-value")
        self.lbl_bg_loss.setStyleSheet("color: #8250df;")
        self.lbl_bg_loss.setAlignment(Qt.AlignmentFlag.AlignRight)
        res_grid.addWidget(self.lbl_bg_loss, 4, 1)
        gb_res.setLayout(res_grid)
        left_layout.addWidget(gb_res)

        # Export Excel
        self.btn_export = QPushButton(" 📥 Batch Export Excel")
        self.btn_export.setStyleSheet("background-color: #8250df; color: white; padding: 10px;")
        self.btn_export.clicked.connect(self.on_export)
        self.btn_export.setEnabled(False)
        left_layout.addWidget(self.btn_export)

        left_layout.addStretch()
        main_layout.addWidget(left_widget)

        # ==========================
        # 🔵 RIGHT SIDE (Plot & Tools)
        # ==========================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # === ✨ Top Control Area (Split View) ===
        top_ctrl_widget = QWidget()
        top_ctrl_layout = QHBoxLayout(top_ctrl_widget)
        top_ctrl_layout.setContentsMargins(0, 0, 0, 0)
        top_ctrl_layout.setSpacing(15)

        # --- Panel A: Style Control (Left) ---
        ctrl_panel = QGroupBox("🎨 Plot Style Control")
        ctrl_layout = QGridLayout()
        ctrl_layout.setVerticalSpacing(12)
        ctrl_layout.setHorizontalSpacing(15)

        # DTG Line
        ctrl_layout.addWidget(QLabel("DTG Line:"), 0, 0)
        self.btn_line_color = QPushButton()
        self.btn_line_color.setFixedSize(40, 22)
        self.btn_line_color.setProperty("class", "color-btn")
        self.btn_line_color.clicked.connect(self.pick_line_color)
        ctrl_layout.addWidget(self.btn_line_color, 0, 1)
        self.combo_linestyle = QComboBox()
        self.combo_linestyle.addItems(["Solid", "Dash", "Dot", "DaDo"])
        self._set_combo(self.combo_linestyle, self.style_cfg['line_style'])
        self.combo_linestyle.currentIndexChanged.connect(self.update_plot_appearance)
        ctrl_layout.addWidget(self.combo_linestyle, 0, 2)

        # Baseline
        ctrl_layout.addWidget(QLabel("Baseline:"), 1, 0)
        self.btn_base_color = QPushButton()
        self.btn_base_color.setFixedSize(40, 22)
        self.btn_base_color.setProperty("class", "color-btn")
        self.btn_base_color.clicked.connect(self.pick_base_color)
        ctrl_layout.addWidget(self.btn_base_color, 1, 1)
        self.combo_base_style = QComboBox()
        self.combo_base_style.addItems(["Solid", "Dash", "Dot", "DaDo"])
        self._set_combo(self.combo_base_style, self.style_cfg['base_style'])
        self.combo_base_style.currentIndexChanged.connect(self.update_plot_appearance)
        ctrl_layout.addWidget(self.combo_base_style, 1, 2)

        # Area
        ctrl_layout.addWidget(QLabel("Area Fill:"), 2, 0)
        self.btn_area_color = QPushButton()
        self.btn_area_color.setFixedSize(40, 22)
        self.btn_area_color.setProperty("class", "color-btn")
        self.btn_area_color.clicked.connect(self.pick_area_color)
        ctrl_layout.addWidget(self.btn_area_color, 2, 1)
        self.spin_alpha = QDoubleSpinBox()
        self.spin_alpha.setRange(0.0, 1.0)
        self.spin_alpha.setSingleStep(0.1)
        self.spin_alpha.setValue(self.style_cfg['area_alpha'])
        self.spin_alpha.setPrefix("Op: ")
        self.spin_alpha.valueChanged.connect(self.update_plot_appearance)
        ctrl_layout.addWidget(self.spin_alpha, 2, 2)

        ctrl_panel.setLayout(ctrl_layout)

        # --- ✨ Panel B: Captured Metrics (Right - New!) ---
        metrics_panel = QGroupBox("📉 Peak Coordinates")
        metrics_layout = QGridLayout()
        metrics_layout.setVerticalSpacing(8)

        # Helper function to create styled labels SAFELY
        def create_coord_lbl(text, style_class):
            l = QLabel(text)
            l.setProperty("class", style_class)
            return l

        # Header
        metrics_layout.addWidget(QLabel("Point"), 0, 0)
        metrics_layout.addWidget(QLabel("Temp (°C)"), 0, 1)
        metrics_layout.addWidget(QLabel("DTG (%/min)"), 0, 2)

        # Start Point
        metrics_layout.addWidget(create_coord_lbl("Onset:", "coord-label"), 1, 0)
        self.lbl_p_start_t = create_coord_lbl("-", "coord-value")
        metrics_layout.addWidget(self.lbl_p_start_t, 1, 1)
        self.lbl_p_start_d = create_coord_lbl("-", "coord-value")
        metrics_layout.addWidget(self.lbl_p_start_d, 1, 2)

        # Peak Point
        metrics_layout.addWidget(create_coord_lbl("Peak:", "coord-label"), 2, 0)
        self.lbl_p_peak_t = create_coord_lbl("-", "coord-value")
        metrics_layout.addWidget(self.lbl_p_peak_t, 2, 1)
        self.lbl_p_peak_d = create_coord_lbl("-", "coord-value")
        metrics_layout.addWidget(self.lbl_p_peak_d, 2, 2)

        # End Point
        metrics_layout.addWidget(create_coord_lbl("Endset:", "coord-label"), 3, 0)
        self.lbl_p_end_t = create_coord_lbl("-", "coord-value")
        metrics_layout.addWidget(self.lbl_p_end_t, 3, 1)
        self.lbl_p_end_d = create_coord_lbl("-", "coord-value")
        metrics_layout.addWidget(self.lbl_p_end_d, 3, 2)

        metrics_panel.setLayout(metrics_layout)

        # Add both to top layout
        top_ctrl_layout.addWidget(ctrl_panel, 3)  # 60% Width
        top_ctrl_layout.addWidget(metrics_panel, 2)  # 40% Width

        right_layout.addWidget(top_ctrl_widget)

        # --- Plot Area ---
        plot_container = QWidget()
        plot_container.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #e1e4e8;")
        plot_layout = QVBoxLayout(plot_container)

        self.canvas = MplCanvas(self)
        self.toolbar = CustomToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: transparent; border: none;")

        btn_save_img = QPushButton("📸 Save Image")
        btn_save_img.setStyleSheet("background-color: #2c3e50; color: white; padding: 5px 15px; border-radius: 4px;")
        btn_save_img.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_img.clicked.connect(self.save_high_res_plot)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.toolbar)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_save_img)

        plot_layout.addLayout(toolbar_layout)
        plot_layout.addWidget(self.canvas)

        right_layout.addWidget(plot_container, stretch=1)
        main_layout.addWidget(right_widget, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._update_color_btn(self.btn_line_color, self.style_cfg['line_color'])
        self._update_color_btn(self.btn_base_color, self.style_cfg['base_color'])
        self._update_color_btn(self.btn_area_color, self.style_cfg['area_color'])

    def _set_combo(self, combo, value):
        try:
            map_name = ["Solid", "Dash", "Dot", "DaDo"]
            idx = self.line_styles_map.index(value)
            combo.setCurrentIndex(idx)
        except:
            pass

    def _make_spin(self, label, layout, min_v, max_v, default):
        lbl = QLabel(label)
        layout.addWidget(lbl)
        sb = QDoubleSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(default)
        sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        sb.valueChanged.connect(self.run_analysis)
        layout.addWidget(sb)
        return sb

    def _load_config(self):
        self.spin_rate.setValue(self.settings.value("rate", DEFAULT_HEATING_RATE, float))
        self.spin_width.setValue(self.settings.value("width", DEFAULT_INTEGRATION_WIDTH, float))
        self.chk_smooth.setChecked(self.settings.value("smooth", False, bool))

    # === Plot Style Logic ===
    def pick_line_color(self):
        self._pick_color('line_color', self.btn_line_color)

    def pick_base_color(self):
        self._pick_color('base_color', self.btn_base_color)

    def pick_area_color(self):
        self._pick_color('area_color', self.btn_area_color)

    def _pick_color(self, key, btn):
        c = QColorDialog.getColor(QColor(self.style_cfg[key]), title="Select Color")
        if c.isValid():
            self.style_cfg[key] = c.name()
            self.settings.setValue(key, c.name())
            self._update_color_btn(btn, c.name())
            self.update_plot_appearance()

    def _update_color_btn(self, btn, color):
        btn.setStyleSheet(f"background-color: {color}; border: 1px solid #999; border-radius: 4px;")

    def update_plot_appearance(self):
        self.style_cfg['area_alpha'] = self.spin_alpha.value()
        self.style_cfg['line_style'] = self.line_styles_map[self.combo_linestyle.currentIndex()]
        self.style_cfg['base_style'] = self.line_styles_map[self.combo_base_style.currentIndex()]
        for k, v in self.style_cfg.items(): self.settings.setValue(k, v)
        if self.current_dtg is not None: self.plot_result(self.current_dtg, self.current_result,
                                                          self.combo_samples.currentText())

    # === Export High Res Image ===
    def save_high_res_plot(self):
        if self.current_dtg is None:
            QMessageBox.warning(self, "No Plot", "Please analyze a sample first.")
            return
        name = self.combo_samples.currentText()
        default_name = f"{name}_DTG.png"
        path, _ = QFileDialog.getSaveFileName(self, "Save Figure", default_name,
                                              "PNG Image (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if not path: return
        try:
            self.canvas.figure.savefig(path, dpi=300, bbox_inches='tight')
            self.status_bar.showMessage(f"Saved: {path}", 3000)
            QMessageBox.information(self, "Success", f"Image saved successfully!\n\nPath: {path}\nDPI: 300")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # === Data Logic ===
    def on_load_click(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Data", "", "Excel Files (*.xlsx)")
        if not path: return
        self.btn_load.setEnabled(False)
        self.pbar.setRange(0, 0)
        self.pbar.show()
        self.lbl_status.setText("Reading...")
        self.worker = DataLoaderThread(path)
        self.worker.finished.connect(self.on_load_success)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def on_load_success(self, data, samples):
        self.data_store = data
        self.pbar.hide()
        self.btn_load.setEnabled(True)
        self.lbl_status.setText(f"Loaded {len(samples)}")
        self.combo_samples.blockSignals(True)
        self.combo_samples.clear()
        self.combo_samples.addItems(samples)
        self.combo_samples.blockSignals(False)
        self.btn_export.setEnabled(True)
        self.run_analysis()

    def on_load_error(self, msg):
        self.pbar.hide()
        self.btn_load.setEnabled(True)
        QMessageBox.critical(self, "Error", "Failed to load file. Please check format.")

    def run_analysis(self):
        if not self.data_store: return
        name = self.combo_samples.currentText()
        if not name or name not in self.data_store: return
        raw = self.data_store[name]
        tg, dtg = raw['tg'].copy(), raw['dtg'].copy()
        if self.chk_smooth.isChecked(): dtg['DTG'] = safe_smooth(dtg['DTG'])
        self.current_result = calculate_ch_content(tg, dtg, self.spin_rate.value(), self.spin_width.value())
        self.current_dtg = dtg

        if self.current_result:
            # Update Left Panel
            self.lbl_peak.setText(f"{self.current_result['t_peak']:.1f} °C")
            self.lbl_ch_net.setText(f"{self.current_result['ch_corrected']:.2f} %")
            self.lbl_ch_raw.setText(f"{self.current_result['ch_traditional']:.2f} %")
            self.lbl_bg_loss.setText(f"{self.current_result['bg_loss']:.2f} %")

            # Update Right Top Panel
            t_s = self.current_result['t_start']
            val_s = self.current_result['val_start'][1]
            t_p = self.current_result['t_peak']
            val_p = dtg.loc[dtg['Temp'] == t_p, 'DTG'].values[0] if not dtg.loc[dtg['Temp'] == t_p].empty else 0
            t_e = self.current_result['t_end']
            val_e = self.current_result['val_end'][1]

            self.lbl_p_start_t.setText(f"{t_s:.1f}")
            self.lbl_p_start_d.setText(f"{val_s:.3f}")
            self.lbl_p_peak_t.setText(f"{t_p:.1f}")
            self.lbl_p_peak_d.setText(f"{val_p:.3f}")
            self.lbl_p_end_t.setText(f"{t_e:.1f}")
            self.lbl_p_end_d.setText(f"{val_e:.3f}")
        else:
            for lbl in [self.lbl_peak, self.lbl_ch_net, self.lbl_ch_raw, self.lbl_bg_loss]: lbl.setText("-")
            for lbl in [self.lbl_p_start_t, self.lbl_p_start_d, self.lbl_p_peak_t, self.lbl_p_peak_d, self.lbl_p_end_t,
                        self.lbl_p_end_d]: lbl.setText("-")

        self.plot_result(dtg, self.current_result, name)

    def plot_result(self, dtg_df, res, title):
        ax = self.canvas.axes
        ax.clear()
        s = self.style_cfg
        mask = (dtg_df['Temp'] > 300) & (dtg_df['Temp'] < 600)
        sub = dtg_df[mask]

        ax.plot(sub['Temp'], sub['DTG'],
                color=s['line_color'], linestyle=s['line_style'], linewidth=s['line_width'],
                label='DTG', zorder=2)
        if res:
            t_s, t_e = res['t_start'], res['t_end']
            d_s, d_e = res['val_start'][1], res['val_end'][1]
            ax.plot([t_s, t_e], [d_s, d_e],
                    color=s['base_color'], linestyle=s['base_style'], linewidth=1.5,
                    label='Base', zorder=3)
            base_line = np.interp(sub['Temp'], [t_s, t_e], [d_s, d_e])
            fill_mask = (sub['Temp'] >= t_s) & (sub['Temp'] <= t_e)
            ax.fill_between(sub['Temp'], sub['DTG'], base_line, where=fill_mask,
                            color=s['area_color'], alpha=s['area_alpha'], label='Area')
            ax.scatter(res['t_peak'], dtg_df.loc[dtg_df['Temp'] == res['t_peak'], 'DTG'],
                       c=s['line_color'], s=30 * s['line_width'], zorder=4)

        ax.set_title(f"Sample: {title}", fontweight='bold')
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("DTG (%/min)")
        ax.grid(True, linestyle=':', alpha=0.5)
        leg = ax.legend(loc='upper right', frameon=True)
        leg.set_draggable(True)
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export", "CH_Report.xlsx", "Excel (*.xlsx)")
        if not path: return
        try:
            if os.path.exists(path):
                with open(path, 'a'): pass
        except:
            QMessageBox.critical(self, "Error", "File open in Excel. Close it.")
            return
        rows = []
        for name in self.sample_list:
            raw = self.data_store[name]
            tg, dtg = raw['tg'].copy(), raw['dtg'].copy()
            if self.chk_smooth.isChecked(): dtg['DTG'] = safe_smooth(dtg['DTG'])
            res = calculate_ch_content(tg, dtg, self.spin_rate.value(), self.spin_width.value())
            row = {'Sample': name}
            if res:
                row.update({'Peak Temp': res['t_peak'], 'Net CH%': res['ch_corrected'],
                            'Raw CH%': res['ch_traditional'], 'Bg Loss': res['bg_loss']})
            rows.append(row)
        pd.DataFrame(rows).to_excel(path, index=False)
        self.status_bar.showMessage("Export Done", 3000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())