# NextCNC

CNC Post-Processor and Simulation (G-Code parser, 3D toolpath viewer).

## Setup

On macOS, use `python3` and the module form of pip:

```bash
cd nextcnc
python3 -m pip install -r requirements.txt
```

Or, if `pip3` is on your PATH:

```bash
pip3 install -r requirements.txt
```

## Run

```bash
python3 main.py
```

Then use **File → Open G-Code** to load a `.nc` or `.gcode` file and view the toolpath in 3D.
