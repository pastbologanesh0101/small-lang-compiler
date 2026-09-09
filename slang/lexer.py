"""Hand-written lexer: source text -> stream of :class:`Token`.

The language ("Slang") has C-flavoured syntax::

    fn fib(n) {
        if (n < 2) { return n; }
        return fib(n - 1) + fib(n - 2);
    }
    let i = 0;
    while (i < 10) {
        print fib(i);
        i = i + 1;
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .errors import LexError


class T(Enum):
    # literals / names
    INT = auto()
    IDENT = auto()
    TRUE = auto()
    FALSE = auto()
    # keywords
    LET = auto()
    FN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    RETURN = auto()
    PRINT = auto()
    # punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    SEMI = auto()
    # operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    ASSIGN = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    EOF = auto()


KEYWORDS = {
    "let": T.LET, "fn": T.FN, "if": T.IF, "else": T.ELSE, "while": T.WHILE,
    "return": T.RETURN, "print": T.PRINT, "true": T.TRUE, "false": T.FALSE,
}

# Two-char operators tried before one-char.
TWO_CHAR = {"==": T.EQ, "!=": T.NE, "<=": T.LE, ">=": T.GE, "&&": T.AND, "||": T.OR}
ONE_CHAR = {
    "(": T.LPAREN, ")": T.RPAREN, "{": T.LBRACE, "}": T.RBRACE, ",": T.COMMA,
    ";": T.SEMI, "+": T.PLUS, "-": T.MINUS, "*": T.STAR, "/": T.SLASH,
    "%": T.PERCENT, "=": T.ASSIGN, "<": T.LT, ">": T.GT, "!": T.NOT,
}


@dataclass
class Token:
    type: T
    value: str
    line: int
    col: int

    def __repr__(self) -> str:  # nicer test output
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    line_start = 0
    n = len(source)

    def col() -> int:
        return i - line_start + 1

    while i < n:
        c = source[i]

        # whitespace
        if c == "\n":
            i += 1
            line += 1
            line_start = i
            continue
        if c in " \t\r":
            i += 1
            continue

        # comments: // to end of line, and /* ... */
        if source.startswith("//", i):
            while i < n and source[i] != "\n":
                i += 1
            continue
        if source.startswith("/*", i):
            start_line, start_col = line, col()
            i += 2
            while i < n and not source.startswith("*/", i):
                if source[i] == "\n":
                    line += 1
                    i += 1
                    line_start = i
                else:
                    i += 1
            if i >= n:
                raise LexError("unterminated block comment", start_line, start_col)
            i += 2
            continue

        # integers
        if c.isdigit():
            start, start_col = i, col()
            while i < n and source[i].isdigit():
                i += 1
            if i < n and (source[i].isalpha() or source[i] == "_"):
                raise LexError("invalid number literal", line, start_col)
            tokens.append(Token(T.INT, source[start:i], line, start_col))
            continue

        # identifiers / keywords
        if c.isalpha() or c == "_":
            start, start_col = i, col()
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            tokens.append(Token(KEYWORDS.get(word, T.IDENT), word, line, start_col))
            continue

        # operators / punctuation
        two = source[i:i + 2]
        if two in TWO_CHAR:
            tokens.append(Token(TWO_CHAR[two], two, line, col()))
            i += 2
            continue
        if c in ONE_CHAR:
            tokens.append(Token(ONE_CHAR[c], c, line, col()))
            i += 1
            continue

        raise LexError(f"unexpected character {c!r}", line, col())

    tokens.append(Token(T.EOF, "", line, col()))
    return tokens
