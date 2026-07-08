# main.py

import sys
import traceback


# ==========================================
# 🛡️ 核心防御：全局异常拦截钩子
# ==========================================
def global_exception_hook(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(f"CRITICAL ERROR:\n{err_msg}", file=sys.stderr)
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("程序遭遇致命崩溃 (Fatal Error)")
            msg.setText("软件运行中出现未捕获的异常，请截图保留详细信息。")
            msg.setDetailedText(err_msg)
            msg.exec()
    except Exception:
        pass
    sys.exit(1)


sys.excepthook = global_exception_hook

import pandas as pd
import numpy as np

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QFileDialog, QDoubleSpinBox,
                             QMessageBox, QGroupBox, QCheckBox, QProgressBar, QStatusBar,
                             QColorDialog, QGridLayout)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QColor, QAction

import matplotlib

matplotlib.use('QtAgg')
import matplotlib.pyplot as plt

# 项目模块导入
from src.config import *
from src.core import *
from src.ui_styles import MODERN_STYLESHEET
from src.ui_components import DataLoaderThread, CustomToolbar, MplCanvas
from src.help_dialog import HelpDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGA-CH Analysis Pro (Modular Edition)")
        self.resize(1450, 950)
        self.setStyleSheet(MODERN_STYLESHEET)

        self.settings = QSettings("MyLab", "TGA_Analyzer")
        self.data_store, self.sample_list = {}, []
        self.current_result, self.current_dtg = None, None
        self.current_summary = {}
        self._draggable_annotation = None

        self.phase_ranges = {
            "CaCO3 (Carbonation)": (600.0, 800.0),
            "Friedel's Salt": (300.0, 380.0),
            "Bound Water (Wn)": (105.0, 1000.0),
            "Hydrate Index (50-200 °C)": (50.0, 200.0),
        }

        def safe_float(key, default):
            try:
                return float(self.settings.value(key, default))
            except Exception:
                return default

        self.style_cfg = {
            'line_color': str(self.settings.value("line_color", "#2c3e50")),
            'line_style': str(self.settings.value("line_style", "-")),
            'line_width': safe_float("line_width", 1.8),
            'base_color': str(self.settings.value("base_color", "#e74c3c")),
            'base_style': str(self.settings.value("base_style", "--")),
            'area_color': str(self.settings.value("area_color", "#3498db")),
            'area_alpha': safe_float("area_alpha", 0.3)
        }
        self.line_styles_map = ['-', '--', ':', '-.']

        self._setup_matplotlib_defaults()
        self._setup_menu()
        self._init_ui_layout()
        self._load_config()

    def _setup_matplotlib_defaults(self):
        plt.rcParams.update(
            {'font.family': FONT_FAMILY, 'font.size': 10, 'axes.linewidth': 1.2, 'xtick.direction': 'in',
             'ytick.direction': 'in', 'xtick.top': True, 'ytick.right': True})

    def _setup_menu(self):
        help_menu = self.menuBar().addMenu("💡 设置与帮助 (Help)")
        action_docs = QAction("📚 公式原理与使用说明", self)
        action_docs.setShortcut("F1")
        action_docs.triggered.connect(lambda: HelpDialog(self).exec())
        help_menu.addAction(action_docs)

    def _init_ui_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        main_layout.addWidget(self._build_left_panel())
        main_layout.addWidget(self._build_right_panel(), stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_left_panel(self) -> QWidget:
        widget = QWidget()
        widget.setFixedWidth(350)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 1. IO Control
        gb_data = QGroupBox("📁 1. Data Source")
        v_data = QVBoxLayout(gb_data)
        self.btn_load = QPushButton(" Load Excel File")
        self.btn_load.setStyleSheet("background-color: #2da44e; color: white; padding: 10px;")
        self.btn_load.clicked.connect(self.on_load_click)
        self.pbar = QProgressBar()
        self.pbar.hide()
        self.lbl_status = QLabel("No Data")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_data.addWidget(self.btn_load)
        v_data.addWidget(self.pbar)
        v_data.addWidget(self.lbl_status)
        layout.addWidget(gb_data)

        # 2. Context-Aware Params
        gb_param = QGroupBox("⚙️ 2. Analysis Parameters")
        v_param = QVBoxLayout(gb_param)
        v_param.setSpacing(10)

        v_param.addWidget(QLabel("Target Phase:"))
        self.combo_target_phase = QComboBox()
        self.combo_target_phase.addItems(
            ["CH (Calcium Hydroxide)", "CaCO3 (Carbonation)", "Friedel's Salt",
             "Bound Water (Wn)", "Hydrate Index (50-200 °C)"])
        self.combo_target_phase.currentIndexChanged.connect(self.on_phase_changed)
        v_param.addWidget(self.combo_target_phase)

        v_param.addWidget(QLabel("Mass Basis:"))
        self.combo_ref_mode = QComboBox()
        self.combo_ref_mode.addItems(["as_input", "normalize_105", "normalize_600"])
        self.combo_ref_mode.setToolTip(
            "as_input: TG 已为百分质量；normalize_105: 以 105 °C 质量归一；normalize_600: 以 600 °C 质量归一。"
        )
        self.combo_ref_mode.currentIndexChanged.connect(self.run_analysis)
        v_param.addWidget(self.combo_ref_mode)

        v_param.addWidget(QLabel("Bound Water Mode:"))
        self.combo_bound_mode = QComboBox()
        self.combo_bound_mode.addItems(["exclude_co2", "bhatty"])
        self.combo_bound_mode.setToolTip(
            "GUI 默认 exclude_co2。bhatty 仅适合 CO2 信号主要来自 CH 碳化相关损失的场景。"
        )
        self.combo_bound_mode.currentIndexChanged.connect(self.run_analysis)
        v_param.addWidget(self.combo_bound_mode)

        self.lbl_dtg_unit_note = QLabel("DTG unit assumed: %/min or mg/min")
        self.lbl_dtg_unit_note.setStyleSheet("color: #57606a; font-size: 11px;")
        self.lbl_dtg_unit_note.setToolTip(
            "若仪器导出的 DTG 是 %/°C 或 mg/°C，CH 背景项不应再除以 heating rate；请先确认仪器导出单位。"
        )
        v_param.addWidget(self.lbl_dtg_unit_note)

        self.w_ch_params = QWidget()
        l_ch = QVBoxLayout(self.w_ch_params)
        l_ch.setContentsMargins(0, 0, 0, 0)
        self.spin_rate = self._make_spin("Heating Rate:", l_ch, 1, 100, 10.0)
        self.spin_width = self._make_spin("Int. Width (±°C):", l_ch, 5, 100, 40.0)

        self.w_range_params = QWidget()
        l_range = QVBoxLayout(self.w_range_params)
        l_range.setContentsMargins(0, 0, 0, 0)
        self.spin_t_start = self._make_spin("Start Temp (°C):", l_range, 0, 1200, 600)
        self.spin_t_end = self._make_spin("End Temp (°C):", l_range, 0, 1200, 800)
        self.spin_t_start.valueChanged.connect(self.on_range_changed)
        self.spin_t_end.valueChanged.connect(self.on_range_changed)
        self.w_range_params.hide()

        v_param.addWidget(self.w_ch_params)
        v_param.addWidget(self.w_range_params)

        self.chk_smooth = QCheckBox("Enable SG Smooth")
        self.chk_smooth.toggled.connect(self.run_analysis)
        btn_calc = QPushButton("⚡ Update")
        btn_calc.setStyleSheet("background-color: #0969da; color: white;")
        btn_calc.clicked.connect(self.run_analysis)
        v_param.addWidget(self.chk_smooth)
        v_param.addWidget(btn_calc)
        layout.addWidget(gb_param)

        # 3. Sample Dropdown
        gb_sample = QGroupBox("🔍 3. Sample Selection")
        v_sample = QVBoxLayout(gb_sample)
        self.combo_samples = QComboBox()
        self.combo_samples.currentIndexChanged.connect(self.run_analysis)
        v_sample.addWidget(self.combo_samples)
        layout.addWidget(gb_sample)

        # 4. Global Results
        gb_res = QGroupBox("📊 Quantification Result")
        res_grid = QGridLayout(gb_res)

        def mk_lbl(cls):
            l = QLabel("-")
            l.setProperty("class", cls)
            l.setAlignment(Qt.AlignmentFlag.AlignRight)
            return l

        res_grid.addWidget(QLabel("CH Peak Temp:"), 0, 0)
        self.lbl_peak = mk_lbl("result-value")
        res_grid.addWidget(self.lbl_peak, 0, 1)
        res_grid.addWidget(QLabel("CH (Net):"), 1, 0)
        self.lbl_ch_net = mk_lbl("result-highlight")
        res_grid.addWidget(self.lbl_ch_net, 1, 1)
        res_grid.addWidget(QLabel("Wn:"), 2, 0)
        self.lbl_wn = mk_lbl("result-secondary")
        res_grid.addWidget(self.lbl_wn, 2, 1)
        res_grid.addWidget(QLabel("CaCO3:"), 3, 0)
        self.lbl_caco3 = mk_lbl("result-secondary")
        res_grid.addWidget(self.lbl_caco3, 3, 1)
        res_grid.addWidget(QLabel("Fs:"), 4, 0)
        self.lbl_fs = mk_lbl("result-secondary")
        res_grid.addWidget(self.lbl_fs, 4, 1)
        res_grid.addWidget(QLabel("Hydrate Index:"), 5, 0)
        self.lbl_hydrate = mk_lbl("result-secondary")
        res_grid.addWidget(self.lbl_hydrate, 5, 1)
        layout.addWidget(gb_res)

        # Action Buttons
        h_btn = QHBoxLayout()
        self.btn_copy = QPushButton("📋 Copy")
        self.btn_copy.clicked.connect(self.copy_results_to_clipboard)
        self.btn_copy.setEnabled(False)
        self.btn_export = QPushButton(" 📥 Export")
        self.btn_export.setStyleSheet("background-color: #8250df; color: white;")
        self.btn_export.clicked.connect(self.on_export)
        self.btn_export.setEnabled(False)
        h_btn.addWidget(self.btn_copy)
        h_btn.addWidget(self.btn_export)
        layout.addLayout(h_btn)
        layout.addStretch()
        return widget

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        top_ctrl = QWidget()
        top_h = QHBoxLayout(top_ctrl)
        top_h.setContentsMargins(0, 0, 0, 0)

        # Style Group
        gb_style = QGroupBox("🎨 Plot Style")
        g_style = QGridLayout(gb_style)

        def mk_btn(cb):
            b = QPushButton()
            b.setFixedSize(40, 22)
            b.setProperty("class", "color-btn")
            b.clicked.connect(cb)
            return b

        def mk_cb(items, cb):
            c = QComboBox()
            c.addItems(items)
            c.currentIndexChanged.connect(cb)
            return c

        self.btn_line_color = mk_btn(lambda: self._pick_color('line_color', self.btn_line_color))
        self.combo_linestyle = mk_cb(["Solid", "Dash", "Dot", "DaDo"], self.update_plot_appearance)
        self.btn_base_color = mk_btn(lambda: self._pick_color('base_color', self.btn_base_color))
        self.combo_base_style = mk_cb(["Solid", "Dash", "Dot", "DaDo"], self.update_plot_appearance)
        self.btn_area_color = mk_btn(lambda: self._pick_color('area_color', self.btn_area_color))
        self.spin_alpha = QDoubleSpinBox()
        self.spin_alpha.setRange(0, 1)
        self.spin_alpha.setSingleStep(0.1)
        self.spin_alpha.valueChanged.connect(self.update_plot_appearance)

        g_style.addWidget(QLabel("DTG Line:"), 0, 0)
        g_style.addWidget(self.btn_line_color, 0, 1)
        g_style.addWidget(self.combo_linestyle, 0, 2)
        g_style.addWidget(QLabel("Guide Line:"), 1, 0)
        g_style.addWidget(self.btn_base_color, 1, 1)
        g_style.addWidget(self.combo_base_style, 1, 2)
        g_style.addWidget(QLabel("Window Fill:"), 2, 0)
        g_style.addWidget(self.btn_area_color, 2, 1)
        g_style.addWidget(self.spin_alpha, 2, 2)

        # Coord Group
        gb_coord = QGroupBox("📉 Phase Coordinates")
        g_coord = QGridLayout(gb_coord)

        def cl(cls):
            l = QLabel("-")
            l.setProperty("class", cls)
            return l

        self.lbl_p_start_t = cl("coord-value")
        self.lbl_p_start_d = cl("coord-value")
        self.lbl_p_peak_t = cl("coord-value")
        self.lbl_p_peak_d = cl("coord-value")
        self.lbl_p_end_t = cl("coord-value")
        self.lbl_p_end_d = cl("coord-value")
        g_coord.addWidget(QLabel("Point"), 0, 0)
        g_coord.addWidget(QLabel("Temp (°C)"), 0, 1)
        g_coord.addWidget(QLabel("DTG"), 0, 2)
        g_coord.addWidget(QLabel("Onset:"), 1, 0)
        g_coord.addWidget(self.lbl_p_start_t, 1, 1)
        g_coord.addWidget(self.lbl_p_start_d, 1, 2)
        g_coord.addWidget(QLabel("Peak:"), 2, 0)
        g_coord.addWidget(self.lbl_p_peak_t, 2, 1)
        g_coord.addWidget(self.lbl_p_peak_d, 2, 2)
        g_coord.addWidget(QLabel("Endset:"), 3, 0)
        g_coord.addWidget(self.lbl_p_end_t, 3, 1)
        g_coord.addWidget(self.lbl_p_end_d, 3, 2)

        top_h.addWidget(gb_style, 3)
        top_h.addWidget(gb_coord, 2)
        layout.addWidget(top_ctrl)

        # Plot Canvas
        plot_cont = QWidget()
        plot_cont.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #e1e4e8;")
        plot_lay = QVBoxLayout(plot_cont)
        self.canvas = MplCanvas(self)
        self.toolbar = CustomToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: transparent; border: none;")
        btn_save = QPushButton("📸 Save Image")
        btn_save.setStyleSheet("background-color: #2c3e50; color: white;")
        btn_save.clicked.connect(self.save_high_res_plot)
        th = QHBoxLayout()
        th.addWidget(self.toolbar)
        th.addStretch()
        th.addWidget(btn_save)
        plot_lay.addLayout(th)
        plot_lay.addWidget(self.canvas)
        layout.addWidget(plot_cont, stretch=1)

        return widget

    def _make_spin(self, label, layout, min_v, max_v, default):
        layout.addWidget(QLabel(label))
        sb = QDoubleSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(default)
        sb.setDecimals(2)
        sb.setKeyboardTracking(False)
        layout.addWidget(sb)
        return sb

    def _load_config(self):
        self.spin_rate.setValue(self._safe_float("rate", DEFAULT_HEATING_RATE))
        self.spin_width.setValue(self._safe_float("width", DEFAULT_INTEGRATION_WIDTH))
        self.chk_smooth.setChecked(self.settings.value("smooth", False, type=bool))
        self.combo_ref_mode.setCurrentText(str(self.settings.value("ref_mode", DEFAULT_REF_MODE)))
        self.combo_bound_mode.setCurrentText(str(self.settings.value("bound_water_mode", DEFAULT_BOUND_WATER_MODE)))
        self.spin_alpha.setValue(self.style_cfg['area_alpha'])
        try:
            self.combo_linestyle.setCurrentIndex(self.line_styles_map.index(self.style_cfg['line_style']))
        except ValueError:
            pass
        try:
            self.combo_base_style.setCurrentIndex(self.line_styles_map.index(self.style_cfg['base_style']))
        except ValueError:
            pass
        self._pick_color('line_color', self.btn_line_color, dry=True)
        self._pick_color('base_color', self.btn_base_color, dry=True)
        self._pick_color('area_color', self.btn_area_color, dry=True)

    def _safe_float(self, key, default):
        try:
            return float(self.settings.value(key, default))
        except Exception:
            return default

    def _current_ref_mode(self) -> str:
        return self.combo_ref_mode.currentText() if hasattr(self, "combo_ref_mode") else DEFAULT_REF_MODE

    def _current_bound_water_mode(self) -> str:
        return self.combo_bound_mode.currentText() if hasattr(self, "combo_bound_mode") else DEFAULT_BOUND_WATER_MODE

    def _pick_color(self, key, btn, dry=False):
        if not dry:
            c = QColorDialog.getColor(QColor(self.style_cfg[key]), title="Select Color")
            if c.isValid():
                self.style_cfg[key] = c.name()
                self.settings.setValue(key, c.name())
                self.update_plot_appearance()
        btn.setStyleSheet(f"background-color: {self.style_cfg[key]}; border: 1px solid #999; border-radius: 4px;")

    def on_phase_changed(self):
        phase = self.combo_target_phase.currentText()
        if "CH" in phase:
            self.w_range_params.hide()
            self.w_ch_params.show()
        else:
            self.w_ch_params.hide()
            self.w_range_params.show()
            start, end = self.phase_ranges.get(phase, (0.0, 0.0))
            self.spin_t_start.blockSignals(True)
            self.spin_t_end.blockSignals(True)
            self.spin_t_start.setValue(start)
            self.spin_t_end.setValue(end)
            self.spin_t_start.blockSignals(False)
            self.spin_t_end.blockSignals(False)
        self.run_analysis()

    def on_range_changed(self):
        phase = self.combo_target_phase.currentText()
        if "CH" not in phase:
            self.phase_ranges[phase] = (self.spin_t_start.value(), self.spin_t_end.value())
            self.run_analysis()

    def copy_results_to_clipboard(self) -> None:
        if not self.current_summary:
            QMessageBox.warning(self, "未就绪", "没有可复制的计算结果，请先点击 Update Calculation。")
            return

        sample_name = self.combo_samples.currentText()
        header = (
            "Sample\tCH Peak Temp (°C)\tCH Net (%)\tBound Water Wn (%)\t"
            "CaCO3 (%)\tFriedel's Salt (%)\tHydrate Index (%)\tMass Basis\tBound Water Mode"
        )
        data_row = (
            f"{sample_name}\t{self.current_summary.get('Peak Temp (°C)', np.nan):.2f}\t"
            f"{self.current_summary.get('CH Net (%)', 0.0):.2f}\t"
            f"{self.current_summary.get('Wn (%)', 0.0):.2f}\t"
            f"{self.current_summary.get('CaCO3 (%)', 0.0):.2f}\t"
            f"{self.current_summary.get('Fs (%)', 0.0):.2f}\t"
            f"{self.current_summary.get('Hydrate Index (%)', 0.0):.2f}\t"
            f"{self._current_ref_mode()}\t{self._current_bound_water_mode()}"
        )

        QApplication.clipboard().setText(f"{header}\n{data_row}")

        self._cached_copy_text = self.btn_copy.text()
        self._cached_copy_style = self.btn_copy.styleSheet()

        self.btn_copy.setText("✔️ 已复制 (Copied!)")
        self.btn_copy.setStyleSheet("""
            background-color: #2da44e; 
            color: white; 
            border-radius: 6px; 
            padding: 6px 12px; 
            font-weight: bold;
        """)

        QTimer.singleShot(1500, self._restore_copy_button_state)
        self.status_bar.showMessage("✅ 结果已复制到剪贴板，可直接粘贴至 Excel", 3000)

    def _restore_copy_button_state(self) -> None:
        if hasattr(self, '_cached_copy_text'):
            self.btn_copy.setText(self._cached_copy_text)
            self.btn_copy.setStyleSheet(self._cached_copy_style)

    def save_high_res_plot(self):
        if self.current_dtg is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Figure", f"{self.combo_samples.currentText()}_Plot.png",
                                              "PNG Image (*.png);;PDF (*.pdf)")
        if path:
            self.canvas.figure.savefig(path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Success", "Image saved!")

    def on_load_click(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "Excel (*.xlsx)")
        if not path:
            return
        self.btn_load.setEnabled(False)
        self.pbar.show()
        self.lbl_status.setText("Reading...")
        self.worker = DataLoaderThread(path)
        self.worker.finished.connect(self.on_load_success)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def on_load_success(self, data, samples):
        self.data_store, self.sample_list = data, samples
        self.pbar.hide()
        self.btn_load.setEnabled(True)
        self.lbl_status.setText(f"Loaded {len(samples)}")
        self.combo_samples.blockSignals(True)
        self.combo_samples.clear()
        self.combo_samples.addItems(samples)
        self.combo_samples.blockSignals(False)
        self.btn_export.setEnabled(True)
        self.btn_copy.setEnabled(True)
        self.run_analysis()

    def on_load_error(self, error_text):
        self.pbar.hide()
        self.btn_load.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self.lbl_status.setText("Load failed")
        QMessageBox.critical(self, "Error", error_text)

    def _calculate_summary(self, tg, dtg):
        ref_mode = self._current_ref_mode()
        bound_mode = self._current_bound_water_mode()
        ch_result = calculate_ch_content(
            tg, dtg, self.spin_rate.value(), self.spin_width.value(), ref_mode=ref_mode
        )
        co2_loss = calculate_co2_loss(tg, self.phase_ranges["CaCO3 (Carbonation)"], ref_mode=ref_mode)
        summary = {
            "Peak Temp (°C)": ch_result["t_peak"] if ch_result else np.nan,
            "CH Net (%)": ch_result["ch_corrected"] if ch_result else 0.0,
            "Wn (%)": calculate_bound_water(tg, co2_loss, mode=bound_mode, ref_mode=ref_mode),
            "CaCO3 (%)": calculate_carbonation(tg, self.phase_ranges["CaCO3 (Carbonation)"], ref_mode=ref_mode),
            "Fs (%)": calculate_friedels_salt(tg, self.phase_ranges["Friedel's Salt"], ref_mode=ref_mode),
            "Hydrate Index (%)": calculate_csh_estimation(
                tg, self.phase_ranges["Hydrate Index (50-200 °C)"], ref_mode=ref_mode
            ),
            "ref_mode": ref_mode,
            "bound_water_mode": bound_mode,
        }
        return ch_result, summary

    def run_analysis(self):
        name = self.combo_samples.currentText()
        if not name or name not in self.data_store:
            return

        tg, dtg = self.data_store[name]['tg'].copy(), self.data_store[name]['dtg'].copy()
        if self.chk_smooth.isChecked():
            dtg['DTG'] = safe_smooth(dtg['DTG'])

        self.current_result, self.current_summary = self._calculate_summary(tg, dtg)
        self.current_dtg = dtg

        self.current_val_caco3 = self.current_summary["CaCO3 (%)"]
        self.current_val_wn = self.current_summary["Wn (%)"]
        self.current_val_fs = self.current_summary["Fs (%)"]
        self.current_val_csh = self.current_summary["Hydrate Index (%)"]

        if self.current_result:
            self.lbl_peak.setText(f"{self.current_result['t_peak']:.1f} °C")
            self.lbl_ch_net.setText(f"{self.current_result['ch_corrected']:.2f} %")
        else:
            self.lbl_peak.setText("-")
            self.lbl_ch_net.setText("-")

        self.lbl_wn.setText(f"{self.current_val_wn:.2f} %")
        self.lbl_caco3.setText(f"{self.current_val_caco3:.2f} %")
        self.lbl_fs.setText(f"{self.current_val_fs:.2f} %")
        self.lbl_hydrate.setText(f"{self.current_val_csh:.2f} %")

        self.settings.setValue("rate", self.spin_rate.value())
        self.settings.setValue("width", self.spin_width.value())
        self.settings.setValue("smooth", self.chk_smooth.isChecked())
        self.settings.setValue("ref_mode", self._current_ref_mode())
        self.settings.setValue("bound_water_mode", self._current_bound_water_mode())

        self.status_bar.showMessage(
            f"Mass basis: {self._current_ref_mode()} | Wn mode: {self._current_bound_water_mode()} | DTG assumed: %/min",
            5000,
        )

        self.plot_result(dtg, self.current_result, name)

    def update_plot_appearance(self):
        self.style_cfg.update({'area_alpha': self.spin_alpha.value(),
                               'line_style': self.line_styles_map[self.combo_linestyle.currentIndex()],
                               'base_style': self.line_styles_map[self.combo_base_style.currentIndex()]})
        for k, v in self.style_cfg.items():
            self.settings.setValue(k, v)
        if self.current_dtg is not None:
            self.plot_result(self.current_dtg, self.current_result, self.combo_samples.currentText())

    def plot_result(self, dtg_df, res, title):
        ax = self.canvas.axes
        ax.clear()
        if dtg_df is None or dtg_df.empty:
            self.canvas.draw()
            return

        s, phase = self.style_cfg, self.combo_target_phase.currentText()

        if "CH" in phase:
            t_min, t_max = 300, 600
        elif "CaCO3" in phase:
            t_min, t_max = 500, 900
        elif "Friedel" in phase:
            t_min, t_max = 200, 500
        elif "Bound" in phase:
            t_min, t_max = 30, dtg_df['Temp'].max() + 50
        else:
            t_min, t_max = 30, 300

        sub = dtg_df[(dtg_df['Temp'] >= t_min) & (dtg_df['Temp'] <= t_max)]
        if sub.empty:
            self.canvas.draw()
            return

        ax.plot(sub['Temp'], sub['DTG'], color=s['line_color'], linestyle=s['line_style'], linewidth=s['line_width'],
                label='DTG', zorder=2)
        c_s_t, c_s_d, c_p_t, c_p_d, c_e_t, c_e_d, display_res = "-", "-", "-", "-", "-", "-", ""

        if "CH" in phase and res:
            t_s, t_e, d_s, d_e, t_p = res['t_start'], res['t_end'], res['val_start'][1], res['val_end'][1], res['t_peak']
            ax.plot([t_s, t_e], [d_s, d_e], color=s['base_color'], linestyle=s['base_style'], linewidth=1.5,
                    label='Endpoint baseline', zorder=3)
            fill_mask = (sub['Temp'] >= t_s) & (sub['Temp'] <= t_e)
            ax.fill_between(sub['Temp'], sub['DTG'], np.interp(sub['Temp'], [t_s, t_e], [d_s, d_e]), where=fill_mask,
                            color=s['area_color'], alpha=s['area_alpha'], label='Corrected CH region')
            peak_d = dtg_df.loc[dtg_df['Temp'] == t_p, 'DTG'].values[0]
            ax.scatter(t_p, peak_d, c=s['line_color'], s=40 * s['line_width'], zorder=4)
            c_s_t, c_s_d, c_p_t, c_p_d, c_e_t, c_e_d = (
                f"{t_s:.1f}", f"{d_s:.3f}", f"{t_p:.1f}", f"{peak_d:.3f}", f"{t_e:.1f}", f"{d_e:.3f}"
            )
            display_res = f"Net CH: {res['ch_corrected']:.2f}%\nMass basis: {self._current_ref_mode()}"
        elif "CH" not in phase:
            f_s, f_e = self.phase_ranges.get(phase, (0, 0))
            s_idx, e_idx = (dtg_df['Temp'] - f_s).abs().idxmin(), (dtg_df['Temp'] - f_e).abs().idxmin()
            t_s, t_e = dtg_df.loc[s_idx, 'Temp'], dtg_df.loc[e_idx, 'Temp']
            d_s, d_e = dtg_df.loc[s_idx, 'DTG'], dtg_df.loc[e_idx, 'DTG']
            ax.plot([t_s, t_e], [d_s, d_e], color=s['base_color'], linestyle=s['base_style'], linewidth=1.5,
                    label='Window guide', zorder=3)
            ax.fill_between(sub['Temp'], sub['DTG'], np.interp(sub['Temp'], [t_s, t_e], [d_s, d_e]),
                            where=(sub['Temp'] >= min(t_s, t_e)) & (sub['Temp'] <= max(t_s, t_e)),
                            color=s['area_color'], alpha=s['area_alpha'], label='Selected window')
            c_s_t, c_s_d, c_e_t, c_e_d = f"{t_s:.1f}", f"{d_s:.3f}", f"{t_e:.1f}", f"{d_e:.3f}"
            if "CaCO3" in phase:
                display_res = f"CaCO3: {self.current_val_caco3:.2f}%\nTG mass-loss window"
            elif "Friedel" in phase:
                display_res = f"Fs eq.: {self.current_val_fs:.2f}%\nTG mass-loss window"
            elif "Bound" in phase:
                display_res = f"Wn: {self.current_val_wn:.2f}%\nMode: {self._current_bound_water_mode()}"
            elif "Hydrate" in phase:
                display_res = f"Hydrate Index: {self.current_val_csh:.2f}%\nTG mass-loss index"

        self.lbl_p_start_t.setText(c_s_t)
        self.lbl_p_start_d.setText(c_s_d)
        self.lbl_p_peak_t.setText(c_p_t)
        self.lbl_p_peak_d.setText(c_p_d)
        self.lbl_p_end_t.setText(c_e_t)
        self.lbl_p_end_d.setText(c_e_d)
        ax.set_title(f"Sample: {title}  |  Target: {phase.split(' (')[0]}", fontweight='bold')
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("DTG (%/min, assumed)")
        ax.grid(True, linestyle=':', alpha=0.5)

        if display_res:
            self._draggable_annotation = ax.annotate(f"{phase.split(' (')[0]}\n{display_res}", xy=(0.03, 0.95),
                                                     xycoords='axes fraction', fontsize=11, fontweight='bold',
                                                     bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=s['line_color'],
                                                               lw=1.5, alpha=0.9), va='top', ha='left')
            if hasattr(self._draggable_annotation, 'draggable'):
                self._draggable_annotation.draggable(True)

        leg = ax.legend(loc='upper right', frameon=True)
        leg.set_draggable(True)
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export", "Report.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            rows = []
            for n in self.sample_list:
                tg = self.data_store[n]['tg']
                dtg = self.data_store[n]['dtg'].copy()
                if self.chk_smooth.isChecked():
                    dtg['DTG'] = safe_smooth(dtg['DTG'])
                summary = calculate_sample_summary(
                    tg,
                    dtg,
                    heating_rate=self.spin_rate.value(),
                    integration_width=self.spin_width.value(),
                    caco3_range=self.phase_ranges["CaCO3 (Carbonation)"],
                    friedels_range=self.phase_ranges["Friedel's Salt"],
                    csh_range=self.phase_ranges["Hydrate Index (50-200 °C)"],
                    ref_mode=self._current_ref_mode(),
                    bound_water_mode=self._current_bound_water_mode(),
                )
                rows.append({"Sample Name": n, **summary})

            pd.DataFrame(rows).to_excel(path, index=False)
            self.status_bar.showMessage("Export Complete", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
