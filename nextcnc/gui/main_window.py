"""
NextCNC main window: dashboard with 3D simulation widget and File menu.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from nextcnc.core.parser import parse_file
from nextcnc.core.kinematics import segments_to_points
from nextcnc.simulation.renderer import SimulationWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NextCNC - G-Code Simulation")
        self.setMinimumSize(800, 600)
        self.resize(1024, 768)

        self._sim_widget = SimulationWidget(self)
        self.setCentralWidget(self._sim_widget)

        self._build_menu()
        self.statusBar().showMessage("Dosya → G-Code Aç (Ctrl+O) ile NC dosyası yükleyin.")

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        open_act = file_menu.addAction("&Open G-Code...")
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._on_open)
        file_menu.addSeparator()
        exit_act = file_menu.addAction("E&xit")
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open G-Code File",
            "",
            "NC Files (*.nc *.ncg *.gcode *.txt);;All Files (*)",
        )
        if not path:
            return
        self._load_gcode(path)

    def _load_gcode(self, path: str) -> None:
        try:
            segments = parse_file(path, metric=True)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Parse Error",
                f"Failed to parse G-Code:\n{e}",
            )
            return
        points = segments_to_points(segments, num_samples=32, connect=True)
        self._sim_widget.set_points(points)
        self.setWindowTitle(f"NextCNC - {Path(path).name}")
        self.statusBar().showMessage(f"Yüklendi: {Path(path).name} — {len(points)} nokta")
