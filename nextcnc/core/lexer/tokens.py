"""
G-Code Token definitions for Fanuc-compatible CNC controllers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class TokenType(Enum):
    """Token types for G-code lexical analysis."""
    
    # End of file
    EOF = auto()
    
    # Newline (block separator)
    NEWLINE = auto()
    
    # Numbers
    INTEGER = auto()
    FLOAT = auto()
    
    # Addresses (letters followed by numbers)
    ADDRESS_G = auto()   # G-code (motion, modal)
    ADDRESS_M = auto()   # M-code (misc)
    ADDRESS_X = auto()   # X coordinate
    ADDRESS_Y = auto()   # Y coordinate
    ADDRESS_Z = auto()   # Z coordinate
    ADDRESS_A = auto()   # A axis
    ADDRESS_B = auto()   # B axis
    ADDRESS_C = auto()   # C axis
    ADDRESS_U = auto()   # U axis
    ADDRESS_V = auto()   # V axis
    ADDRESS_W = auto()   # W axis
    ADDRESS_I = auto()   # Arc center X
    ADDRESS_J = auto()   # Arc center Y
    ADDRESS_K = auto()   # Arc center Z / tool axis
    ADDRESS_R = auto()   # Radius / Reference
    ADDRESS_F = auto()   # Feed rate
    ADDRESS_S = auto()   # Spindle speed
    ADDRESS_T = auto()   # Tool
    ADDRESS_H = auto()   # Tool length offset
    ADDRESS_D = auto()   # Cutter radius offset
    ADDRESS_L = auto()   # Loop count / Subprogram
    ADDRESS_P = auto()   # Parameter / Dwell / Subprogram
    ADDRESS_Q = auto()   # Peck depth / Parameter
    ADDRESS_N = auto()   # Block number
    ADDRESS_O = auto()   # Program number
    
    # Parameters (# variables)
    PARAMETER = auto()   # #1, #100, etc.
    
    # Operators
    PLUS = auto()        # +
    MINUS = auto()       # -
    MUL = auto()         # *
    DIV = auto()         # /
    ASSIGN = auto()      # =
    
    # Functions (Fanuc)
    FUNC_SIN = auto()
    FUNC_COS = auto()
    FUNC_TAN = auto()
    FUNC_SQRT = auto()
    FUNC_ABS = auto()
    FUNC_ROUND = auto()
    FUNC_FIX = auto()
    FUNC_FUP = auto()
    FUNC_ACOS = auto()
    FUNC_ASIN = auto()
    FUNC_ATAN = auto()
    
    # Brackets
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    
    # Comments
    COMMENT = auto()     # (comment)
    COMMENT_SEMI = auto()  # ; comment
    
    # Block delete
    BLOCK_SKIP = auto()  # / (block delete character)
    
    # Labels
    LABEL = auto()       # Label for GOTO
    
    # String (for file names, etc.)
    STRING = auto()


@dataclass(frozen=True)
class Token:
    """Represents a single token in the G-code stream."""
    type: TokenType
    value: Any
    line: int
    column: int
    raw: str  # Original text
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line})"


# Fanuc G-code modal groups
class ModalGroup(Enum):
    """Modal group classification for G-codes."""
    GROUP_00_NON_MODAL = 0     # G04, G09, G10, etc.
    GROUP_01_MOTION = 1        # G00, G01, G02, G03
    GROUP_02_PLANE = 2         # G17, G18, G19
    GROUP_03_DISTANCE = 3      # G90, G91
    GROUP_05_FEED = 5          # G93, G94, G95
    GROUP_06_UNITS = 6         # G20, G21
    GROUP_07_CUTTER_COMP = 7   # G40, G41, G42
    GROUP_08_TOOL_LENGTH = 8   # G43, G44, G49
    GROUP_09_CANNED_RETURN = 9 # G98, G99
    GROUP_10_CANNED = 10       # G73-G89
    GROUP_12_WCS = 12          # G54-G59
    GROUP_13_COORD_SYS = 13    # G52, G92


# G-code to modal group mapping
G_CODE_MODAL_GROUPS: dict[int, ModalGroup] = {
    # Group 00 - Non-modal
    4: ModalGroup.GROUP_00_NON_MODAL,
    10: ModalGroup.GROUP_00_NON_MODAL,
    28: ModalGroup.GROUP_00_NON_MODAL,
    30: ModalGroup.GROUP_00_NON_MODAL,
    53: ModalGroup.GROUP_00_NON_MODAL,
    
    # Group 01 - Motion
    0: ModalGroup.GROUP_01_MOTION,
    1: ModalGroup.GROUP_01_MOTION,
    2: ModalGroup.GROUP_01_MOTION,
    3: ModalGroup.GROUP_01_MOTION,
    
    # Group 02 - Plane selection
    17: ModalGroup.GROUP_02_PLANE,
    18: ModalGroup.GROUP_02_PLANE,
    19: ModalGroup.GROUP_02_PLANE,
    
    # Group 03 - Distance mode
    90: ModalGroup.GROUP_03_DISTANCE,
    91: ModalGroup.GROUP_03_DISTANCE,
    
    # Group 05 - Feed mode
    93: ModalGroup.GROUP_05_FEED,
    94: ModalGroup.GROUP_05_FEED,
    95: ModalGroup.GROUP_05_FEED,
    
    # Group 06 - Units
    20: ModalGroup.GROUP_06_UNITS,
    21: ModalGroup.GROUP_06_UNITS,
    
    # Group 07 - Cutter radius compensation
    40: ModalGroup.GROUP_07_CUTTER_COMP,
    41: ModalGroup.GROUP_07_CUTTER_COMP,
    42: ModalGroup.GROUP_07_CUTTER_COMP,
    
    # Group 08 - Tool length offset
    43: ModalGroup.GROUP_08_TOOL_LENGTH,
    44: ModalGroup.GROUP_08_TOOL_LENGTH,
    49: ModalGroup.GROUP_08_TOOL_LENGTH,
    
    # Group 09 - Canned return mode
    98: ModalGroup.GROUP_09_CANNED_RETURN,
    99: ModalGroup.GROUP_09_CANNED_RETURN,
    
    # Group 10 - Canned cycles
    73: ModalGroup.GROUP_10_CANNED,
    74: ModalGroup.GROUP_10_CANNED,
    76: ModalGroup.GROUP_10_CANNED,
    80: ModalGroup.GROUP_10_CANNED,
    81: ModalGroup.GROUP_10_CANNED,
    82: ModalGroup.GROUP_10_CANNED,
    83: ModalGroup.GROUP_10_CANNED,
    84: ModalGroup.GROUP_10_CANNED,
    85: ModalGroup.GROUP_10_CANNED,
    86: ModalGroup.GROUP_10_CANNED,
    87: ModalGroup.GROUP_10_CANNED,
    88: ModalGroup.GROUP_10_CANNED,
    89: ModalGroup.GROUP_10_CANNED,
    
    # Group 12 - Work coordinate systems
    54: ModalGroup.GROUP_12_WCS,
    55: ModalGroup.GROUP_12_WCS,
    56: ModalGroup.GROUP_12_WCS,
    57: ModalGroup.GROUP_12_WCS,
    58: ModalGroup.GROUP_12_WCS,
    59: ModalGroup.GROUP_12_WCS,
    
    # Group 13 - Coordinate system
    52: ModalGroup.GROUP_13_COORD_SYS,
    92: ModalGroup.GROUP_13_COORD_SYS,
}


def get_modal_group(g_code: int) -> Optional[ModalGroup]:
    """Get the modal group for a G-code."""
    return G_CODE_MODAL_GROUPS.get(g_code)
