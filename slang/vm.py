"""A stack-based virtual machine that executes a compiled :class:`Chunk`.

Model: one value stack shared by all calls; a frame records ``(chunk, ip,
base)`` where ``base`` is the index in the value stack of a call's slot 0. Local
variable ``slot`` lives at ``stack[base + slot]``.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from .bytecode import Chunk, Function, Op

MAX_FRAMES = 4000


class SlangRuntimeError(Exception):
    pass


@dataclass
class Frame:
    chunk: Chunk
    ip: int
    base: int


def _truthy(v) -> bool:
    return v is True or (v is not False and v != 0)


def _fmt(v) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


class VM:
    def __init__(self, chunk: Chunk, stdout: io.TextIOBase | None = None):
        self.frames = [Frame(chunk, 0, 0)]
        self.stack: list = []
        self.globals: dict = {}
        self.stdout = stdout or io.StringIO()

    # convenience for tests / CLI
    @classmethod
    def run_chunk(cls, chunk: Chunk) -> str:
        vm = cls(chunk)
        vm.run()
        return vm.stdout.getvalue()

    # -- helpers --------------------------------------------
    @property
    def frame(self) -> Frame:
        return self.frames[-1]

    def _num(self, v, op: str):
        if isinstance(v, bool) or not isinstance(v, int):
            raise SlangRuntimeError(f"operator '{op}' expects an int, got {_fmt(v)}")
        return v

    def _bool(self, v, op: str):
        if not isinstance(v, bool):
            raise SlangRuntimeError(f"operator '{op}' expects a bool, got {_fmt(v)}")
        return v

    # -- main loop -----------------------------------------
    def run(self) -> None:
        stack = self.stack
        while True:
            frame = self.frame
            if frame.ip >= len(frame.chunk.code):
                return
            op, *operands = frame.chunk.code[frame.ip]
            frame.ip += 1

            if op is Op.CONST:
                stack.append(frame.chunk.constants[operands[0]])
            elif op is Op.POP:
                stack.pop()
            elif op is Op.PRINT:
                self.stdout.write(_fmt(stack.pop()) + "\n")

            elif op is Op.NEG:
                stack.append(-self._num(stack.pop(), "-"))
            elif op is Op.NOT:
                stack.append(not self._bool(stack.pop(), "!"))

            elif op in _ARITH:
                b = self._num(stack.pop(), op.name)
                a = self._num(stack.pop(), op.name)
                if op in (Op.DIV, Op.MOD) and b == 0:
                    raise SlangRuntimeError("division by zero")
                stack.append(_ARITH[op](a, b))

            elif op is Op.EQ:
                b, a = stack.pop(), stack.pop()
                stack.append(a == b and type(a) is type(b))
            elif op is Op.NE:
                b, a = stack.pop(), stack.pop()
                stack.append(not (a == b and type(a) is type(b)))
            elif op in _CMP:
                b = self._num(stack.pop(), op.name)
                a = self._num(stack.pop(), op.name)
                stack.append(_CMP[op](a, b))

            elif op is Op.JUMP:
                frame.ip = operands[0]
            elif op is Op.JUMP_IF_FALSE:
                if not _truthy(stack.pop()):
                    frame.ip = operands[0]
            elif op is Op.JUMP_IF_FALSE_KEEP:
                if not _truthy(stack[-1]):
                    frame.ip = operands[0]
            elif op is Op.JUMP_IF_TRUE_KEEP:
                if _truthy(stack[-1]):
                    frame.ip = operands[0]

            elif op is Op.GET_LOCAL:
                stack.append(stack[frame.base + operands[0]])
            elif op is Op.SET_LOCAL:
                stack[frame.base + operands[0]] = stack[-1]
            elif op is Op.GET_GLOBAL:
                name = frame.chunk.constants[operands[0]]
                if name not in self.globals:
                    raise SlangRuntimeError(f"undefined name '{name}'")
                stack.append(self.globals[name])
            elif op is Op.SET_GLOBAL:
                name = frame.chunk.constants[operands[0]]
                if name not in self.globals:
                    raise SlangRuntimeError(f"assignment to undefined name '{name}'")
                self.globals[name] = stack[-1]
            elif op is Op.DEF_GLOBAL:
                self.globals[frame.chunk.constants[operands[0]]] = stack.pop()

            elif op is Op.CALL:
                self._call(operands[0])
            elif op is Op.RETURN:
                self._ret()
            elif op is Op.HALT:
                return
            else:  # pragma: no cover
                raise SlangRuntimeError(f"bad opcode {op}")

    # -- calls ---------------------------------------------
    def _call(self, argc: int) -> None:
        callee = self.stack[-argc - 1]
        if not isinstance(callee, Function):
            raise SlangRuntimeError(f"'{_fmt(callee)}' is not callable")
        if callee.arity != argc:
            raise SlangRuntimeError(
                f"{callee.name}() takes {callee.arity} argument(s), got {argc}")
        if len(self.frames) >= MAX_FRAMES:
            raise SlangRuntimeError("stack overflow (recursion too deep)")
        base = len(self.stack) - argc
        self.frames.append(Frame(callee.chunk, 0, base))

    def _ret(self) -> None:
        result = self.stack.pop()
        base = self.frame.base
        del self.stack[base - 1:]     # drop args + the callee slot
        self.frames.pop()
        self.stack.append(result)
        if not self.frames:  # pragma: no cover - compiler prevents top-level return
            raise SlangRuntimeError("return from top level")


_ARITH = {
    Op.ADD: lambda a, b: a + b,
    Op.SUB: lambda a, b: a - b,
    Op.MUL: lambda a, b: a * b,
    Op.DIV: lambda a, b: int(a / b),   # truncate toward zero, like C
    Op.MOD: lambda a, b: a - int(a / b) * b,
}
_CMP = {
    Op.LT: lambda a, b: a < b,
    Op.GT: lambda a, b: a > b,
    Op.LE: lambda a, b: a <= b,
    Op.GE: lambda a, b: a >= b,
}
