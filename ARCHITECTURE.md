# OpenCNC-Engine: Industrial Digital Twin & Optimization Suite

## 1. Executive Summary
OpenCNC-Engine is a high-performance CNC simulation and optimization platform. It provides a bridge between CAM output and physical machining through G-code verification, machine kinematics simulation, and feedrate optimization.

## 2. Core Architectural Layers

### A. Data Ingestion Layer (The Parser)
- **Multi-Dialect Support:** Modular parser for Fanuc, Siemens (Sinumerik), and Heidenhain.
- **Lexical Analysis:** Tokenizes NC files into `G-Code`, `M-Code`, `T-Code` (Tool), and `S-Code` (Spindle).
- **Look-Ahead Buffer:** Pre-calculates upcoming moves for smooth simulation and optimization.

### B. Kinematics & Motion Control Layer
- **Machine Configuration:** XML/JSON based machine definition (3-Axis, 4-Axis, 5-Axis).
- **Forward Kinematics:** Calculates Tool Center Point (TCP) from axis positions.
- **Inverse Kinematics:** Calculates axis positions from target TCP (Essential for 5-axis RTCP).
- **Interpolation Engine:** Linear (G01), Circular (G02/G03), and Helical interpolation logic.

### C. Simulation & Physics Layer (The Digital Twin)
- **3D Rendering Engine:** OpenGL 4.0+ with Shader support for real-time toolpath visualization.
- **Collision Detection (CD):** 
    - AABB (Axis-Aligned Bounding Box) for fast broad-phase checks.
    - GJK/EPA algorithms for narrow-phase precision (Tool vs. Fixture/Machine).
- **Material Removal Simulation:** Voxel-based or Mesh-based material removal to visualize the final part.

### D. Optimization & Analysis Layer
- **Air-Cut Detection:** Identifies non-cutting toolpaths using geometry intersection tests.
- **Feedrate Optimization:** 
    - Automatically increases F-values for air-cuts.
    - Adjusts F-values based on material removal rate (MRR) to maintain constant cutting force.
- **Cycle Time Estimation:** High-precision time calculation considering machine acceleration/deceleration (Jerk control).

## 3. Technical Stack
- **Core:** Python 3.11+ (Logic) / C++ (Performance-critical CD algorithms).
- **Math:** NumPy / SciPy / Eigen (for matrix transformations).
- **UI:** PySide6 (Qt) with custom dark-themed industrial widgets.
- **Graphics:** PyOpenGL / ModernGL.
- **Data:** SQLite for Tool Library and Machine Database.

## 4. Directory Structure & Module Responsibilities
```text
/opencnc_engine
│
├── /core
│   ├── parser.py           # NC file tokenization & parsing
│   ├── kinematics.py       # 3/4/5 Axis transformation matrices
│   └── motion_planner.py   # Interpolation & Jerk control
│
├── /simulation
│   ├── renderer.py         # OpenGL scene management
│   ├── collision.py        # GJK/EPA collision detection
│   └── stock_model.py      # Material removal logic
│
├── /optimization
│   ├── air_cut_finder.py   # Geometry-based air-cut detection
│   └── feed_optimizer.py   # Feedrate adjustment logic
│
├── /gui
│   ├── main_window.py      # Main Dashboard
│   ├── tool_library.py     # Tool management UI
│   └── widgets/            # Custom Qt widgets (G-code editor, etc.)
│
├── /data
│   ├── machines/           # Machine definition files (JSON)
│   └── tools/              # Tool database (SQLite)
│
├── main.py                 # Application entry point
└── ARCHITECTURE.md         # This document
