"""
Fanuc-compatible G-Code parser.
Tokenizes NC files and produces a list of motion segments (rapid, linear, arc).

Features:
- WCS (G54-G59) support
- Modal state tracking
- Extended G-code support
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Union

import numpy as np

# Token pattern: optional letter + optional minus + number (integer or decimal)
TOKEN_PATTERN = re.compile(r"([GMTXYZIJKFRNSHLQP])\s*(-?\d*\.?\d+)", re.IGNORECASE)


class ModalState:
    """Tracks modal G-code state."""
    
    # Modal Group 1: Motion
    MOTION_G00 = "G00"  # Rapid
    MOTION_G01 = "G01"  # Linear
    MOTION_G02 = "G02"  # Arc CW
    MOTION_G03 = "G03"  # Arc CCW
    
    # Modal Group 2: Plane selection
    PLANE_G17 = "G17"  # XY
    PLANE_G18 = "G18"  # XZ
    PLANE_G19 = "G19"  # YZ
    
    # Modal Group 6: Units
    UNITS_G20 = "G20"  # Inch
    UNITS_G21 = "G21"  # MM
    
    # Modal Group 7: Cutter radius compensation
    CRC_G40 = "G40"  # Cancel
    CRC_G41 = "G41"  # Left
    CRC_G42 = "G42"  # Right
    
    # Modal Group 8: Tool length compensation
    TLC_G43 = "G43"  # Positive
    TLC_G44 = "G44"  # Negative
    TLC_G49 = "G49"  # Cancel
    
    # Work Coordinate Systems (Group 12)
    WCS_G54 = 0
    WCS_G55 = 1
    WCS_G56 = 2
    WCS_G57 = 3
    WCS_G58 = 4
    WCS_G59 = 5
    
    def __init__(self):
        # Current state
        self.motion = self.MOTION_G01
        self.plane = self.PLANE_G17
        self.units = self.UNITS_G21
        self.crc = self.CRC_G40
        self.tlc = self.TLC_G49
        self.wcs = self.WCS_G54
        self.absolute = True  # G90 = True, G91 = False
        
        # Current position
        self.position = np.array([0.0, 0.0, 0.0])
        
        # Current feed and tool
        self.feed_rate: Union[float, None] = None
        self.tool_id: int = 0
        self.spindle_rpm: float = 0.0
        self.spindle_on: bool = False
        
        # WCS offsets (G54-G59)
        self.wcs_offsets: list[np.ndarray] = [
            np.array([0.0, 0.0, 0.0]),  # G54
            np.array([0.0, 0.0, 0.0]),  # G55
            np.array([0.0, 0.0, 0.0]),  # G56
            np.array([0.0, 0.0, 0.0]),  # G57
            np.array([0.0, 0.0, 0.0]),  # G58
            np.array([0.0, 0.0, 0.0]),  # G59
        ]
    
    def get_active_wcs_offset(self) -> np.ndarray:
        """Get currently active WCS offset."""
        return self.wcs_offsets[self.wcs].copy()
    
    def to_dict(self) -> dict[str, Any]:
        """Export state to dictionary."""
        return {
            "motion": self.motion,
            "plane": self.plane,
            "units": self.units,
            "wcs": self.wcs,
            "absolute": self.absolute,
            "position": self.position.copy(),
            "feed_rate": self.feed_rate,
            "tool_id": self.tool_id,
        }


def _tokenize_line(line: str) -> dict[str, float]:
    """Parse a single line into a dict of address -> value."""
    line = line.split(";")[0].strip()  # Remove comments
    if not line or line.startswith("("):
        return {}
    result: dict[str, float] = {}
    for match in TOKEN_PATTERN.finditer(line):
        letter = match.group(1).upper()
        value = float(match.group(2))
        result[letter] = value
    return result


def _parse_g_code(g: int, tokens: dict[str, float], modal: ModalState) -> bool:
    """
    Parse a G-code and update modal state.
    Returns True if a motion command was processed.
    """
    # Motion commands (Group 1)
    if g in (0, 1, 2, 3):
        modal.motion = f"G{g:02d}"
        return True
    
    # Plane selection (Group 2)
    elif g == 17:
        modal.plane = ModalState.PLANE_G17
    elif g == 18:
        modal.plane = ModalState.PLANE_G18
    elif g == 19:
        modal.plane = ModalState.PLANE_G19
    
    # Units (Group 6)
    elif g == 20:
        modal.units = ModalState.UNITS_G20
    elif g == 21:
        modal.units = ModalState.UNITS_G21
    
    # WCS (Group 12) - G54 to G59
    elif g == 54:
        modal.wcs = ModalState.WCS_G54
    elif g == 55:
        modal.wcs = ModalState.WCS_G55
    elif g == 56:
        modal.wcs = ModalState.WCS_G56
    elif g == 57:
        modal.wcs = ModalState.WCS_G57
    elif g == 58:
        modal.wcs = ModalState.WCS_G58
    elif g == 59:
        modal.wcs = ModalState.WCS_G59
    
    # Absolute/Incremental (Group 3)
    elif g == 90:
        modal.absolute = True
    elif g == 91:
        modal.absolute = False
    
    return False


def parse_string(
    content: str,
    initial_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    metric: bool = True,
) -> tuple[list[dict[str, Any]], ModalState]:
    """
    Parse G-Code string and return a list of motion segments and final modal state.
    Each segment has: type ('rapid'|'linear'|'arc_cw'|'arc_ccw'), start, end,
    and for arcs: center, plane. Optional: feedrate, wcs.
    """
    segments: list[dict[str, Any]] = []
    modal = ModalState()
    modal.position = np.array(initial_position, dtype=np.float64)
    units_scale = 1.0 if metric else 25.4  # inch -> mm for internal storage

    for raw_line in content.splitlines():
        tokens = _tokenize_line(raw_line)
        if not tokens:
            continue

        # Process G-codes
        if "G" in tokens:
            g = int(tokens["G"])
            _parse_g_code(g, tokens, modal)
            # Update units scale
            if g == 20:
                units_scale = 25.4
            elif g == 21:
                units_scale = 1.0

        # Program end
        if "M" in tokens:
            m = int(tokens["M"])
            if m in (2, 30):
                break
            # Tool change
            elif m == 6 and "T" in tokens:
                modal.tool_id = int(tokens["T"])

        # Spindle control
        if "M" in tokens:
            m = int(tokens["M"])
            if m == 3:
                modal.spindle_on = True
            elif m == 5:
                modal.spindle_on = False

        # Spindle speed
        if "S" in tokens:
            modal.spindle_rpm = tokens["S"]

        # Build end position (modal: missing axis keeps current value)
        end = modal.position.copy()
        if "X" in tokens:
            x_val = tokens["X"] * units_scale
            if modal.absolute:
                end[0] = x_val
            else:
                end[0] += x_val
        if "Y" in tokens:
            y_val = tokens["Y"] * units_scale
            if modal.absolute:
                end[1] = y_val
            else:
                end[1] += y_val
        if "Z" in tokens:
            z_val = tokens["Z"] * units_scale
            if modal.absolute:
                end[2] = z_val
            else:
                end[2] += z_val

        if "F" in tokens:
            modal.feed_rate = tokens["F"]

        # Arc center offsets (I, J, K) in current plane
        center_offset = np.zeros(3)
        if "I" in tokens:
            center_offset[0] = tokens["I"] * units_scale
        if "J" in tokens:
            center_offset[1] = tokens["J"] * units_scale
        if "K" in tokens:
            center_offset[2] = tokens["K"] * units_scale

        # Emit segment only if there is a move (position or motion command with coordinates)
        has_position = "X" in tokens or "Y" in tokens or "Z" in tokens
        if not has_position:
            continue

        start = modal.position.copy()

        # Determine motion type and create segment
        if modal.motion == "G00":
            seg = {
                "type": "rapid",
                "start": start.copy(),
                "end": end.copy(),
                "plane": modal.plane,
                "wcs": modal.wcs,
                "modal": modal.to_dict(),
            }
            if modal.feed_rate is not None:
                seg["feedrate"] = modal.feed_rate
            segments.append(seg)
        elif modal.motion == "G01":
            seg = {
                "type": "linear",
                "start": start.copy(),
                "end": end.copy(),
                "plane": modal.plane,
                "wcs": modal.wcs,
                "modal": modal.to_dict(),
            }
            if modal.feed_rate is not None:
                seg["feedrate"] = modal.feed_rate
            segments.append(seg)
        elif modal.motion in ("G02", "G03"):
            # Arc: center = start + (I,J,K) in plane
            if modal.plane == "G17":  # XY
                center = start + np.array([center_offset[0], center_offset[1], 0.0])
            elif modal.plane == "G18":  # XZ
                center = start + np.array([center_offset[0], 0.0, center_offset[2]])
            else:  # G19 YZ
                center = start + np.array([0.0, center_offset[1], center_offset[2]])
            seg = {
                "type": "arc_cw" if modal.motion == "G02" else "arc_ccw",
                "start": start.copy(),
                "end": end.copy(),
                "center": center.copy(),
                "plane": modal.plane,
                "wcs": modal.wcs,
                "modal": modal.to_dict(),
            }
            if modal.feed_rate is not None:
                seg["feedrate"] = modal.feed_rate
            segments.append(seg)

        modal.position = end.copy()

    return segments, modal


def parse_file(
    path: Union[str, Path],
    initial_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    metric: bool = True,
    return_modal: bool = False,
) -> Union[list[dict[str, Any]], tuple[list[dict[str, Any]], ModalState]]:
    """
    Parse a G-Code file and return list of motion segments.
    If return_modal=True, also returns the final modal state.
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8", errors="replace")
    segments, modal = parse_string(content, initial_position=initial_position, metric=metric)
    if return_modal:
        return segments, modal
    return segments
