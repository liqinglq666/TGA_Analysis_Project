from __future__ import annotations

import traceback

import matplotlib
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from src.config import DPI
from src.data_loader import load_tga_data


class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(dict, list)
    error = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.path = file_path

    @property
    def finished(self):
        # main.py 还在用旧名字，先留个兼容口。
        return self.data_loaded

    def run(self):
        try:
            data = load_tga_data(self.path)
            self.data_loaded.emit(data, list(data))
        except Exception:
            self.error.emit(traceback.format_exc())


class CustomToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        for action in list(self.actions()):
            tooltip = action.toolTip() or ""
            if action.text() in {"Customize", "Subplots"} or "configuration" in tooltip:
                self.removeAction(action)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(
        self,
        parent: QWidget | None = None,
        width: float = 5.0,
        height: float = 4.0,
        dpi: int = DPI,
    ):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # tight_layout 在 Qt renderer 起来前偶发 C++ 崩溃，别挪回来。
        super().__init__(fig)
        if parent:
            self.setParent(parent)
