# Slang — a compiler for a small language

**▶ Live playground: https://slang-playground.vercel.app** — write Slang in the
browser and see the output, the AST, the bytecode disassembly, or the
transpiled C (runs on a Vercel Python function; code in [`web/`](web/)).

A complete little compiler in pure Python, no dependencies. It takes a
C-flavoured toy language and runs it two ways:

1. **Front end** — hand-written lexer → **Pratt parser** → typed AST → a
   constant-folding **optimizer** pass.
2. **Back end #1** — AST → **bytecode** → a **stack virtual machine** that
   executes it.
3. **Back end #2** — AST → **portable C99** you can hand to `cc`.

Same AST, two targets. For integer programs the VM and the compiled C binary
produce byte-identical output (enforced in CI).

```
source ──▶ lexer ──▶ Pratt parser ──▶ AST ──▶ optimizer ──▶ AST
                                                              │
                                          ┌───────────────────┴───────────────┐
                                          ▼                                   ▼
                                  compiler → bytecode                  transpile_c → C99
                                          ▼                                   ▼
                                   stack VM → output                    cc → a.out → output
```

## The language

```rust
// recursive fibonacci
fn fib(n) {
    if (n < 2) { return n; }
    return fib(n - 1) + fib(n - 2);
}

let i = 0;
while (i < 15) {
    print fib(i);
    i = i + 1;
}
```

`int` and `bool`; `let`, assignment, block scope with shadowing; `fn` with
parameters, recursion and mutual recursion; `if / else if / else`; `while`;
`return`; `print`. Arithmetic `+ - * / %`, comparison `== != < > <= >=`,
logical `&& || !` with short-circuit evaluation. `//` and `/* */` comments.

## Quick start

```bash
git clone https://github.com/pastbologanesh0101/small-lang-compiler
cd small-lang-compiler
pip install -e ".[dev]"
pytest -q                              # 41 tests

slang run    examples/fib.sl           # execute on the bytecode VM
slang ast    examples/gcd.sl           # dump the AST
slang disasm examples/gcd.sl           # show the bytecode
slang cc     examples/fib.sl -o fib.c  # emit C
cc fib.c -o fib && ./fib               # ...and it matches `slang run`
```

## Concepts demonstrated

| Area | Where | What it shows |
|---|---|---|
| **Lexing** | `slang/lexer.py` | Hand-written scanner: maximal-munch operators (`==` before `=`), keyword/identifier split, nested block comments, line/column tracking for diagnostics. |
| **Parsing** | `slang/parser.py` | **Pratt parsing** — one precedence table drives all infix operators; recursive descent for statements. Left-associativity, unary binding, `else if` chains, `x = e` vs expression-statement disambiguation. |
| **AST** | `slang/ast.py` | Typed dataclass nodes, each with a source line. |
| **Optimization** | `slang/optimizer.py` | AST→AST constant folding, dead-branch elimination (`if (true)`, `while (false)`), short-circuit simplification — with a test that output is identical with and without it. |
| **Code generation** | `slang/compiler.py` + `slang/bytecode.py` | AST → bytecode for a stack machine: constant pool with de-dup, jump patching for control flow, globals-by-name vs stack-slot locals, scope enter/exit, function hoisting. Includes a disassembler. |
| **Execution** | `slang/vm.py` | A stack VM with call frames (`chunk`, `ip`, `base`), locals at `stack[base+slot]`, a recursion guard, and runtime type checks (`true + 1` is an error). |
| **A real target** | `slang/transpile_c.py` | The same AST lowered to C: forward declarations, top-level `let` hoisted into `main`, control flow passed straight through. CI compiles it with `-Wall -Werror` and diffs the output against the VM. |

## Example: how `1 + 2 * 3` becomes bytecode

```
$ echo 'print 1 + 2 * 3;' | slang disasm /dev/stdin
0000  CONST   0  ; 1
0001  CONST   1  ; 2
0002  CONST   2  ; 3
0003  MUL
0004  ADD
0005  PRINT
0006  HALT
```

The parser already nested `*` under `+` (precedence); the compiler just does a
post-order walk emitting operands then the operator — classic stack-machine
codegen.

## Two backends, one semantics

The bytecode VM is the reference. The C backend is an *integer lowering*: every
value is a C `long`, so `print` of a boolean shows `1`/`0` instead of
`true`/`false`. For integer programs (`examples/fib.sl`, `gcd.sl`, `primes.sl`)
the outputs are identical and `tests/test_transpile_c.py` compiles and runs the
C to prove it.

## Limitations

- Two types only (`int`, `bool`); no strings, arrays, structs, or floats.
- No static type checker — type errors surface at run time on the VM.
- The C backend rejects nested functions; no closures in either backend.
- Tree-walking optimizer only (no SSA, no register allocation, no peephole on
  the bytecode).

## Project layout

```
slang/
  lexer.py         source -> tokens
  ast.py           node definitions
  parser.py        Pratt parser -> AST
  optimizer.py     constant folding / dead-branch elimination
  bytecode.py      Op enum, Chunk, disassembler
  compiler.py      AST -> bytecode
  vm.py            stack VM
  transpile_c.py   AST -> C99
  cli.py           run / ast / disasm / cc
examples/          fib, fizzbuzz, gcd, primes
tests/             lexer / parser / optimizer / run (VM) / transpile_c (cc parity)
```

## License

MIT
