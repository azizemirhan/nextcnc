"""
Fanuc G-Code Parser with AST and Modal State Machine.
Uses lexer for tokenization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .lexer import (
    GCodeLexer, Token, TokenType, 
    LexerError, tokenize, get_modal_group
)
from .ast_nodes import (
    ProgramNode, BlockNode, WordNode,
    GCodeNode, MCodeNode, CoordinateNode, FeedNode, SpindleNode, ToolNode,
    RapidMoveNode, LinearMoveNode, ArcMoveNode,
    ModalStateNode, ToolpathSegment, create_segment_from_move,
)


class ParserError(Exception):
    """Parser error with context."""
    def __init__(self, message: str, token: Optional[Token] = None):
        self.message = message
        self.token = token
        if token:
            super().__init__(f"Parser Error at L{token.line}: {message}")
        else:
            super().__init__(f"Parser Error: {message}")


class ModalStateMachine:
    """
    Modal state machine for G-code parsing.
    Tracks and updates modal state based on G-codes.
    """
    
    def __init__(self):
        self.state = ModalStateNode()
        self.history: list[ModalStateNode] = []
    
    def save_state(self) -> None:
        """Save current state to history."""
        self.history.append(self.state.clone())
    
    def update_from_g_code(self, g_code: int) -> None:
        """Update modal state from G-code."""
        group = get_modal_group(g_code)
        if group is None:
            return  # Unknown G-code
        
        # Update based on group
        if group.name == "GROUP_01_MOTION":
            self.state.motion_mode = g_code
        elif group.name == "GROUP_02_PLANE":
            self.state.plane = g_code
        elif group.name == "GROUP_03_DISTANCE":
            self.state.absolute = (g_code == 90)
        elif group.name == "GROUP_06_UNITS":
            self.state.metric = (g_code == 21)
        elif group.name == "GROUP_12_WCS":
            self.state.wcs = g_code
        elif group.name == "GROUP_07_CUTTER_COMP":
            self.state.cutter_comp = g_code
        elif group.name == "GROUP_08_TOOL_LENGTH":
            self.state.tool_length_comp = g_code
        elif group.name == "GROUP_09_CANNED_RETURN":
            self.state.canned_return = g_code
        elif group.name == "GROUP_10_CANNED":
            self.state.canned_cycle = g_code
    
    def update_position(self, x: Optional[float], y: Optional[float], z: Optional[float]) -> None:
        """Update current position."""
        if x is not None:
            self.state.position[0] = x
        if y is not None:
            self.state.position[1] = y
        if z is not None:
            self.state.position[2] = z
    
    def get_state(self) -> ModalStateNode:
        """Get current state copy."""
        return self.state.clone()


class GCodeParser:
    """
    G-code parser with AST generation and modal state tracking.
    """
    
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.modal = ModalStateMachine()
        
        # Unit conversion
        self.units_scale = 1.0  # 1.0 for mm, 25.4 for inch
    
    @property
    def current_token(self) -> Token:
        """Get current token."""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[self.pos]
    
    def advance(self) -> Token:
        """Advance to next token and return current."""
        token = self.current_token
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token
    
    def peek(self, offset: int = 0) -> Token:
        """Peek at token at offset."""
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]
    
    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type."""
        token = self.current_token
        if token.type != token_type:
            raise ParserError(f"Expected {token_type.name}, got {token.type.name}", token)
        self.advance()
        return token
    
    def skip_newlines(self) -> None:
        """Skip newline tokens."""
        while self.current_token.type == TokenType.NEWLINE:
            self.advance()
    
    def skip_comments(self) -> None:
        """Skip comment tokens."""
        while self.current_token.type in (TokenType.COMMENT, TokenType.COMMENT_SEMI):
            self.advance()
    
    def skip_whitespace(self) -> None:
        """Skip newlines and comments."""
        self.skip_newlines()
        self.skip_comments()
    
    def parse(self) -> ProgramNode:
        """Parse tokens into AST."""
        program = ProgramNode()
        
        while self.current_token.type != TokenType.EOF:
            self.skip_whitespace()
            
            if self.current_token.type == TokenType.EOF:
                break
            
            # Check for program number (O-code)
            if self.current_token.type == TokenType.ADDRESS_O:
                program.program_number = int(self.current_token.value)
                self.advance()
                self.skip_comments()
            
            # Parse block
            block = self.parse_block()
            if block:
                program.blocks.append(block)
        
        return program
    
    def parse_block(self) -> Optional[BlockNode]:
        """Parse a single block (line)."""
        block = BlockNode()
        
        # Check for block skip
        if self.current_token.type == TokenType.BLOCK_SKIP:
            block.block_skip = True
            self.advance()
        
        # Check for block number (N-code)
        if self.current_token.type == TokenType.ADDRESS_N:
            block.block_number = int(self.current_token.value)
            self.advance()
        
        # Parse words until newline or EOF
        while self.current_token.type not in (
            TokenType.NEWLINE, TokenType.EOF
        ):
            token = self.current_token
            
            if token.type in (TokenType.COMMENT, TokenType.COMMENT_SEMI):
                if block.comment:
                    block.comment += " " + str(token.value)
                else:
                    block.comment = str(token.value)
                self.advance()
            
            elif token.type == TokenType.ADDRESS_G:
                block.words.append(GCodeNode(token.value))
                self.modal.update_from_g_code(int(token.value))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_M:
                block.words.append(MCodeNode(token.value))
                # Handle M-codes
                m_code = int(token.value)
                if m_code in (3, 4):
                    self.modal.state.spindle_on = True
                elif m_code == 5:
                    self.modal.state.spindle_on = False
                elif m_code == 6:
                    # Tool change - tool should be set before
                    pass
                elif m_code in (2, 30):
                    # Program end
                    pass
                self.advance()
            
            elif token.type == TokenType.ADDRESS_X:
                block.words.append(CoordinateNode("X", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_Y:
                block.words.append(CoordinateNode("Y", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_Z:
                block.words.append(CoordinateNode("Z", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_I:
                block.words.append(CoordinateNode("I", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_J:
                block.words.append(CoordinateNode("J", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_K:
                block.words.append(CoordinateNode("K", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_R:
                block.words.append(CoordinateNode("R", token.value * self.units_scale))
                self.advance()
            
            elif token.type == TokenType.ADDRESS_F:
                block.words.append(FeedNode(token.value))
                self.modal.state.feed_rate = token.value
                self.advance()
            
            elif token.type == TokenType.ADDRESS_S:
                block.words.append(SpindleNode(token.value))
                self.modal.state.spindle_rpm = token.value
                self.advance()
            
            elif token.type == TokenType.ADDRESS_T:
                block.words.append(ToolNode(token.value))
                self.modal.state.tool_id = int(token.value)
                self.advance()
            
            else:
                # Skip unknown tokens
                self.advance()
        
        # Skip newline
        if self.current_token.type == TokenType.NEWLINE:
            self.advance()
        
        return block if block.words or block.comment else None
    
    def interpret_to_segments(self) -> list[ToolpathSegment]:
        """
        Parse and interpret to toolpath segments.
        This combines parsing with motion interpretation.
        """
        segments = []
        program = self.parse()
        
        # Reset state for interpretation
        self.modal = ModalStateMachine()
        position = np.zeros(3)
        
        for block in program.blocks:
            # Skip block delete
            if block.block_skip:
                continue
            
            # Extract coordinates and parameters from block
            coords = {"X": None, "Y": None, "Z": None}
            ijk = {"I": None, "J": None, "K": None}
            r = None
            feed = None
            has_motion = False
            
            for word in block.words:
                if isinstance(word, GCodeNode):
                    self.modal.update_from_g_code(int(word.value))
                    has_motion = True
                elif isinstance(word, MCodeNode):
                    m_code = int(word.value)
                    if m_code in (2, 30):
                        # Program end
                        return segments
                elif isinstance(word, CoordinateNode):
                    if word.letter in coords:
                        coords[word.letter] = word.value
                    elif word.letter in ijk:
                        ijk[word.letter] = word.value
                    elif word.letter == "R":
                        r = word.value
                elif isinstance(word, FeedNode):
                    feed = word.value
            
            # Create motion command based on modal state
            motion_mode = self.modal.state.motion_mode
            
            if motion_mode == 0:  # Rapid
                move = RapidMoveNode(
                    x=coords["X"],
                    y=coords["Y"],
                    z=coords["Z"],
                )
            elif motion_mode in (1,):  # Linear
                move = LinearMoveNode(
                    x=coords["X"],
                    y=coords["Y"],
                    z=coords["Z"],
                    feed=feed,
                )
            elif motion_mode in (2, 3):  # Arc
                move = ArcMoveNode(
                    clockwise=(motion_mode == 2),
                    x=coords["X"],
                    y=coords["Y"],
                    z=coords["Z"],
                    i=ijk["I"],
                    j=ijk["J"],
                    k=ijk["K"],
                    r=r,
                    feed=feed,
                )
            else:
                continue  # Unknown motion mode
            
            # Check if there's actual motion
            if coords["X"] is None and coords["Y"] is None and coords["Z"] is None:
                continue
            
            # Create segment
            segment = create_segment_from_move(
                move, position, self.modal.get_state(), block.block_number
            )
            segments.append(segment)
            
            # Update position
            position = segment.end_pos.copy()
            self.modal.state.position = position.copy()
        
        return segments


# ============================================================================
# Convenience functions
# ============================================================================

def parse_string(text: str) -> tuple[ProgramNode, list[ToolpathSegment]]:
    """Parse G-code string to AST and segments."""
    tokens = tokenize(text)
    parser = GCodeParser(tokens)
    ast = parser.parse()
    
    # Re-parse for segments (resets state)
    tokens = tokenize(text)
    parser2 = GCodeParser(tokens)
    segments = parser2.interpret_to_segments()
    
    return ast, segments


def parse_file(path: str | Path) -> tuple[ProgramNode, list[ToolpathSegment]]:
    """Parse G-code file to AST and segments."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_string(text)
