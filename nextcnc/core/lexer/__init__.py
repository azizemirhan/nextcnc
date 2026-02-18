"""
G-Code Lexer module for Fanuc-compatible CNC controllers.
"""

from .tokens import (
    Token,
    TokenType,
    ModalGroup,
    G_CODE_MODAL_GROUPS,
    get_modal_group,
)
from .lexer import (
    GCodeLexer,
    LexerError,
    tokenize,
    tokenize_file,
)

__all__ = [
    # Token types
    "Token",
    "TokenType",
    "ModalGroup",
    "G_CODE_MODAL_GROUPS",
    "get_modal_group",
    # Lexer
    "GCodeLexer",
    "LexerError",
    "tokenize",
    "tokenize_file",
]
