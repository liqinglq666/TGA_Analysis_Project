import sys
import os
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use('QtAgg')

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFileDialog, QDoubleSpinBox,
    QMessageBox, QGroupBox, QCheckBox, QProgressBar, QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QIcon, QAction

# 引入 Matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 引入平滑算法
from scipy.signal import savgol_filter

# 引入我们写好的模块
from src.data_loader import load_tga_data
from src.calculator import calculate_ch_content

# 设置字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


# --- 1. 后台加载线程 (防止界面卡死) ---
class DataLoaderThread(QThread):
    finished = pyqtSignal(dict, list)  # 信号：传回数据字典和样品列表
    error = pyqtSignal(str)  # 信号：传回错误信息

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            # 调用原本的加载逻辑
            data_dict = load_tga_data(self.file_path)
            sample_list = list(data_dict.keys())
            self.finished.emit(data_dict, sample_list)
        except Exception as e:
            self.error.emit(str(e))


# --- 2. 绘图画布 ---
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        # 优化布局，防止坐标轴文字被切掉
        self.fig.tight_layout()
        super(MplCanvas, self).__init__(self.fig)


# --- 3. 主窗口 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TGA-CH Analysis Pro (Research Grade)")
        self.resize(1280, 850)

        # 持久化设置 (记住上次的参数)
        self.settings = QSettings("MyLab", "TGA_Analyzer")

        self.data_dict = {}
        self.sample_list = []
        self.loader_thread = None

        self.init_ui()
        self.load_settings()  # 加载上次的设置

    def init_ui(self):
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # === 左边栏：控制面板 ===
        panel = QVBoxLayout()
        panel.setSpacing(15)

        # 1. 标题区
        lbl_title = QLabel("TGA 科研分析工具 v2.0")
        lbl_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel.addWidget(lbl_title)

        # 2. 文件操作
        grp_file = QGroupBox("1. 数据导入")
        vbox_file = QVBoxLayout()
        self.btn_load = QPushButton(" 加载 Excel 数据")
        self.btn_load.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; font-weight: bold; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_load.clicked.connect(self.on_load_file)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # 默认隐藏
        self.progress_bar.setRange(0, 0)  # 忙碌模式 (跑马灯)

        self.lbl_file_status = QLabel("未加载文件")
        self.lbl_file_status.setStyleSheet("color: gray; font-style: italic;")
        self.lbl_file_status.setWordWrap(True)

        vbox_file.addWidget(self.btn_load)
        vbox_file.addWidget(self.progress_bar)
        vbox_file.addWidget(self.lbl_file_status)
        grp_file.setLayout(vbox_file)
        panel.addWidget(grp_file)

        # 3. 参数设置
        grp_param = QGroupBox("2. 实验参数")
        vbox_param = QVBoxLayout()

        # 升温速率
        hbox_rate = QHBoxLayout()
        hbox_rate.addWidget(QLabel("升温速率 (°C/min):"))
        self.spin_rate = QDoubleSpinBox()
        self.spin_rate.setRange(0.1, 100.0)
        self.spin_rate.setValue(10.0)
        self.spin_rate.valueChanged.connect(self.save_and_refresh)
        hbox_rate.addWidget(self.spin_rate)
        vbox_param.addLayout(hbox_rate)

        # 积分宽度
        hbox_width = QHBoxLayout()
        hbox_width.addWidget(QLabel("积分宽度 (±°C):"))
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(5.0, 100.0)
        self.spin_width.setValue(40.0)
        self.spin_width.valueChanged.connect(self.save_and_refresh)
        hbox_width.addWidget(self.spin_width)
        vbox_param.addLayout(hbox_width)

        # 数据平滑 (新增功能)
        self.chk_smooth = QCheckBox("启用 DTG 平滑 (去噪)")
        self.chk_smooth.setToolTip("使用 Savitzky-Golay 滤波器去除数据毛刺，使找峰更准确")
        self.chk_smooth.toggled.connect(self.save_and_refresh)
        vbox_param.addWidget(self.chk_smooth)

        grp_param.setLayout(vbox_param)
        panel.addWidget(grp_param)

        # 4. 样品选择
        grp_sample = QGroupBox("3. 样品分析")
        vbox_sample = QVBoxLayout()
        self.combo_samples = QComboBox()
        self.combo_samples.currentIndexChanged.connect(self.refresh_analysis)
        vbox_sample.addWidget(QLabel("当前查看样品:"))
        vbox_sample.addWidget(self.combo_samples)
        grp_sample.setLayout(vbox_sample)
        panel.addWidget(grp_sample)

        # 5. 结果显示卡片
        grp_res = QGroupBox("计算结果")
        grp_res.setStyleSheet("""
            QGroupBox { border: 2px solid #3498db; border-radius: 8px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #3498db; font-weight: bold; }
        """)
        vbox_res = QVBoxLayout()

        self.lbl_t_peak = QLabel("峰值温度: -")
        self.lbl_ch_trad = QLabel("传统法 CH: -")
        self.lbl_ch_corr = QLabel("修正后 CH: -")

        # 结果高亮
        self.lbl_ch_corr.setStyleSheet("font-size: 20px; color: #e74c3c; font-weight: bold; margin: 5px 0;")

        vbox_res.addWidget(self.lbl_t_peak)
        vbox_res.addWidget(self.lbl_ch_trad)
        vbox_res.addWidget(self.lbl_ch_corr)
        grp_res.setLayout(vbox_res)
        panel.addWidget(grp_res)

        # 6. 导出
        self.btn_export = QPushButton(" 导出完整报表 (.xlsx)")
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 12px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.btn_export.clicked.connect(self.on_export)
        self.btn_export.setEnabled(False)
        panel.addWidget(self.btn_export)

        panel.addStretch()
        layout.addLayout(panel, 3)  # 左侧占比 3

        # === 右边栏：绘图区 ===
        plot_layout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        # 稍微美化一下工具栏
        self.toolbar.setStyleSheet("background-color: #ecf0f1; border-bottom: 1px solid #ccc;")

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        frame = QGroupBox("DTG 动态积分示意图")
        frame.setStyleSheet("font-weight: bold;")
        frame.setLayout(plot_layout)
        layout.addWidget(frame, 7)  # 右侧占比 7

    def load_settings(self):
        """加载上次的配置"""
        val_rate = self.settings.value("heating_rate", 10.0, type=float)
        val_width = self.settings.value("integration_width", 40.0, type=float)
        val_smooth = self.settings.value("enable_smooth", False, type=bool)

        self.spin_rate.setValue(val_rate)
        self.spin_width.setValue(val_width)
        self.chk_smooth.setChecked(val_smooth)

    def save_and_refresh(self):
        """保存配置并刷新图表"""
        self.settings.setValue("heating_rate", self.spin_rate.value())
        self.settings.setValue("integration_width", self.spin_width.value())
        self.settings.setValue("enable_smooth", self.chk_smooth.isChecked())

        self.refresh_analysis()

    def on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Excel", "", "Excel Files (*.xlsx *.xls)")
        if not path: return

        # UI 状态切换
        self.btn_load.setEnabled(False)
        self.btn_load.setText("正在加载...")
        self.progress_bar.setVisible(True)
        self.lbl_file_status.setText("正在解析 Excel，请稍候...")
        self.status_bar.showMessage("正在读取数据...")

        # 启动后台线程
        self.loader_thread = DataLoaderThread(path)
        self.loader_thread.finished.connect(self.on_load_success)
        self.loader_thread.error.connect(self.on_load_error)
        self.loader_thread.start()

    def on_load_success(self, data_dict, sample_list):
        self.data_dict = data_dict
        self.sample_list = sample_list

        # UI 恢复
        self.btn_load.setEnabled(True)
        self.btn_load.setText(" 加载 Excel 数据")
        self.progress_bar.setVisible(False)

        self.combo_samples.blockSignals(True)  # 暂时屏蔽信号，防止清空时触发刷新
        self.combo_samples.clear()
        self.combo_samples.addItems(self.sample_list)
        self.combo_samples.blockSignals(False)

        # 显示文件名（只取文件名，不含路径）
        filename = os.path.basename(self.loader_thread.file_path)
        self.lbl_file_status.setText(f"当前文件: {filename}")
        self.lbl_file_status.setStyleSheet("color: #27ae60; font-weight: bold;")

        self.btn_export.setEnabled(True)
        self.status_bar.showMessage(f"成功加载 {len(sample_list)} 个样品", 5000)

        # 触发第一次绘图
        self.refresh_analysis()
        QMessageBox.information(self, "加载成功", f"成功读取 {len(sample_list)} 个样品！\n\n请在左侧下拉框切换样品查看。")

    def on_load_error(self, err_msg):
        self.btn_load.setEnabled(True)
        self.btn_load.setText(" 加载 Excel 数据")
        self.progress_bar.setVisible(False)
        self.lbl_file_status.setText("加载失败")
        self.lbl_file_status.setStyleSheet("color: red;")
        self.status_bar.showMessage("加载失败", 5000)
        QMessageBox.critical(self, "错误", f"读取文件失败: {err_msg}")

    def refresh_analysis(self):
        if not self.data_dict: return

        sample = self.combo_samples.currentText()
        if not sample: return

        data = self.data_dict[sample]
        tg_df = data['tg'].copy()
        dtg_df = data['dtg'].copy()

        # --- 优化点：数据平滑处理 ---
        if self.chk_smooth.isChecked() and len(dtg_df) > 15:
            try:
                # 窗口长度 15，多项式阶数 3 (经验值)
                dtg_df['DTG'] = savgol_filter(dtg_df['DTG'], window_length=15, polyorder=3)
            except:
                pass  # 如果数据太短，就不平滑

        result = calculate_ch_content(
            tg_df,
            dtg_df,
            heating_rate=self.spin_rate.value(),
            integration_width=self.spin_width.value()
        )

        self.draw_plot(dtg_df, result, sample)
        self.update_labels(result)

    def update_labels(self, res):
        if res:
            self.lbl_t_peak.setText(f"峰值温度: {res['t_peak']:.1f} °C")
            self.lbl_ch_trad.setText(f"传统法 CH: {res['ch_traditional']:.2f}%")
            self.lbl_ch_corr.setText(f"修正后 CH: {res['ch_corrected']:.2f}%")
        else:
            self.lbl_t_peak.setText("峰值温度: 未检测到")
            self.lbl_ch_trad.setText("传统法 CH: -")
            self.lbl_ch_corr.setText("修正后 CH: 0.00%")

    def draw_plot(self, dtg_df, res, title):
        ax = self.canvas.axes
        ax.clear()

        # 绘图范围
        mask = (dtg_df['Temp'] > 300) & (dtg_df['Temp'] < 600)
        sub = dtg_df[mask]

        # 绘制 DTG 主线
        label_text = 'DTG Curve'
        if self.chk_smooth.isChecked(): label_text += ' (Smoothed)'
        ax.plot(sub['Temp'], sub['DTG'], 'k-', label=label_text, linewidth=1.5, zorder=1)

        if res:
            t_s, t_e = res['t_start'], res['t_end']
            d_s, d_e = res['val_start'][1], res['val_end'][1]

            # 绘制基线
            ax.plot([t_s, t_e], [d_s, d_e], 'r--', label='Baseline (C-S-H)', linewidth=1.5, zorder=2)

            # 填充积分区域
            base_vals = np.interp(sub['Temp'], [t_s, t_e], [d_s, d_e])
            fill_mask = (sub['Temp'] >= t_s) & (sub['Temp'] <= t_e)

            ax.fill_between(sub['Temp'], sub['DTG'], base_vals,
                            where=fill_mask, color='dodgerblue', alpha=0.3, label='Integrated CH Area', zorder=0)

            # 标记起点终点
            ax.scatter([t_s, t_e], [d_s, d_e], c='red', s=30, zorder=3)

            # 在图上标注峰温
            ax.annotate(f"Peak: {res['t_peak']:.1f}°C",
                        xy=(res['t_peak'], sub.loc[sub['Temp'].sub(res['t_peak']).abs().idxmin(), 'DTG']),
                        xytext=(0, -20), textcoords='offset points', ha='center', color='blue')

        ax.set_title(f"Sample: {title}", fontsize=12, fontweight='bold')
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("DTG (%/min)")
        ax.legend(loc='lower right')
        ax.grid(True, linestyle=':', alpha=0.5)

        self.canvas.draw()

    def on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存报表", "CH_Analysis_Report.xlsx", "Excel Files (*.xlsx)")
        if not path: return

        self.status_bar.showMessage("正在导出...")
        export_data = []

        # 需要重新计算一遍所有样品，确保使用的是当前参数
        for sample in self.sample_list:
            data = self.data_dict[sample]
            tg, dtg = data['tg'].copy(), data['dtg'].copy()

            # 导出时同样应用平滑
            if self.chk_smooth.isChecked() and len(dtg) > 15:
                try:
                    dtg['DTG'] = savgol_filter(dtg['DTG'], window_length=15, polyorder=3)
                except:
                    pass

            res = calculate_ch_content(
                tg, dtg,
                heating_rate=self.spin_rate.value(),
                integration_width=self.spin_width.value()
            )

            row = {'Sample': sample}
            if res:
                row.update({
                    'Peak_Temp': res['t_peak'],
                    'CH_Traditional (%)': res['ch_traditional'],
                    'CH_Corrected (%)': res['ch_corrected'],
                    'Background_Loss (%)': res['bg_loss_ch_equiv']
                })
            else:
                row.update({'Peak_Temp': '-', 'CH_Corrected (%)': 0})

            export_data.append(row)

        try:
            pd.DataFrame(export_data).to_excel(path, index=False)
            self.status_bar.showMessage("导出完成", 5000)
            QMessageBox.information(self, "完成", f"报表已保存至: {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setWindowIcon(QIcon('icon.png'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())