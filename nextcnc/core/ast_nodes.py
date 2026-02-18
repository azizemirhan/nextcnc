"""
AST (Abstract Syntax Tree) nodes for G-code parsing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


class ASTNode(ABC):
    """Base class for all AST nodes."""
    
    @abstractmethod
    def accept(self, visitor: ASTVisitor) -> Any:
        """Accept a visitor."""
        pass


class ASTVisitor(ABC):
    """Base class for AST visitors."""
    pass


# ============================================================================
# Program Structure
# ============================================================================

@dataclass
class ProgramNode(ASTNode):
    """Root node for a G-code program."""
    program_number: Optional[int] = None
    blocks: list[BlockNode] = field(default_factory=list)
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_program(self)


@dataclass
class BlockNode(ASTNode):
    """A single block (line) of G-code."""
    block_number: Optional[int] = None
    words: list[WordNode] = field(default_factory=list)
    comment: Optional[str] = None
    block_skip: bool = False
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_block(self)


# ============================================================================
# Words (Commands)
# ============================================================================

@dataclass
class WordNode(ASTNode):
    """Base class for G-code words."""
    letter: str
    value: float
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_word(self)


@dataclass 
class GCodeNode(WordNode):
    """G-code word (motion, modal, etc.)."""
    def __init__(self, value: float):
        super().__init__("G", value)
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_g_code(self)


@dataclass
class MCodeNode(WordNode):
    """M-code word (miscellaneous functions)."""
    def __init__(self, value: float):
        super().__init__("M", value)
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_m_code(self)


@dataclass
class CoordinateNode(WordNode):
    """Coordinate words (X, Y, Z, etc.)."""
    pass


@dataclass
class FeedNode(WordNode):
    """Feed rate (F)."""
    def __init__(self, value: float):
        super().__init__("F", value)
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_feed(self)


@dataclass
class SpindleNode(WordNode):
    """Spindle speed (S)."""
    def __init__(self, value: float):
        super().__init__("S", value)
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_spindle(self)


@dataclass
class ToolNode(WordNode):
    """Tool selection (T)."""
    def __init__(self, value: float):
        super().__init__("T", value)
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_tool(self)


# ============================================================================
# Motion Commands
# ============================================================================

@dataclass
class MotionCommand(ASTNode):
    """Base class for motion commands."""
    pass


@dataclass
class RapidMoveNode(MotionCommand):
    """G00 - Rapid positioning."""
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_rapid_move(self)


@dataclass
class LinearMoveNode(MotionCommand):
    """G01 - Linear interpolation."""
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    feed: Optional[float] = None
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_linear_move(self)


@dataclass
class ArcMoveNode(MotionCommand):
    """G02/G03 - Circular interpolation."""
    clockwise: bool  # True = G02, False = G03
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    i: Optional[float] = None  # Center X offset
    j: Optional[float] = None  # Center Y offset
    k: Optional[float] = None  # Center Z offset
    r: Optional[float] = None  # Radius (alternative to IJK)
    feed: Optional[float] = None
    
    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_arc_move(self)


# ============================================================================
# Modal State Container
# ============================================================================

@dataclass
class ModalStateNode:
    """Complete modal state snapshot."""
    # Motion
    motion_mode: int = 1  # G00-G03
    
    # Plane
    plane: int = 17  # G17, G18, G19
    
    # Distance mode
    absolute: bool = True  # G90/G91
    
    # Units
    metric: bool = True  # G20/G21
    
    # WCS
    wcs: int = 54  # G54-G59
    
    # Feed mode
    feed_per_minute: bool = True  # G94/G95
    
    # Cutter radius compensation
    cutter_comp: int = 40  # G40-G42
    
    # Tool length offset
    tool_length_comp: int = 49  # G43, G44, G49
    
    # Canned cycle return
    canned_return: int = 98  # G98/G99
    
    # Canned cycle
    canned_cycle: int = 80  # G73-G89, G80
    
    # Current position
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    
    # Current feed
    feed_rate: float = 0.0
    
    # Current tool
    tool_id: int = 0
    
    # Spindle
    spindle_rpm: float = 0.0
    spindle_on: bool = False
    
    def clone(self) -> ModalStateNode:
        """Create a copy of this state."""
        return ModalStateNode(
            motion_mode=self.motion_mode,
            plane=self.plane,
            absolute=self.absolute,
            metric=self.metric,
            wcs=self.wcs,
            feed_per_minute=self.feed_per_minute,
            cutter_comp=self.cutter_comp,
            tool_length_comp=self.tool_length_comp,
            canned_return=self.canned_return,
            canned_cycle=self.canned_cycle,
            position=self.position.copy(),
            feed_rate=self.feed_rate,
            tool_id=self.tool_id,
            spindle_rpm=self.spindle_rpm,
            spindle_on=self.spindle_on,
        )


# ============================================================================
# Toolpath Segments (Output of interpretation)
# ============================================================================

@dataclass
class ToolpathSegment:
    """A single motion segment in the toolpath."""
    block_number: Optional[int]
    motion_type: str  # 'rapid', 'linear', 'arc_cw', 'arc_ccw'
    start_pos: np.ndarray
    end_pos: np.ndarray
    feed_rate: float
    tool_id: int
    wcs: int
    
    # For arcs
    arc_center: Optional[np.ndarray] = None
    arc_radius: Optional[float] = None
    plane: str = "G17"
    
    # Modal snapshot
    modal: ModalStateNode = field(default_factory=ModalStateNode)


def create_segment_from_move(
    move: MotionCommand,
    start_pos: np.ndarray,
    modal: ModalStateNode,
    block_num: Optional[int] = None,
) -> ToolpathSegment:
    """Create a ToolpathSegment from a motion command."""
    if isinstance(move, RapidMoveNode):
        end_pos = start_pos.copy()
        if move.x is not None:
            end_pos[0] = move.x if modal.absolute else start_pos[0] + move.x
        if move.y is not None:
            end_pos[1] = move.y if modal.absolute else start_pos[1] + move.y
        if move.z is not None:
            end_pos[2] = move.z if modal.absolute else start_pos[2] + move.z
        
        return ToolpathSegment(
            block_number=block_num,
            motion_type="rapid",
            start_pos=start_pos.copy(),
            end_pos=end_pos,
            feed_rate=0.0,
            tool_id=modal.tool_id,
            wcs=modal.wcs,
            modal=modal.clone(),
        )
    
    elif isinstance(move, LinearMoveNode):
        end_pos = start_pos.copy()
        if move.x is not None:
            end_pos[0] = move.x if modal.absolute else start_pos[0] + move.x
        if move.y is not None:
            end_pos[1] = move.y if modal.absolute else start_pos[1] + move.y
        if move.z is not None:
            end_pos[2] = move.z if modal.absolute else start_pos[2] + move.z
        
        feed = move.feed if move.feed is not None else modal.feed_rate
        
        return ToolpathSegment(
            block_number=block_num,
            motion_type="linear",
            start_pos=start_pos.copy(),
            end_pos=end_pos,
            feed_rate=feed,
            tool_id=modal.tool_id,
            wcs=modal.wcs,
            modal=modal.clone(),
        )
    
    elif isinstance(move, ArcMoveNode):
        end_pos = start_pos.copy()
        if move.x is not None:
            end_pos[0] = move.x if modal.absolute else start_pos[0] + move.x
        if move.y is not None:
            end_pos[1] = move.y if modal.absolute else start_pos[1] + move.y
        if move.z is not None:
            end_pos[2] = move.z if modal.absolute else start_pos[2] + move.z
        
        feed = move.feed if move.feed is not None else modal.feed_rate
        motion_type = "arc_cw" if move.clockwise else "arc_ccw"
        
        # Calculate center
        if move.r is not None:
            # Radius mode - center calculated later
            center = None
        else:
            # IJK mode
            center = start_pos.copy()
            if move.i is not None:
                center[0] += move.i
            if move.j is not None:
                center[1] += move.j
            if move.k is not None:
                center[2] += move.k
        
        return ToolpathSegment(
            block_number=block_num,
            motion_type=motion_type,
            start_pos=start_pos.copy(),
            end_pos=end_pos,
            feed_rate=feed,
            tool_id=modal.tool_id,
            wcs=modal.wcs,
            arc_center=center,
            arc_radius=move.r,
            plane=f"G{modal.plane}",
            modal=modal.clone(),
        )
    
    raise ValueError(f"Unknown motion type: {type(move)}")
