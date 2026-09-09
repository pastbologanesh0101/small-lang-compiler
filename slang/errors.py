"""One error type, carrying a source location so messages point at a line."""

from __future__ import annotations


class SlangError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def render(self, source: str | None = None, filename: str = "<input>") -> str:
        head = f"{filename}:{self.line}:{self.col}: error: {self.message}"
        if source and self.line:
            lines = source.splitlines()
            if 1 <= self.line <= len(lines):
                src = lines[self.line - 1]
                caret = " " * (self.col - 1) + "^"
                return f"{head}\n  {src}\n  {caret}"
        return head


class LexError(SlangError):
    pass


class ParseError(SlangError):
    pass


class CompileError(SlangError):
    pass
