"""
3-axis kinematics: convert parser segments to TCP polyline points.
Handles linear and circular interpolation (arc sampling).

Features:
- WCS (Work Coordinate System) G54-G59 support
- Axis limit checking
- Machine configuration (JSON based)
- Forward kinematics for 3-axis milling
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass
class AxisLimits:
    """Axis limit configuration."""
    min: float = -9999.0
    max: float = 9999.0
    
    def check(self, value: float, axis_name: str) -> tuple[bool, Optional[str]]:
        """Check if value is within limits. Returns (ok, error_message)."""
        if value < self.min:
            return False, f"{axis_name} limit exceeded: {value:.3f} < {self.min:.3f}"
        if value > self.max:
            return False, f"{axis_name} limit exceeded: {value:.3f} > {self.max:.3f}"
        return True, None


@dataclass
class MachineConfig:
    """3-axis machine configuration."""
    name: str = "Default 3-Axis Mill"
    
    # Axis limits
    x_limits: AxisLimits = field(default_factory=lambda: AxisLimits(-500.0, 500.0))
    y_limits: AxisLimits = field(default_factory=lambda: AxisLimits(-300.0, 300.0))
    z_limits: AxisLimits = field(default_factory=lambda: AxisLimits(-200.0, 100.0))
    
    # Rapid feed rate (mm/min)
    max_rapid_feed: float = 10000.0
    
    # Max cutting feed rate (mm/min)
    max_cutting_feed: float = 5000.0
    
    @classmethod
    def from_json(cls, path: str | Path) -> "MachineConfig":
        """Load configuration from JSON file."""
        path = Path(path)
        if not path.exists():
            return cls()  # Return default
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return cls(
            name=data.get("name", "Default 3-Axis Mill"),
            x_limits=AxisLimits(**data.get("x_limits", {})),
            y_limits=AxisLimits(**data.get("y_limits", {})),
            z_limits=AxisLimits(**data.get("z_limits", {})),
            max_rapid_feed=data.get("max_rapid_feed", 10000.0),
            max_cutting_feed=data.get("max_cutting_feed", 5000.0),
        )
    
    def to_json(self, path: str | Path) -> None:
        """Save configuration to JSON file."""
        path = Path(path)
        data = {
            "name": self.name,
            "x_limits": {"min": self.x_limits.min, "max": self.x_limits.max},
            "y_limits": {"min": self.y_limits.min, "max": self.y_limits.max},
            "z_limits": {"min": self.z_limits.min, "max": self.z_limits.max},
            "max_rapid_feed": self.max_rapid_feed,
            "max_cutting_feed": self.max_cutting_feed,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def check_axis_limits(self, x: float, y: float, z: float) -> tuple[bool, list[str]]:
        """Check all axis limits. Returns (all_ok, list_of_errors)."""
        errors = []
        for value, limits, name in [(x, self.x_limits, "X"), 
                                     (y, self.y_limits, "Y"), 
                                     (z, self.z_limits, "Z")]:
            ok, error = limits.check(value, name)
            if not ok:
                errors.append(error)
        return len(errors) == 0, errors


@dataclass
class WorkCoordinateSystem:
    """WCS (G54-G59) offset storage."""
    # G54 is index 0, G55 is index 1, etc.
    offsets: list[np.ndarray] = field(default_factory=lambda: [
        np.array([0.0, 0.0, 0.0]),  # G54
        np.array([0.0, 0.0, 0.0]),  # G55
        np.array([0.0, 0.0, 0.0]),  # G56
        np.array([0.0, 0.0, 0.0]),  # G57
        np.array([0.0, 0.0, 0.0]),  # G58
        np.array([0.0, 0.0, 0.0]),  # G59
    ])
    active_wcs: int = 0  # 0 = G54, 5 = G59
    
    def set_offset(self, wcs_index: int, x: float, y: float, z: float) -> None:
        """Set WCS offset (0-5 for G54-G59)."""
        if 0 <= wcs_index < 6:
            self.offsets[wcs_index] = np.array([x, y, z])
    
    def get_active_offset(self) -> np.ndarray:
        """Get currently active WCS offset."""
        return self.offsets[self.active_wcs].copy()
    
    def work_to_machine(self, work_pos: np.ndarray) -> np.ndarray:
        """Convert work coordinates to machine coordinates."""
        return work_pos + self.get_active_offset()
    
    def machine_to_work(self, machine_pos: np.ndarray) -> np.ndarray:
        """Convert machine coordinates to work coordinates."""
        return machine_pos - self.get_active_offset()


@dataclass
class MachineState:
    """Complete machine state at a given moment."""
    # Axis positions (machine coordinates)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    # Work coordinates
    x_work: float = 0.0
    y_work: float = 0.0
    z_work: float = 0.0
    
    # Active WCS
    active_wcs: int = 0  # 0-5 for G54-G59
    
    # Feed rate
    feed_rate: float = 0.0
    
    # Spindle
    spindle_rpm: float = 0.0
    spindle_on: bool = False
    
    # Active tool
    tool_id: int = 0
    
    # Modal state reference
    modal_snapshot: dict[str, Any] = field(default_factory=dict)
    
    # Status
    limits_ok: bool = True
    limit_errors: list[str] = field(default_factory=list)
    
    @property
    def position_machine(self) -> np.ndarray:
        """Get machine position as array."""
        return np.array([self.x, self.y, self.z])
    
    @property
    def position_work(self) -> np.ndarray:
        """Get work position as array."""
        return np.array([self.x_work, self.y_work, self.z_work])


class Kinematics3Axis:
    """3-axis milling machine kinematics engine."""
    
    def __init__(self, config: Optional[MachineConfig] = None):
        self.config = config or MachineConfig()
        self.wcs = WorkCoordinateSystem()
        self.current_state = MachineState()
    
    def set_wcs(self, wcs_index: int) -> None:
        """Activate WCS (0-5 for G54-G59)."""
        if 0 <= wcs_index < 6:
            self.wcs.active_wcs = wcs_index
            self.current_state.active_wcs = wcs_index
            # Update work coordinates based on new offset
            work = self.wcs.machine_to_work(self.current_state.position_machine)
            self.current_state.x_work, self.current_state.y_work, self.current_state.z_work = work
    
    def set_wcs_offset(self, wcs_index: int, x: float, y: float, z: float) -> None:
        """Set WCS offset."""
        self.wcs.set_offset(wcs_index, x, y, z)
    
    def move_to_work(self, x: Optional[float] = None, y: Optional[float] = None, 
                     z: Optional[float] = None, feed_rate: Optional[float] = None) -> MachineState:
        """Move to work coordinates. Returns new state."""
        # Update work position
        if x is not None:
            self.current_state.x_work = x
        if y is not None:
            self.current_state.y_work = y
        if z is not None:
            self.current_state.z_work = z
        if feed_rate is not None:
            self.current_state.feed_rate = feed_rate
        
        # Convert to machine coordinates
        work_pos = self.current_state.position_work
        machine_pos = self.wcs.work_to_machine(work_pos)
        self.current_state.x, self.current_state.y, self.current_state.z = machine_pos
        
        # Check limits
        ok, errors = self.config.check_axis_limits(
            self.current_state.x, 
            self.current_state.y, 
            self.current_state.z
        )
        self.current_state.limits_ok = ok
        self.current_state.limit_errors = errors
        
        return self.current_state
    
    def move_to_machine(self, x: Optional[float] = None, y: Optional[float] = None,
                        z: Optional[float] = None, feed_rate: Optional[float] = None) -> MachineState:
        """Move to machine coordinates. Returns new state."""
        # Update machine position
        if x is not None:
            self.current_state.x = x
        if y is not None:
            self.current_state.y = y
        if z is not None:
            self.current_state.z = z
        if feed_rate is not None:
            self.current_state.feed_rate = feed_rate
        
        # Convert to work coordinates
        machine_pos = self.current_state.position_machine
        work_pos = self.wcs.machine_to_work(machine_pos)
        self.current_state.x_work, self.current_state.y_work, self.current_state.z_work = work_pos
        
        # Check limits
        ok, errors = self.config.check_axis_limits(
            self.current_state.x, 
            self.current_state.y, 
            self.current_state.z
        )
        self.current_state.limits_ok = ok
        self.current_state.limit_errors = errors
        
        return self.current_state
    
    def get_state(self) -> MachineState:
        """Get current machine state."""
        return self.current_state


# ============================================================================
# Arc interpolation functions (original implementation)
# ============================================================================

def _arc_points_xy(
    start: np.ndarray,
    end: np.ndarray,
    center: np.ndarray,
    clockwise: bool,
    num_samples: int,
) -> np.ndarray:
    """Sample an arc in XY plane (G17). start/end/center are (3,) arrays."""
    sx, sy = start[0], start[1]
    ex, ey = end[0], end[1]
    cx, cy = center[0], center[1]
    start_angle = np.arctan2(sy - cy, sx - cx)
    end_angle = np.arctan2(ey - cy, ex - cx)
    radius = np.sqrt((sx - cx) ** 2 + (sy - cy) ** 2)
    if clockwise:
        if end_angle >= start_angle:
            end_angle -= 2 * np.pi
    else:
        if end_angle <= start_angle:
            end_angle += 2 * np.pi
    t = np.linspace(0, 1, num_samples, endpoint=True)
    angles = start_angle + t * (end_angle - start_angle)
    z = np.linspace(start[2], end[2], num_samples, endpoint=True)
    x = cx + radius * np.cos(angles)
    y = cy + radius * np.sin(angles)
    return np.column_stack((x, y, z))


def _arc_points_xz(
    start: np.ndarray,
    end: np.ndarray,
    center: np.ndarray,
    clockwise: bool,
    num_samples: int,
) -> np.ndarray:
    """Arc in XZ plane (G18): angle in XZ."""
    sx, sz = start[0], start[2]
    ex, ez = end[0], end[2]
    cx, cz = center[0], center[2]
    start_angle = np.arctan2(sz - cz, sx - cx)
    end_angle = np.arctan2(ez - cz, ex - cx)
    radius = np.sqrt((sx - cx) ** 2 + (sz - cz) ** 2)
    if clockwise:
        if end_angle >= start_angle:
            end_angle -= 2 * np.pi
    else:
        if end_angle <= start_angle:
            end_angle += 2 * np.pi
    t = np.linspace(0, 1, num_samples, endpoint=True)
    angles = start_angle + t * (end_angle - start_angle)
    y = np.linspace(start[1], end[1], num_samples, endpoint=True)
    x = cx + radius * np.cos(angles)
    z = cz + radius * np.sin(angles)
    return np.column_stack((x, y, z))


def _arc_points_yz(
    start: np.ndarray,
    end: np.ndarray,
    center: np.ndarray,
    clockwise: bool,
    num_samples: int,
) -> np.ndarray:
    """Arc in YZ plane (G19)."""
    sy, sz = start[1], start[2]
    ey, ez = end[1], end[2]
    cy, cz = center[1], center[2]
    start_angle = np.arctan2(sz - cz, sy - cy)
    end_angle = np.arctan2(ez - cz, ey - cy)
    radius = np.sqrt((sy - cy) ** 2 + (sz - cz) ** 2)
    if clockwise:
        if end_angle >= start_angle:
            end_angle -= 2 * np.pi
    else:
        if end_angle <= start_angle:
            end_angle += 2 * np.pi
    t = np.linspace(0, 1, num_samples, endpoint=True)
    angles = start_angle + t * (end_angle - start_angle)
    x = np.linspace(start[0], end[0], num_samples, endpoint=True)
    y = cy + radius * np.cos(angles)
    z = cz + radius * np.sin(angles)
    return np.column_stack((x, y, z))


def segment_to_points(segment: dict[str, Any], num_samples: int = 32) -> np.ndarray:
    """
    Convert a single motion segment to an array of 3D points (N, 3).
    Linear/rapid: start and end; arc: sampled along the arc.
    """
    start = np.asarray(segment["start"], dtype=np.float64)
    end = np.asarray(segment["end"], dtype=np.float64)
    seg_type = segment.get("type", "linear")
    plane = segment.get("plane", "G17")

    if seg_type in ("rapid", "linear"):
        return np.array([start, end], dtype=np.float64)

    if seg_type == "arc_cw":
        clockwise = True
    elif seg_type == "arc_ccw":
        clockwise = False
    else:
        return np.array([start, end], dtype=np.float64)

    center = np.asarray(segment["center"], dtype=np.float64)
    if plane == "G17":
        return _arc_points_xy(start, end, center, clockwise, num_samples)
    if plane == "G18":
        return _arc_points_xz(start, end, center, clockwise, num_samples)
    if plane == "G19":
        return _arc_points_yz(start, end, center, clockwise, num_samples)
    return np.array([start, end], dtype=np.float64)


def segments_to_points(
    segments: list[dict[str, Any]],
    num_samples: int = 32,
    connect: bool = True,
) -> np.ndarray:
    """
    Convert a list of segments to a single polyline (N, 3).
    If connect=True, segments are concatenated (shared endpoints not duplicated
    to avoid gaps when drawing line_strip; duplicate is needed for strict polyline).
    For GL_LINE_STRIP we want no duplicate so the path is continuous.
    """
    if not segments:
        return np.zeros((0, 3), dtype=np.float64)

    chunks = []
    for seg in segments:
        pts = segment_to_points(seg, num_samples=num_samples)
        chunks.append(pts)

    if connect:
        # Concatenate: skip first point of each chunk after the first (it equals previous end)
        out = [chunks[0]]
        for i in range(1, len(chunks)):
            out.append(chunks[i][1:])
        return np.concatenate(out, axis=0) if out else np.zeros((0, 3), dtype=np.float64)
    return np.concatenate(chunks, axis=0)


# ============================================================================
# New: Machine-aware segment processing
# ============================================================================

def process_segments_with_machine(
    segments: list[dict[str, Any]],
    kinematics: Kinematics3Axis,
    num_samples: int = 32,
) -> tuple[np.ndarray, list[MachineState]]:
    """
    Process segments with full machine kinematics.
    
    Returns:
        points: (N, 3) array of toolpath points
        states: List of MachineState for each point
    """
    points = []
    states = []
    
    for seg in segments:
        seg_type = seg.get("type", "linear")
        
        # Handle WCS changes if present in segment
        if "wcs" in seg:
            kinematics.set_wcs(seg["wcs"])
        
        # Get segment points
        seg_points = segment_to_points(seg, num_samples=num_samples)
        
        for pt in seg_points:
            # Move to this point in work coordinates
            state = kinematics.move_to_work(x=pt[0], y=pt[1], z=pt[2])
            
            # Store machine position for visualization
            points.append(state.position_machine)
            states.append(state)
    
    return np.array(points), states
