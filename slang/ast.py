"""The abstract syntax tree.

Plain dataclasses, every node carries a ``line`` for diagnostics. A program is
a list of statements; functions are declared at any statement position but
hoisted by the compiler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


# ---- expressions ---------------------------------------------------------
@dataclass
class IntLit:
    value: int
    line: int = 0


@dataclass
class BoolLit:
    value: bool
    line: int = 0


@dataclass
class Var:
    name: str
    line: int = 0


@dataclass
class Unary:
    op: str            # "-", "!"
    operand: "Expr"
    line: int = 0


@dataclass
class Binary:
    op: str            # + - * / % == != < > <= >= && ||
    left: "Expr"
    right: "Expr"
    line: int = 0


@dataclass
class Call:
    callee: str
    args: list["Expr"]
    line: int = 0


Expr = Union[IntLit, BoolLit, Var, Unary, Binary, Call]


# ---- statements ---------------------------------------------------------
@dataclass
class Let:
    name: str
    value: Expr
    line: int = 0


@dataclass
class Assign:
    name: str
    value: Expr
    line: int = 0


@dataclass
class ExprStmt:
    expr: Expr
    line: int = 0


@dataclass
class Print:
    expr: Expr
    line: int = 0


@dataclass
class Block:
    body: list["Stmt"]
    line: int = 0


@dataclass
class If:
    cond: Expr
    then: Block
    otherwise: Optional[Block]
    line: int = 0


@dataclass
class While:
    cond: Expr
    body: Block
    line: int = 0


@dataclass
class Return:
    value: Optional[Expr]
    line: int = 0


@dataclass
class Function:
    name: str
    params: list[str]
    body: Block
    line: int = 0


Stmt = Union[Let, Assign, ExprStmt, Print, Block, If, While, Return, Function]


@dataclass
class Program:
    body: list[Stmt] = field(default_factory=list)
