"""Bytecode definition and a disassembler.

A :class:`Chunk` is a flat list of ``(Op, *operands)`` tuples plus a constant
pool. Each function compiles to its own chunk; a function value pairs a chunk
with its arity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class Op(Enum):
    CONST = auto()        # CONST idx        push constants[idx]
    POP = auto()
    NEG = auto()
    NOT = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    JUMP = auto()             # JUMP target
    JUMP_IF_FALSE = auto()    # JUMP_IF_FALSE target   (pops condition)
    JUMP_IF_FALSE_KEEP = auto()  # peek; jump if falsey, leaving value (for &&)
    JUMP_IF_TRUE_KEEP = auto()   # peek; jump if truthy, leaving value  (for ||)
    GET_LOCAL = auto()        # GET_LOCAL slot
    SET_LOCAL = auto()        # SET_LOCAL slot   (leaves value on stack)
    GET_GLOBAL = auto()       # GET_GLOBAL name_idx
    SET_GLOBAL = auto()
    DEF_GLOBAL = auto()
    CALL = auto()             # CALL argc
    RETURN = auto()
    PRINT = auto()
    HALT = auto()


@dataclass
class Function:
    name: str
    arity: int
    chunk: "Chunk"

    def __repr__(self) -> str:
        return f"<fn {self.name}/{self.arity}>"


@dataclass
class Chunk:
    code: list[tuple] = field(default_factory=list)
    constants: list = field(default_factory=list)

    def emit(self, op: Op, *operands) -> int:
        self.code.append((op, *operands))
        return len(self.code) - 1

    def add_const(self, value) -> int:
        # de-duplicate simple immutable constants
        for i, c in enumerate(self.constants):
            if type(c) is type(value) and c == value and not isinstance(c, Function):
                return i
        self.constants.append(value)
        return len(self.constants) - 1

    def patch(self, at: int, target: int) -> None:
        op = self.code[at][0]
        self.code[at] = (op, target)


def disassemble(chunk: Chunk, name: str = "main") -> str:
    out = [f"== {name} =="]
    for i, instr in enumerate(chunk.code):
        op, *ops = instr
        line = f"{i:04d}  {op.name:<20}"
        if op is Op.CONST:
            c = chunk.constants[ops[0]]
            line += f"{ops[0]:>4}  ; {c!r}"
        elif ops:
            line += f"{ops[0]:>4}"
        out.append(line)
    # recurse into nested function constants
    for c in chunk.constants:
        if isinstance(c, Function):
            out.append("")
            out.append(disassemble(c.chunk, c.name))
    return "\n".join(out)
