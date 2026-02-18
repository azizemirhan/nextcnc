"""
3-axis kinematics: convert parser segments to TCP polyline points.
Handles linear and circular interpolation (arc sampling).
"""

from typing import Any

import numpy as np


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
