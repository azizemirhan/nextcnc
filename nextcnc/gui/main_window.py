"""
NextCNC main window: dashboard with 3D simulation and stock removal.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from nextcnc.qt_compat import QFileDialog, QMainWindow, QMessageBox, Qt
from nextcnc.qt_compat import QMenu, QMenuBar, QToolBar, QStatusBar
from nextcnc.qt_compat import QDockWidget, QWidget, QVBoxLayout, QLabel, QPushButton

from nextcnc.core.parser import parse_file
from nextcnc.core.kinematics import (
    segments_to_points,
    Kinematics3Axis,
    MachineConfig,
    process_segments_with_machine,
)
from nextcnc.simulation.renderer import SimulationWidget
from nextcnc.simulation.stock_model import (
    StockSimulator, StockConfig, Tool, ToolType
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NextCNC - G-Code Simulation")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Initialize components
        self.kinematics = Kinematics3Axis()
        self.stock_simulator = StockSimulator()
        self.current_tool = Tool(
            tool_id=1,
            name="D10 Flat",
            tool_type=ToolType.FLAT_ENDMILL,
            diameter=10.0,
            length=50.0
        )
        
        self.segments: list[dict] = []
        self.modal_state = None

        self._setup_ui()
        self._build_menu()
        
        self.statusBar().showMessage("Hazır - G-Code dosyası açın (Ctrl+O)")

    def _setup_ui(self) -> None:
        """Setup main UI components."""
        # Central 3D view
        self._sim_widget = SimulationWidget(self)
        self.setCentralWidget(self._sim_widget)
        
        # Stock info dock
        self._create_stock_dock()

    def _create_stock_dock(self) -> None:
        """Create stock information dock widget."""
        dock = QDockWidget("Stock Simülasyonu", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | 
                             Qt.DockWidgetArea.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Stock stats labels
        self._stock_total_label = QLabel("Toplam Hacim: -")
        self._stock_removed_label = QLabel("Kaldırılan: -")
        self._stock_percent_label = QLabel("İlerleme: -")
        self._stock_aircut_label = QLabel("Air-cut segment: -")
        
        layout.addWidget(self._stock_total_label)
        layout.addWidget(self._stock_removed_label)
        layout.addWidget(self._stock_percent_label)
        layout.addWidget(self._stock_aircut_label)
        
        layout.addStretch()
        
        # Simulate button
        sim_btn = QPushButton("Simülasyonu Başlat")
        sim_btn.clicked.connect(self._run_stock_simulation)
        layout.addWidget(sim_btn)
        
        # Reset button
        reset_btn = QPushButton("Stock'u Sıfırla")
        reset_btn.clicked.connect(self._reset_stock)
        layout.addWidget(reset_btn)
        
        widget.setLayout(layout)
        dock.setWidget(widget)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _build_menu(self) -> None:
        """Build menu bar."""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&Dosya")
        open_act = file_menu.addAction("&G-Code Aç...")
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._on_open)
        
        file_menu.addSeparator()
        exit_act = file_menu.addAction("Çı&kış")
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)
        
        # View Menu
        view_menu = menubar.addMenu("&Görünüm")
        reset_view_act = view_menu.addAction("&Kamerayı Sıfırla")
        reset_view_act.setShortcut("Ctrl+R")
        reset_view_act.triggered.connect(self._sim_widget.reset_view)
        
        toggle_stock_act = view_menu.addAction("Stock Gö&ster")
        toggle_stock_act.setCheckable(True)
        toggle_stock_act.setChecked(True)
        toggle_stock_act.triggered.connect(self._sim_widget.show_stock)
        
        # Settings Menu
        settings_menu = menubar.addMenu("&Ayarlar")
        load_machine_act = settings_menu.addAction("Makine &Konfigürasyonu...")
        load_machine_act.triggered.connect(self._on_load_machine)
        
        stock_config_act = settings_menu.addAction("Stock &Ayarları...")
        stock_config_act.triggered.connect(self._on_stock_config)

    def _on_open(self) -> None:
        """Open G-code file dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "G-Code Dosyası Aç",
            "",
            "NC Files (*.nc *.ncg *.gcode *.txt);;All Files (*)",
        )
        if not path:
            return
        self._load_gcode(path)

    def _on_load_machine(self) -> None:
        """Load machine configuration."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Makine Konfigürasyonu Yükle",
            "data/machines",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            config = MachineConfig.from_json(path)
            self.kinematics = Kinematics3Axis(config)
            self.statusBar().showMessage(f"Makine yüklendi: {config.name}")
            if self.segments:
                self._process_and_display()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Konfigürasyon yüklenemedi:\n{e}")

    def _on_stock_config(self) -> None:
        """Configure stock settings."""
        # For now, just reset with default config
        # In future, open a dialog
        self.stock_simulator = StockSimulator(StockConfig())
        self._update_stock_display()
        self.statusBar().showMessage("Stock ayarları sıfırlandı")

    def _load_gcode(self, path: str) -> None:
        """Load and parse G-code file."""
        try:
            self.segments = parse_file(path, metric=True)
        except Exception as e:
            QMessageBox.critical(self, "Parse Hatası", f"G-Code okunamadı:\n{e}")
            return
        
        self._process_and_display()
        self.setWindowTitle(f"NextCNC - {Path(path).name}")
        
        # Auto-run stock simulation
        self._run_stock_simulation()

    def _process_and_display(self) -> None:
        """Process segments and update display."""
        if not self.segments:
            return
        
        # Process with kinematics
        points, states = process_segments_with_machine(
            self.segments, self.kinematics, num_samples=32
        )
        
        # Check for limit errors
        limit_errors = [s for s in states if not s.limits_ok]
        if limit_errors:
            self.statusBar().showMessage(f"UYARI: {len(limit_errors)} noktada eksen limit aşımı")
        
        # Display toolpath
        self._sim_widget.set_points(points)
        
        # Show stats
        wcs_info = f"WCS: G{54 + self.kinematics.wcs.active_wcs}"
        pos = self.kinematics.current_state.position_work
        self.statusBar().showMessage(
            f"{len(points)} nokta | {wcs_info} | "
            f"Son pozisyon: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"
        )

    def _run_stock_simulation(self) -> None:
        """Run material removal simulation."""
        if not self.segments:
            QMessageBox.information(self, "Bilgi", "Önce G-Code dosyası açın")
            return
        
        try:
            self.statusBar().showMessage("Stok yapılandırılıyor...")
            
            # Configure stock to cover toolpath
            self._auto_configure_stock()
            
            # Check performance estimate
            perf = self.stock_simulator.config.estimate_performance()
            if perf["status"] == "HEAVY":
                reply = QMessageBox.question(
                    self, "Büyük Simülasyon",
                    f"Bu simülasyon {perf['total_xy_cells']:,} hücre içeriyor ve yavaş olabilir.\n"
                    "Devam etmek istiyor musunuz?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Run simulation with fewer samples for speed
            self.stock_simulator.set_tool(self.current_tool)
            self.statusBar().showMessage("Simülasyon çalışıyor...")
            
            # Process events to keep UI responsive
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            stats = self.stock_simulator.simulate_toolpath(
                self.segments,
                self.current_tool,
                on_progress=lambda p: self._update_progress(p)
            )
            
            # Update display
            self._update_stock_display()
            self._update_stock_stats(stats)
            
            self.statusBar().showMessage(
                f"Simülasyon tamamlandı - Kaldırılan: {stats['removed_volume_mm3']:.1f} mm³"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Simülasyon Hatası", str(e))
    
    def _update_progress(self, pct: float) -> None:
        """Update progress bar/status."""
        self.statusBar().showMessage(f"Simülasyon: %{pct:.0f}")
        # Process events every 10% to keep UI responsive
        if int(pct) % 10 == 0:
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

    def _auto_configure_stock(self) -> None:
        """Auto-configure stock to fit toolpath with smart resolution."""
        if not self.segments:
            return
        
        # Find bounds
        all_points = []
        for seg in self.segments:
            all_points.append(seg["start"])
            all_points.append(seg["end"])
        
        points = np.array(all_points)
        min_coords = points.min(axis=0)
        max_coords = points.max(axis=0)
        
        # Calculate dimensions
        width = max_coords[0] - min_coords[0]
        depth = max_coords[1] - min_coords[1]
        height = max_coords[2] - min_coords[2]
        
        # Smart resolution based on part size
        # Larger parts = lower resolution for performance
        max_dim = max(width, depth)
        if max_dim > 500:
            resolution = 5.0  # Very large part
        elif max_dim > 200:
            resolution = 3.0  # Large part
        elif max_dim > 100:
            resolution = 2.0  # Medium part
        else:
            resolution = 1.0  # Small part (detailed)
        
        # Add padding
        padding = max(10.0, max_dim * 0.05)  # At least 10mm or 5% of size
        
        config = StockConfig(
            width=width + 2 * padding,
            depth=depth + 2 * padding,
            height=height + padding + 5,
            origin_x=min_coords[0] - padding,
            origin_y=min_coords[1] - padding,
            origin_z=min_coords[2] - 5,
            resolution=resolution,
        )
        
        self.stock_simulator = StockSimulator(config)

    def _update_stock_display(self) -> None:
        """Update OpenGL display with stock mesh."""
        mesh_data = self.stock_simulator.get_mesh_for_render()
        if mesh_data:
            vertices, indices = mesh_data
            self._sim_widget.set_stock_mesh(vertices, indices)

    def _update_stock_stats(self, stats: dict) -> None:
        """Update stock statistics in UI."""
        self._stock_total_label.setText(f"Toplam Hacim: {stats['total_volume_mm3']:.1f} mm³")
        self._stock_removed_label.setText(f"Kaldırılan: {stats['removed_volume_mm3']:.1f} mm³")
        self._stock_percent_label.setText(f"İlerleme: %{stats['removal_percent']:.2f}")
        self._stock_aircut_label.setText(f"Air-cut segment: {stats['air_cut_segments']}")

    def _reset_stock(self) -> None:
        """Reset stock simulation."""
        self.stock_simulator.reset()
        self._update_stock_display()
        self._update_stock_stats(self.stock_simulator.get_stats())
        self.statusBar().showMessage("Stock sıfırlandı")
