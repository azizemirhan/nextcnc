"""
Check that required packages are installed. Run: python check_setup.py
"""
import sys

def main():
    missing = []
    try:
        import PySide6
    except ImportError:
        try:
            import PyQt6
        except ImportError:
            missing.append("PySide6 veya PyQt6")
    try:
        import OpenGL
    except ImportError:
        missing.append("PyOpenGL")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    if missing:
        print("Eksik paketler:", ", ".join(missing))
        print("\nKurulum (PySide6):")
        print("  python -m pip install -r requirements.txt")
        print("\nSSL hatasi alirsaniz - PyQt6 alternatifi:")
        print("  python -m pip install -r requirements-pyqt6.txt")
        print("\nDetayli cozumler: INSTALL_WINDOWS.md dosyasina bakin.")
        return 1
    print("Tum bagimliliklar yüklü. Calistirmak icin: python main.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())
