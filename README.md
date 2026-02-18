# NextCNC

CNC Post-Processor and Simulation (G-Code parser, 3D toolpath viewer).

## Setup

### Windows

```powershell
cd nextcnc
python -m pip install -r requirements.txt
```

**PySide6 SSL hatası alırsanız** (büyük indirme sırasında `SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC`): PyQt6 kullanın (tek paket, daha küçük indirme):

```powershell
python -m pip install -r requirements-pyqt6.txt
```

### macOS / Linux

```bash
cd nextcnc
python3 -m pip install -r requirements.txt
```

(On macOS you can also use `pip3 install -r requirements.txt` if `pip3` is on your PATH.)

## Run

**Windows:**

```powershell
python main.py
```

**macOS / Linux:**

```bash
python3 main.py
```

Then use **File → Open G-Code** (Ctrl+O) to load a `.nc` or `.gcode` file and view the toolpath in 3D.
