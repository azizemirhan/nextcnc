"""
Fanuc-compatible G-Code parser.
Tokenizes NC files and produces a list of motion segments (rapid, linear, arc).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Union

import numpy as np

# Token pattern: optional letter + optional minus + number (integer or decimal)
TOKEN_PATTERN = re.compile(r"([GMTXYZIJKFRNS])\s*(-?\d*\.?\d+)", re.IGNORECASE)


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


# Modal group: one of G00, G01, G02, G03 (motion)
DEFAULT_MOTION = "G01"
# Plane: G17 (XY), G18 (XZ), G19 (YZ)
DEFAULT_PLANE = "G17"
# Units: G20 inch, G21 mm
DEFAULT_UNITS = "G21"


def parse_string(
    content: str,
    initial_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    metric: bool = True,
) -> list[dict[str, Any]]:
    """
    Parse G-Code string and return a list of motion segments.
    Each segment has: type ('rapid'|'linear'|'arc_cw'|'arc_ccw'), start, end,
    and for arcs: center, plane. Optional: feedrate.
    """
    segments: list[dict[str, Any]] = []
    position = np.array(initial_position, dtype=np.float64)
    motion = DEFAULT_MOTION
    plane = DEFAULT_PLANE
    units_scale = 1.0 if metric else 25.4  # inch -> mm for internal storage
    feedrate: Union[float, None] = None

    for raw_line in content.splitlines():
        tokens = _tokenize_line(raw_line)
        if not tokens:
            continue

        # Units (G20/G21) - affects subsequent coordinates
        if "G" in tokens:
            g = int(tokens["G"])
            if g == 20:
                units_scale = 25.4
            elif g == 21:
                units_scale = 1.0
            elif g == 17:
                plane = "G17"
            elif g == 18:
                plane = "G18"
            elif g == 19:
                plane = "G19"
            elif g in (0, 1, 2, 3):
                motion = f"G{g:02d}"

        # Program end
        if "M" in tokens:
            m = int(tokens["M"])
            if m in (2, 30):
                break

        # Build end position (modal: missing axis keeps current value)
        end = position.copy()
        if "X" in tokens:
            end[0] = tokens["X"] * units_scale
        if "Y" in tokens:
            end[1] = tokens["Y"] * units_scale
        if "Z" in tokens:
            end[2] = tokens["Z"] * units_scale

        if "F" in tokens:
            feedrate = tokens["F"]

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

        start = position.copy()

        if motion == "G00":
            seg = {
                "type": "rapid",
                "start": start.copy(),
                "end": end.copy(),
                "plane": plane,
            }
            if feedrate is not None:
                seg["feedrate"] = feedrate
            segments.append(seg)
        elif motion == "G01":
            seg = {
                "type": "linear",
                "start": start.copy(),
                "end": end.copy(),
                "plane": plane,
            }
            if feedrate is not None:
                seg["feedrate"] = feedrate
            segments.append(seg)
        elif motion in ("G02", "G03"):
            # Arc: center = start + (I,J,K) in plane
            if plane == "G17":  # XY
                center = start + np.array([center_offset[0], center_offset[1], 0.0])
            elif plane == "G18":  # XZ
                center = start + np.array([center_offset[0], 0.0, center_offset[2]])
            else:  # G19 YZ
                center = start + np.array([0.0, center_offset[1], center_offset[2]])
            seg = {
                "type": "arc_cw" if motion == "G02" else "arc_ccw",
                "start": start.copy(),
                "end": end.copy(),
                "center": center.copy(),
                "plane": plane,
            }
            if feedrate is not None:
                seg["feedrate"] = feedrate
            segments.append(seg)

        position = end.copy()

    return segments


def parse_file(
    path: Union[str, Path],
    initial_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    metric: bool = True,
) -> list[dict[str, Any]]:
    """Parse a G-Code file and return list of motion segments."""
    path = Path(path)
    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_string(content, initial_position=initial_position, metric=metric)
