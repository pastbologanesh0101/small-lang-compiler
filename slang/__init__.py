"""Slang — a small C-flavoured language: lexer, Pratt parser, optimizer,
bytecode compiler + stack VM, and a C transpiler backend."""

from .compiler import compile_source
from .optimizer import optimize
from .parser import parse
from .transpile_c import to_c
from .vm import VM

__version__ = "0.1.0"
__all__ = ["parse", "optimize", "compile_source", "VM", "to_c", "run"]


def run(source: str, *, optimize_ast: bool = True) -> str:
    """Parse -> (optimize) -> compile -> execute; return everything printed."""
    program = parse(source)
    if optimize_ast:
        program = optimize(program)
    return VM.run_chunk(compile_source(program))
