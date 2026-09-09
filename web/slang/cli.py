"""``slang`` command line.

    slang run     prog.sl            parse -> optimize -> compile -> run on the VM
    slang ast     prog.sl            pretty-print the AST
    slang disasm  prog.sl            show the bytecode
    slang cc      prog.sl -o out.c   emit C  (then: cc out.c && ./a.out)
"""

from __future__ import annotations

import argparse
import sys
from pprint import pformat

from . import compiler, optimizer
from .bytecode import disassemble
from .errors import SlangError
from .parser import parse
from .transpile_c import to_c
from .vm import VM, SlangRuntimeError


def _load(path: str) -> str:
    with open(path) as f:
        return f.read()


def _frontend(src: str, do_opt: bool):
    prog = parse(src)
    return optimizer.optimize(prog) if do_opt else prog


def cmd_run(ns) -> int:
    src = _load(ns.file)
    try:
        prog = _frontend(src, not ns.no_opt)
        vm = VM(compiler.compile_source(prog), stdout=sys.stdout)
        vm.run()
    except SlangError as e:
        print(e.render(src, ns.file), file=sys.stderr)
        return 1
    except SlangRuntimeError as e:
        print(f"{ns.file}: runtime error: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_ast(ns) -> int:
    src = _load(ns.file)
    try:
        prog = _frontend(src, not ns.no_opt)
    except SlangError as e:
        print(e.render(src, ns.file), file=sys.stderr)
        return 1
    print(pformat(prog, width=100))
    return 0


def cmd_disasm(ns) -> int:
    src = _load(ns.file)
    try:
        prog = _frontend(src, not ns.no_opt)
        chunk = compiler.compile_source(prog)
    except SlangError as e:
        print(e.render(src, ns.file), file=sys.stderr)
        return 1
    print(disassemble(chunk))
    return 0


def cmd_cc(ns) -> int:
    src = _load(ns.file)
    try:
        prog = _frontend(src, not ns.no_opt)
        code = to_c(prog)
    except SlangError as e:
        print(e.render(src, ns.file), file=sys.stderr)
        return 1
    if ns.output and ns.output != "-":
        with open(ns.output, "w") as f:
            f.write(code)
        print(f"wrote {ns.output}", file=sys.stderr)
    else:
        sys.stdout.write(code)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="slang")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, extra in [
        ("run", cmd_run, None),
        ("ast", cmd_ast, None),
        ("disasm", cmd_disasm, None),
        ("cc", cmd_cc, "output"),
    ]:
        s = sub.add_parser(name)
        s.add_argument("file")
        s.add_argument("--no-opt", action="store_true", help="skip the optimizer pass")
        if extra == "output":
            s.add_argument("-o", "--output", default="-", help="output path ('-' = stdout)")
        s.set_defaults(func=fn)
    return p


def main(argv=None) -> int:
    ns = build_parser().parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    raise SystemExit(main())
