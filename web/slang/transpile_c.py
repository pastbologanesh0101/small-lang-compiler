"""A second code-generation backend: AST -> portable C99.

This is a lowering, not a faithful mirror of the bytecode VM: every Slang value
becomes a C ``long``, so ``print`` of a boolean emits ``1``/``0`` rather than
``true``/``false``. The bytecode VM is the reference semantics; this backend
exists to show the same AST driving a completely different target (text you can
hand to ``cc``). Integer-only programs produce identical output on both.

Slang maps onto C almost 1:1: functions -> functions, ``let`` -> ``long``
declarations, ``print`` -> ``printf``, control flow unchanged. The only fix-ups
are forward declarations (so definition order doesn't matter) and hoisting
top-level ``let`` into a generated ``main``.
"""

from __future__ import annotations

from . import ast
from .errors import CompileError

_BIN_C = {
    "+": "+", "-": "-", "*": "*", "/": "/", "%": "%",
    "==": "==", "!=": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
    "&&": "&&", "||": "||",
}


class CGen:
    def __init__(self) -> None:
        self.out: list[str] = []
        self.indent = 0

    def line(self, text: str = "") -> None:
        self.out.append("    " * self.indent + text if text else "")

    # -- program ------------------------------------------
    def gen_program(self, prog: ast.Program) -> str:
        funcs = [s for s in prog.body if isinstance(s, ast.Function)]
        top = [s for s in prog.body if not isinstance(s, ast.Function)]

        self.line("/* generated from Slang source by slang.transpile_c */")
        self.line("#include <stdio.h>")
        self.line()
        for f in funcs:
            params = ", ".join(f"long {p}" for p in f.params) or "void"
            self.line(f"long {f.name}({params});")
        self.line()
        for f in funcs:
            self.gen_function(f)
            self.line()
        self.line("int main(void) {")
        self.indent += 1
        for s in top:
            self.gen_stmt(s)
        self.line("return 0;")
        self.indent -= 1
        self.line("}")
        return "\n".join(self.out) + "\n"

    def gen_function(self, f: ast.Function) -> None:
        params = ", ".join(f"long {p}" for p in f.params) or "void"
        self.line(f"long {f.name}({params}) {{")
        self.indent += 1
        for s in f.body.body:
            self.gen_stmt(s)
        self.line("return 0;  /* implicit */")
        self.indent -= 1
        self.line("}")

    # -- statements --------------------------------------
    def gen_stmt(self, s: ast.Stmt) -> None:
        if isinstance(s, ast.Let):
            self.line(f"long {s.name} = {self.gen_expr(s.value)};")
        elif isinstance(s, ast.Assign):
            self.line(f"{s.name} = {self.gen_expr(s.value)};")
        elif isinstance(s, ast.ExprStmt):
            self.line(f"{self.gen_expr(s.expr)};")
        elif isinstance(s, ast.Print):
            self.line(f'printf("%ld\\n", (long)({self.gen_expr(s.expr)}));')
        elif isinstance(s, ast.Return):
            self.line(f"return {self.gen_expr(s.value) if s.value else '0'};")
        elif isinstance(s, ast.Block):
            self.line("{")
            self.indent += 1
            for x in s.body:
                self.gen_stmt(x)
            self.indent -= 1
            self.line("}")
        elif isinstance(s, ast.If):
            self.line(f"if ({self.gen_expr(s.cond)}) {{")
            self.indent += 1
            for x in s.then.body:
                self.gen_stmt(x)
            self.indent -= 1
            if s.otherwise:
                self.line("} else {")
                self.indent += 1
                for x in s.otherwise.body:
                    self.gen_stmt(x)
                self.indent -= 1
            self.line("}")
        elif isinstance(s, ast.While):
            self.line(f"while ({self.gen_expr(s.cond)}) {{")
            self.indent += 1
            for x in s.body.body:
                self.gen_stmt(x)
            self.indent -= 1
            self.line("}")
        elif isinstance(s, ast.Function):
            raise CompileError("nested functions are not supported by the C backend",
                               s.line)
        else:  # pragma: no cover
            raise CompileError(f"cannot lower {type(s).__name__}")

    # -- expressions ------------------------------------
    def gen_expr(self, e: ast.Expr) -> str:
        if isinstance(e, ast.IntLit):
            return str(e.value)
        if isinstance(e, ast.BoolLit):
            return "1" if e.value else "0"
        if isinstance(e, ast.Var):
            return e.name
        if isinstance(e, ast.Unary):
            return f"({'-' if e.op == '-' else '!'}{self.gen_expr(e.operand)})"
        if isinstance(e, ast.Binary):
            return f"({self.gen_expr(e.left)} {_BIN_C[e.op]} {self.gen_expr(e.right)})"
        if isinstance(e, ast.Call):
            return f"{e.callee}(" + ", ".join(self.gen_expr(a) for a in e.args) + ")"
        raise CompileError(f"cannot lower {type(e).__name__}")  # pragma: no cover


def to_c(program: ast.Program) -> str:
    return CGen().gen_program(program)
