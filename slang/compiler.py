"""AST -> bytecode.

One :class:`Compiler` per function. Top-level ``let``/``fn`` become globals
(looked up by name at run time); parameters and inner ``let`` bindings become
stack locals addressed by slot. Blocks open and close scopes, popping their
locals on exit.
"""

from __future__ import annotations

from . import ast
from .bytecode import Chunk, Function, Op, disassemble
from .errors import CompileError

_BINOP = {
    "+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV, "%": Op.MOD,
    "==": Op.EQ, "!=": Op.NE, "<": Op.LT, ">": Op.GT, "<=": Op.LE, ">=": Op.GE,
}


class Compiler:
    def __init__(self, name: str = "main", params: list[str] | None = None,
                 is_function: bool = False):
        self.name = name
        self.chunk = Chunk()
        self.is_function = is_function
        self.locals: list[tuple[str, int]] = []   # (name, scope_depth)
        self.scope_depth = 0
        for p in params or []:
            self.locals.append((p, 0))

    # -- scope helpers ---------------------------------------
    def begin_scope(self) -> None:
        self.scope_depth += 1

    def end_scope(self) -> None:
        self.scope_depth -= 1
        while self.locals and self.locals[-1][1] > self.scope_depth:
            self.locals.pop()
            self.chunk.emit(Op.POP)

    def declare_local(self, name: str) -> int:
        self.locals.append((name, self.scope_depth))
        return len(self.locals) - 1

    def resolve_local(self, name: str) -> int | None:
        for i in range(len(self.locals) - 1, -1, -1):
            if self.locals[i][0] == name:
                return i
        return None

    # -- top level ------------------------------------------
    def compile_program(self, program: ast.Program) -> Chunk:
        for stmt in program.body:
            self.statement(stmt)
        self.chunk.emit(Op.HALT)
        return self.chunk

    # -- statements ----------------------------------------
    def statement(self, s: ast.Stmt) -> None:
        method = getattr(self, "s_" + type(s).__name__.lower())
        method(s)

    def s_let(self, s: ast.Let) -> None:
        self.expression(s.value)
        if self.scope_depth == 0 and not self.is_function:
            idx = self.chunk.add_const(s.name)
            self.chunk.emit(Op.DEF_GLOBAL, idx)
        else:
            self.declare_local(s.name)   # value stays on the stack as the local

    def s_assign(self, s: ast.Assign) -> None:
        self.expression(s.value)
        slot = self.resolve_local(s.name)
        if slot is not None:
            self.chunk.emit(Op.SET_LOCAL, slot)
        else:
            self.chunk.emit(Op.SET_GLOBAL, self.chunk.add_const(s.name))
        self.chunk.emit(Op.POP)          # assignment as a statement discards value

    def s_exprstmt(self, s: ast.ExprStmt) -> None:
        self.expression(s.expr)
        self.chunk.emit(Op.POP)

    def s_print(self, s: ast.Print) -> None:
        self.expression(s.expr)
        self.chunk.emit(Op.PRINT)

    def s_block(self, s: ast.Block) -> None:
        self.begin_scope()
        for stmt in s.body:
            self.statement(stmt)
        self.end_scope()

    def s_if(self, s: ast.If) -> None:
        self.expression(s.cond)
        else_jump = self.chunk.emit(Op.JUMP_IF_FALSE, -1)
        self.statement(s.then)
        end_jump = self.chunk.emit(Op.JUMP, -1)
        self.chunk.patch(else_jump, len(self.chunk.code))
        if s.otherwise:
            self.statement(s.otherwise)
        self.chunk.patch(end_jump, len(self.chunk.code))

    def s_while(self, s: ast.While) -> None:
        loop_start = len(self.chunk.code)
        self.expression(s.cond)
        exit_jump = self.chunk.emit(Op.JUMP_IF_FALSE, -1)
        self.statement(s.body)
        self.chunk.emit(Op.JUMP, loop_start)
        self.chunk.patch(exit_jump, len(self.chunk.code))

    def s_return(self, s: ast.Return) -> None:
        if not self.is_function:
            raise CompileError("'return' outside of a function", s.line)
        if s.value is not None:
            self.expression(s.value)
        else:
            self.chunk.emit(Op.CONST, self.chunk.add_const(0))
        self.chunk.emit(Op.RETURN)

    def s_function(self, s: ast.Function) -> None:
        sub = Compiler(s.name, s.params, is_function=True)
        for stmt in s.body.body:
            sub.statement(stmt)
        sub.chunk.emit(Op.CONST, sub.chunk.add_const(0))   # implicit `return 0`
        sub.chunk.emit(Op.RETURN)
        fn = Function(s.name, len(s.params), sub.chunk)
        idx = self.chunk.add_const(fn)
        self.chunk.emit(Op.CONST, idx)
        if self.scope_depth == 0 and not self.is_function:
            self.chunk.emit(Op.DEF_GLOBAL, self.chunk.add_const(s.name))
        else:
            self.declare_local(s.name)

    # -- expressions --------------------------------------
    def expression(self, e: ast.Expr) -> None:
        method = getattr(self, "e_" + type(e).__name__.lower())
        method(e)

    def e_intlit(self, e: ast.IntLit) -> None:
        self.chunk.emit(Op.CONST, self.chunk.add_const(e.value))

    def e_boollit(self, e: ast.BoolLit) -> None:
        self.chunk.emit(Op.CONST, self.chunk.add_const(e.value))

    def e_var(self, e: ast.Var) -> None:
        slot = self.resolve_local(e.name)
        if slot is not None:
            self.chunk.emit(Op.GET_LOCAL, slot)
        else:
            self.chunk.emit(Op.GET_GLOBAL, self.chunk.add_const(e.name))

    def e_unary(self, e: ast.Unary) -> None:
        self.expression(e.operand)
        self.chunk.emit(Op.NEG if e.op == "-" else Op.NOT)

    def e_binary(self, e: ast.Binary) -> None:
        if e.op == "&&":
            self.expression(e.left)
            j = self.chunk.emit(Op.JUMP_IF_FALSE_KEEP, -1)
            self.chunk.emit(Op.POP)
            self.expression(e.right)
            self.chunk.patch(j, len(self.chunk.code))
            return
        if e.op == "||":
            self.expression(e.left)
            j = self.chunk.emit(Op.JUMP_IF_TRUE_KEEP, -1)
            self.chunk.emit(Op.POP)
            self.expression(e.right)
            self.chunk.patch(j, len(self.chunk.code))
            return
        self.expression(e.left)
        self.expression(e.right)
        self.chunk.emit(_BINOP[e.op])

    def e_call(self, e: ast.Call) -> None:
        self.chunk.emit(Op.GET_GLOBAL, self.chunk.add_const(e.callee))
        for arg in e.args:
            self.expression(arg)
        self.chunk.emit(Op.CALL, len(e.args))


def compile_source(program: ast.Program) -> Chunk:
    return Compiler().compile_program(program)


def dump(program: ast.Program) -> str:
    return disassemble(compile_source(program))
