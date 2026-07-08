# src/ui_components.py

import traceback
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget
import matplotlib

matplotlib.use('QtAgg')  # 防御性声明，确保后端不冲突
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from src.data_loader import load_tga_data
from src.config import DPI


class DataLoaderThread(QThread):
    finished = pyqtSignal(dict, list)
    error = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.path = file_path

    def run(self):
        try:
            data = load_tga_data(self.path)
            self.finished.emit(data, list(data.keys()))
        except Exception:
            self.error.emit(traceback.format_exc())


class CustomToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        # 防御性编程：禁止在遍历动态列表时直接 remove，应先收集再集中清理
        actions_to_remove = []
        for action in self.actions():
            if action.text() in ['Customize', 'Subplots'] or (action.toolTip() and 'configuration' in action.toolTip()):
                actions_to_remove.append(action)
        for action in actions_to_remove:
            self.removeAction(action)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent: QWidget = None, width: float = 5.0, height: float = 4.0, dpi: int = DPI):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # NOTE: 严禁在此处调用 fig.tight_layout()！由于此时 Canvas 尚未与 Qt 主窗口完成绑定，
        # 底层 renderer 不存在，部分 Matplotlib 版本会直接引发 C++ 级 Segfault 导致闪退。
        super().__init__(fig)
        if parent:
            self.setParent(parent)