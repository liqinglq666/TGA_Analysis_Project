import sys
import os
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

# GUI Framework
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFileDialog, QDoubleSpinBox,
    QMessageBox, QGroupBox, QCheckBox, QProgressBar, QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QFont

# Plotting
import matplotlib

matplotlib.use('QtAgg')  # Force Qt backend
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Local Modules
from src.data_loader import load_tga_data
from src.calculator import calculate_ch_content
from src.config import *

# Global Style Setup
plt.rcParams['font.sans-serif'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False


class DataLoaderThread(QThread):
    """
    Offload heavy Excel parsing to prevent UI freeze.
    """
    finished = pyqtSignal(dict, list)
    error = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.path = file_path

    def run(self):
        try:
            data, samples = load_tga_data(self.path), []
            if data:
                samples = list(data.keys())
            self.finished.emit(data, samples)
        except Exception as e:
            self.error.emit(str(e))


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=DPI):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        fig.tight_layout()  # Fix label clipping
        super().__init__(fig)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGA-CH Analysis Pro")
        self.resize(1280, 850)

        # Persist user prefs (registry/ini)
        self.settings = QSettings("MyLab", "TGA_Analyzer")

        self.data_store = {}  # Raw data cache
        self.sample_list = []

        self._init_ui()
        self._load_last_config()

    def _init_ui(self):
        # ... (此处省略部分标准布局代码，和原版类似，但逻辑更紧凑) ...
        # 重点优化了下面的组件定义

        # Main Container
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # === Left Panel: Controls ===
        ctrl_panel = QVBoxLayout()
        ctrl_panel.setSpacing(15)

        # 1. File I/O
        gb_file = QGroupBox("1. Data Source")
        vb_file = QVBoxLayout()

        self.btn_load = QPushButton("Load Raw Excel")
        self.btn_load.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        self.btn_load.clicked.connect(self.on_load_click)

        self.pbar = QProgressBar()
        self.pbar.hide()

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: gray;")

        vb_file.addWidget(self.btn_load)
        vb_file.addWidget(self.pbar)
        vb_file.addWidget(self.lbl_status)
        gb_file.setLayout(vb_file)
        ctrl_panel.addWidget(gb_file)

        # 2. Params
        gb_param = QGroupBox("2. Parameters")
        vb_param = QVBoxLayout()

        self.spin_rate = self._create_spinbox("Heating Rate (°C/min):", vb_param, 0.1, 100, 10)
        self.spin_width = self._create_spinbox("Integration Width (±°C):", vb_param, 5, 100, 40)

        self.chk_smooth = QCheckBox("Enable Savitzky-Golay Smoothing")
        self.chk_smooth.setToolTip("Useful for noisy signals")
        self.chk_smooth.toggled.connect(self.on_param_change)
        vb_param.addWidget(self.chk_smooth)

        gb_param.setLayout(vb_param)
        ctrl_panel.addWidget(gb_param)

        # 3. Sample Selector
        self.combo_samples = QComboBox()
        self.combo_samples.currentIndexChanged.connect(self.run_analysis)
        ctrl_panel.addWidget(QLabel("Current Sample:"))
        ctrl_panel.addWidget(self.combo_samples)

        # 4. Dashboard
        gb_dash = QGroupBox("Results")
        vb_dash = QVBoxLayout()
        self.lbl_res_peak = QLabel("-")
        self.lbl_res_val = QLabel("-")
        self.lbl_res_val.setStyleSheet("font-size: 18px; color: #e74c3c; font-weight: bold;")

        vb_dash.addWidget(QLabel("Peak Temp:"))
        vb_dash.addWidget(self.lbl_res_peak)
        vb_dash.addWidget(QLabel("CH Content (Corrected):"))
        vb_dash.addWidget(self.lbl_res_val)
        gb_dash.setLayout(vb_dash)
        ctrl_panel.addWidget(gb_dash)

        # Export
        self.btn_export = QPushButton("Export Report (.xlsx)")
        self.btn_export.clicked.connect(self.on_export)
        self.btn_export.setEnabled(False)
        ctrl_panel.addWidget(self.btn_export)

        ctrl_panel.addStretch()
        layout.addLayout(ctrl_panel, 3)

        # === Right Panel: Plot ===
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        gb_plot = QGroupBox("Visual Analysis")
        gb_plot.setLayout(plot_layout)
        layout.addWidget(gb_plot, 7)

        # StatusBar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _create_spinbox(self, label, layout, min_v, max_v, default):
        layout.addWidget(QLabel(label))
        sb = QDoubleSpinBox()
        sb.setRange(min_v, max_v)
        sb.setValue(default)
        sb.valueChanged.connect(self.on_param_change)
        layout.addWidget(sb)
        return sb

    def _load_last_config(self):
        # Restore session state
        self.spin_rate.setValue(self.settings.value("rate", DEFAULT_HEATING_RATE, float))
        self.spin_width.setValue(self.settings.value("width", DEFAULT_INTEGRATION_WIDTH, float))
        self.chk_smooth.setChecked(self.settings.value("smooth", False, bool))

    def on_param_change(self):
        # Auto-save prefs
        self.settings.setValue("rate", self.spin_rate.value())
        self.settings.setValue("width", self.spin_width.value())
        self.settings.setValue("smooth", self.chk_smooth.isChecked())
        self.run_analysis()

    def on_load_click(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Data", "", "Excel (*.xlsx *.xls)")
        if not fname: return

        self.btn_load.setEnabled(False)
        self.pbar.setRange(0, 0)  # Indeterminate mode
        self.pbar.show()
        self.lbl_status.setText("Parsing large file...")

        self.worker = DataLoaderThread(fname)
        self.worker.finished.connect(self.on_data_ready)
        self.worker.error.connect(self.on_data_error)
        self.worker.start()

    def on_data_ready(self, data, samples):
        self.data_store = data
        self.sample_list = samples

        self.pbar.hide()
        self.btn_load.setEnabled(True)
        self.lbl_status.setText(f"Loaded {len(samples)} samples")
        self.lbl_status.setStyleSheet("color: green")

        self.combo_samples.blockSignals(True)
        self.combo_samples.clear()
        self.combo_samples.addItems(samples)
        self.combo_samples.blockSignals(False)

        self.btn_export.setEnabled(True)
        self.run_analysis()  # Trigger first plot

    def on_data_error(self, msg):
        self.pbar.hide()
        self.btn_load.setEnabled(True)
        QMessageBox.critical(self, "Load Error", f"Failed to parse file:\n{msg}")

    def run_analysis(self):
        if not self.data_store: return

        current_sample = self.combo_samples.currentText()
        raw = self.data_store.get(current_sample)
        if not raw: return

        tg, dtg = raw['tg'].copy(), raw['dtg'].copy()

        # Pre-processing
        if self.chk_smooth.isChecked() and len(dtg) > 15:
            # Window length 15 is empirical. Maybe make it adjustable later?
            dtg['DTG'] = savgol_filter(dtg['DTG'], 15, 3)

        res = calculate_ch_content(
            tg, dtg,
            heating_rate=self.spin_rate.value(),
            integration_width=self.spin_width.value()
        )

        self._update_plot(dtg, res, current_sample)
        self._update_dash(res)

    def _update_dash(self, res):
        if res:
            self.lbl_res_peak.setText(f"{res['t_peak']:.1f} °C")
            self.lbl_res_val.setText(f"{res['ch_corrected']:.2f} %")
        else:
            self.lbl_res_peak.setText("Not detected")
            self.lbl_res_val.setText("0.00 %")

    def _update_plot(self, dtg, res, title):
        ax = self.canvas.axes
        ax.clear()

        # Plot Logic
        # Filter for better visualization range (300-600)
        # TODO: Make range adjustable in UI?
        view_mask = (dtg['Temp'] > 300) & (dtg['Temp'] < 600)
        sub = dtg[view_mask]

        ax.plot(sub['Temp'], sub['DTG'], 'k-', lw=1.2, label='DTG Signal', zorder=2)

        if res:
            # Visualize integration area
            t_s, t_e = res['t_start'], res['t_end']
            d_s, d_e = res['val_start'][1], res['val_end'][1]

            # Baseline
            ax.plot([t_s, t_e], [d_s, d_e], 'r--', lw=1.5, label='Baseline', zorder=3)

            # Shade area
            base_interp = np.interp(sub['Temp'], [t_s, t_e], [d_s, d_e])
            fill_mask = (sub['Temp'] >= t_s) & (sub['Temp'] <= t_e)
            ax.fill_between(sub['Temp'], sub['DTG'], base_interp,
                            where=fill_mask, color='dodgerblue', alpha=0.4)

            # Peak marker
            ax.scatter(res['t_peak'], dtg.loc[dtg['Temp'] == res['t_peak'], 'DTG'],
                       c='blue', s=40, zorder=4)

        ax.set_title(f"Sample: {title}", fontweight='bold')
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("DTG (%/min)")
        ax.grid(True, ls=':', alpha=0.6)
        ax.legend()

        self.canvas.draw()

    def on_export(self):
        # Batch processing for export
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "CH_Report.xlsx", "Excel (*.xlsx)")
        if not path: return

        self.status_bar.showMessage("Generating report...")
        QApplication.processEvents()  # Keep UI responsive

        rows = []
        for name in self.sample_list:
            # Re-calc is fast enough, no need to cache everything
            raw = self.data_store[name]
            tg, dtg = raw['tg'], raw['dtg']

            # Apply same smoothing logic as UI
            if self.chk_smooth.isChecked():
                dtg = dtg.copy()  # Avoid warning
                dtg['DTG'] = savgol_filter(dtg['DTG'], 15, 3)

            res = calculate_ch_content(
                tg, dtg,
                self.spin_rate.value(),
                self.spin_width.value()
            )

            row = {'Sample': name}
            if res:
                row.update({
                    'Peak_Temp': res['t_peak'],
                    'CH_Content_Corrected': res['ch_corrected'],
                    'CH_Content_Raw': res['ch_traditional'],
                    'Baseline_Loss': res['bg_loss_ch_equiv']
                })
            else:
                row.update({'Peak_Temp': None, 'CH_Content_Corrected': 0})

            rows.append(row)

        try:
            pd.DataFrame(rows).to_excel(path, index=False)
            self.status_bar.showMessage("Done", 3000)
            QMessageBox.information(self, "Success", f"Report saved to:\n{path}")
        except PermissionError:
            QMessageBox.warning(self, "Error", "File is open in Excel. Close it and try again.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())