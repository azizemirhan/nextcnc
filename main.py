"""
NextCNC application entry point.
"""

import sys
from pathlib import Path

# Ensure project root is on path when running as python main.py
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from nextcnc.qt_compat import QApplication, QSurfaceFormat
from nextcnc.gui.main_window import MainWindow


def main() -> None:
    # macOS (Apple Silicon) only supports OpenGL Core Profile; Compatibility causes SIGSEGV.
    # On macOS use Core Profile 3.3; on Windows/Linux use default so QOpenGLWidget's format wins.
    if sys.platform == "darwin":
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(4)
        QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    app.setApplicationName("NextCNC")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
