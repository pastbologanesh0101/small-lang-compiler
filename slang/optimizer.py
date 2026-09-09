"""A small AST -> AST pass: constant folding and dead-branch elimination.

Not required for correctness — it just makes the point that optimizations are
tree rewrites that preserve meaning. ``slang run --no-opt`` skips it.
"""

from __future__ import annotations

from . import ast

_INT_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: int(a / b) if b != 0 else None,
    "%": lambda a, b: a % b if b != 0 else None,
}
_CMP_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
}


def optimize(program: ast.Program) -> ast.Program:
    return ast.Program([_stmt(s) for s in program.body])


def _stmt(s: ast.Stmt) -> ast.Stmt:
    if isinstance(s, ast.Let):
        return ast.Let(s.name, _expr(s.value), s.line)
    if isinstance(s, ast.Assign):
        return ast.Assign(s.name, _expr(s.value), s.line)
    if isinstance(s, ast.ExprStmt):
        return ast.ExprStmt(_expr(s.expr), s.line)
    if isinstance(s, ast.Print):
        return ast.Print(_expr(s.expr), s.line)
    if isinstance(s, ast.Block):
        return ast.Block([_stmt(x) for x in s.body], s.line)
    if isinstance(s, ast.Return):
        return ast.Return(_expr(s.value) if s.value else None, s.line)
    if isinstance(s, ast.Function):
        return ast.Function(s.name, s.params, _stmt(s.body), s.line)
    if isinstance(s, ast.While):
        cond = _expr(s.cond)
        if isinstance(cond, ast.BoolLit) and cond.value is False:
            return ast.Block([], s.line)          # while(false) {...}  -> nothing
        return ast.While(cond, _stmt(s.body), s.line)
    if isinstance(s, ast.If):
        cond = _expr(s.cond)
        if isinstance(cond, ast.BoolLit):
            branch = s.then if cond.value else s.otherwise
            return _stmt(branch) if branch else ast.Block([], s.line)
        return ast.If(cond, _stmt(s.then),
                      _stmt(s.otherwise) if s.otherwise else None, s.line)
    return s


def _expr(e: ast.Expr) -> ast.Expr:
    if isinstance(e, ast.Unary):
        operand = _expr(e.operand)
        if e.op == "-" and isinstance(operand, ast.IntLit):
            return ast.IntLit(-operand.value, e.line)
        if e.op == "!" and isinstance(operand, ast.BoolLit):
            return ast.BoolLit(not operand.value, e.line)
        return ast.Unary(e.op, operand, e.line)

    if isinstance(e, ast.Binary):
        left, right = _expr(e.left), _expr(e.right)
        if isinstance(left, ast.IntLit) and isinstance(right, ast.IntLit):
            if e.op in _INT_OPS:
                v = _INT_OPS[e.op](left.value, right.value)
                if v is not None:
                    return ast.IntLit(v, e.line)
            if e.op in _CMP_OPS:
                return ast.BoolLit(_CMP_OPS[e.op](left.value, right.value), e.line)
        if isinstance(left, ast.BoolLit) and isinstance(right, ast.BoolLit):
            if e.op == "&&":
                return ast.BoolLit(left.value and right.value, e.line)
            if e.op == "||":
                return ast.BoolLit(left.value or right.value, e.line)
        # short-circuit with a known left operand
        if isinstance(left, ast.BoolLit):
            if e.op == "&&":
                return right if left.value else ast.BoolLit(False, e.line)
            if e.op == "||":
                return ast.BoolLit(True, e.line) if left.value else right
        return ast.Binary(e.op, left, right, e.line)

    if isinstance(e, ast.Call):
        return ast.Call(e.callee, [_expr(a) for a in e.args], e.line)
    return e
