"""
G-Code Lexer: Tokenizes Fanuc-compatible NC files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from .tokens import Token, TokenType


# Regex patterns for G-code tokens
class LexerPatterns:
    """Regular expression patterns for token recognition."""
    
    # Whitespace (not including newline)
    WHITESPACE = re.compile(r"[ \t]+")
    
    # Newline (CR, LF, or CRLF)
    NEWLINE = re.compile(r"\r\n|\r|\n")
    
    # Numbers: integer or decimal
    NUMBER = re.compile(r"-?\d+\.?\d*|\.\d+")
    
    # Word (letter + number): G01, X100.5, etc.
    WORD = re.compile(r"([A-Za-z])(-?\d+\.?\d*)")
    
    # Address letter to token type mapping
    ADDRESS_TOKENS = {
        "G": TokenType.ADDRESS_G,
        "M": TokenType.ADDRESS_M,
        "X": TokenType.ADDRESS_X,
        "Y": TokenType.ADDRESS_Y,
        "Z": TokenType.ADDRESS_Z,
        "A": TokenType.ADDRESS_A,
        "B": TokenType.ADDRESS_B,
        "C": TokenType.ADDRESS_C,
        "U": TokenType.ADDRESS_U,
        "V": TokenType.ADDRESS_V,
        "W": TokenType.ADDRESS_W,
        "I": TokenType.ADDRESS_I,
        "J": TokenType.ADDRESS_J,
        "K": TokenType.ADDRESS_K,
        "R": TokenType.ADDRESS_R,
        "F": TokenType.ADDRESS_F,
        "S": TokenType.ADDRESS_S,
        "T": TokenType.ADDRESS_T,
        "H": TokenType.ADDRESS_H,
        "D": TokenType.ADDRESS_D,
        "L": TokenType.ADDRESS_L,
        "P": TokenType.ADDRESS_P,
        "Q": TokenType.ADDRESS_Q,
        "N": TokenType.ADDRESS_N,
        "O": TokenType.ADDRESS_O,
    }


@dataclass
class LexerError(Exception):
    """Lexer error with position information."""
    message: str
    line: int
    column: int
    
    def __str__(self) -> str:
        return f"Lexer Error at L{self.line}, C{self.column}: {self.message}"


class GCodeLexer:
    """
    Fanuc-compatible G-code lexer.
    Tokenizes G-code text into a stream of tokens.
    """
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        
    @property
    def current_char(self) -> str | None:
        """Get current character or None if EOF."""
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]
    
    @property
    def remaining(self) -> str:
        """Get remaining text from current position."""
        return self.text[self.pos:]
    
    def advance(self, count: int = 1) -> None:
        """Advance position by count characters."""
        for _ in range(count):
            if self.pos < len(self.text):
                if self.text[self.pos] == "\n":
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
    
    def skip_whitespace(self) -> None:
        """Skip whitespace (but not newlines)."""
        while self.current_char is not None and self.current_char in " \t":
            self.advance()
    
    def read_number(self) -> tuple[float, str]:
        """Read a number (integer or float)."""
        match = LexerPatterns.NUMBER.match(self.remaining)
        if not match:
            raise LexerError(
                f"Expected number, got '{self.current_char}'",
                self.line, self.column
            )
        raw = match.group(0)
        value = float(raw) if "." in raw else int(raw)
        self.advance(len(raw))
        return value, raw
    
    def read_word(self) -> tuple[TokenType, float, str]:
        """Read a word (letter + number)."""
        match = LexerPatterns.WORD.match(self.remaining)
        if not match:
            raise LexerError(
                f"Expected word, got '{self.current_char}'",
                self.line, self.column
            )
        
        letter = match.group(1).upper()
        number_str = match.group(2)
        value = float(number_str) if "." in number_str else int(number_str)
        
        token_type = LexerPatterns.ADDRESS_TOKENS.get(
            letter, TokenType.LABEL
        )
        
        raw = match.group(0)
        self.advance(len(raw))
        return token_type, float(value), raw
    
    def read_comment_paren(self) -> tuple[TokenType, str, str]:
        """Read parenthesized comment."""
        chars = ["("]
        self.advance()
        
        while self.current_char is not None:
            char = self.current_char
            chars.append(char)
            self.advance()
            if char == ")":
                break
        
        raw = "".join(chars)
        content = raw[1:-1] if len(raw) > 2 else ""
        return TokenType.COMMENT, content, raw
    
    def next_token(self) -> Token:
        """Get next token from input."""
        self.skip_whitespace()
        
        if self.current_char is None:
            return Token(TokenType.EOF, None, self.line, self.column, "")
        
        start_line = self.line
        start_col = self.column
        char = self.current_char
        
        # Newline
        newline_match = LexerPatterns.NEWLINE.match(self.remaining)
        if newline_match:
            raw = newline_match.group(0)
            self.advance(len(raw))
            return Token(TokenType.NEWLINE, None, start_line, start_col, raw)
        
        # Semicolon comment
        if char == ";":
            comment = self.remaining.split("\n", 1)[0]
            self.advance(len(comment))
            return Token(TokenType.COMMENT_SEMI, comment[1:], start_line, start_col, comment)
        
        # Parenthesized comment
        if char == "(":
            return Token(*self.read_comment_paren(), start_line, start_col)
        
        # Block skip
        if char == "/":
            self.advance()
            return Token(TokenType.BLOCK_SKIP, None, start_line, start_col, "/")
        
        # Parameter
        if char == "#":
            self.advance()
            param_match = re.match(r"\d+", self.remaining)
            if param_match:
                num = int(param_match.group(0))
                self.advance(len(param_match.group(0)))
                raw = f"#{num}"
                return Token(TokenType.PARAMETER, num, start_line, start_col, raw)
            else:
                return Token(TokenType.PARAMETER, 0, start_line, start_col, "#")
        
        # Operators
        if char == "+":
            self.advance()
            return Token(TokenType.PLUS, char, start_line, start_col, char)
        if char == "-":
            self.advance()
            return Token(TokenType.MINUS, char, start_line, start_col, char)
        if char == "*":
            self.advance()
            return Token(TokenType.MUL, char, start_line, start_col, char)
        if char == "=":
            self.advance()
            return Token(TokenType.ASSIGN, char, start_line, start_col, char)
        if char == "[":
            self.advance()
            return Token(TokenType.LBRACKET, char, start_line, start_col, char)
        if char == "]":
            self.advance()
            return Token(TokenType.RBRACKET, char, start_line, start_col, char)
        
        # Word (letter + number)
        if char.isalpha():
            token_type, value, raw = self.read_word()
            return Token(token_type, value, start_line, start_col, raw)
        
        raise LexerError(f"Unexpected character: '{char}'", start_line, start_col)
    
    def tokenize(self) -> list[Token]:
        """Tokenize entire input and return list of tokens."""
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens
    
    def __iter__(self) -> Iterator[Token]:
        """Iterate over tokens."""
        while True:
            token = self.next_token()
            yield token
            if token.type == TokenType.EOF:
                break


def tokenize(text: str) -> list[Token]:
    """Convenience function to tokenize G-code text."""
    lexer = GCodeLexer(text)
    return lexer.tokenize()


def tokenize_file(path: str) -> list[Token]:
    """Convenience function to tokenize a G-code file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return tokenize(text)
