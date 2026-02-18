"""
Qt binding compatibility: use PySide6 if available, otherwise PyQt6.
Install either: pip install PySide6  OR  pip install PyQt6
"""

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QMainWindow,
        QMessageBox,
        QMenu,
        QMenuBar,
        QToolBar,
        QStatusBar,
        QDockWidget,
        QWidget,
        QVBoxLayout,
        QLabel,
        QPushButton,
    )
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    __binding__ = "PySide6"
except ImportError:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QSurfaceFormat
    from PyQt6.QtWidgets import (
        QApplication,
        QFileDialog,
        QMainWindow,
        QMessageBox,
        QMenu,
        QMenuBar,
        QToolBar,
        QStatusBar,
        QDockWidget,
        QWidget,
        QVBoxLayout,
        QLabel,
        QPushButton,
    )
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget
    __binding__ = "PyQt6"

__all__ = [
    "Qt",
    "QSurfaceFormat",
    "QApplication",
    "QFileDialog",
    "QMainWindow",
    "QMessageBox",
    "QOpenGLWidget",
    "QMenu",
    "QMenuBar",
    "QToolBar",
    "QStatusBar",
    "QDockWidget",
    "QWidget",
    "QVBoxLayout",
    "QLabel",
    "QPushButton",
]
