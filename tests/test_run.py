"""Execute Slang programs on the bytecode VM and check their output."""

import pytest

from slang import run
from slang.vm import SlangRuntimeError


def out(src, **kw):
    return run(src, **kw).strip().splitlines()


def test_arithmetic_and_precedence():
    assert out("print 1 + 2 * 3 - 4;") == ["3"]
    assert out("print (1 + 2) * 3;") == ["9"]
    assert out("print 7 / 2; print 7 % 2; print -7 / 2;") == ["3", "1", "-3"]


def test_booleans_and_comparison():
    assert out("print 1 < 2; print 2 <= 2; print 3 == 3; print 1 != 1;") == \
        ["true", "true", "true", "false"]
    assert out("print true && false; print true || false; print !true;") == \
        ["false", "true", "false"]


def test_short_circuit_does_not_evaluate_rhs():
    src = """
    fn boom() { print 999; return true; }
    print false && boom();
    print true || boom();
    """
    assert out(src) == ["false", "true"]   # boom() never runs -> no 999


def test_globals_locals_and_assignment():
    src = """
    let x = 10;
    x = x + 5;
    { let x = 1; print x; }   // shadow in a block
    print x;
    """
    assert out(src) == ["1", "15"]


def test_while_loop():
    assert out("let i = 0; let s = 0; while (i < 5) { s = s + i; i = i + 1; } print s;") == ["10"]


def test_if_elseif_else():
    def classify(n):
        return f"let n = {n}; if (n < 0) {{ print 0; }} else if (n == 0) {{ print 1; }} else {{ print 2; }}"
    assert out(classify(-3)) == ["0"]
    assert out(classify(0)) == ["1"]
    assert out(classify(7)) == ["2"]


def test_recursion_fib():
    src = "fn fib(n){ if(n<2){return n;} return fib(n-1)+fib(n-2); } print fib(20);"
    assert out(src) == ["6765"]


def test_mutual_recursion():
    src = """
    fn is_even(n) { if (n == 0) { return true; } return is_odd(n - 1); }
    fn is_odd(n)  { if (n == 0) { return false; } return is_even(n - 1); }
    print is_even(10); print is_odd(10);
    """
    assert out(src) == ["true", "false"]


def test_examples_match_expected(tmp_path):
    import pathlib
    ex = pathlib.Path(__file__).parent.parent / "examples"
    assert out(ex.joinpath("gcd.sl").read_text()) == ["21", "12"]
    assert out(ex.joinpath("primes.sl").read_text())[:5] == ["2", "3", "5", "7", "11"]
    assert out(ex.joinpath("fib.sl").read_text())[:8] == \
        ["0", "1", "1", "2", "3", "5", "8", "13"]


def test_runtime_errors():
    with pytest.raises(SlangRuntimeError, match="division by zero"):
        run("print 1 / 0;")
    with pytest.raises(SlangRuntimeError, match="undefined name"):
        run("print notdefined;")
    with pytest.raises(SlangRuntimeError, match="int"):
        run("print true + 1;")
    with pytest.raises(SlangRuntimeError, match="argument"):
        run("fn f(a){return a;} print f(1, 2);")


def test_optimizer_preserves_semantics():
    src = "print 2 * 3 + 4; if (1 < 2) { print 10; } else { print 20; } let i = 0; while (false) { print 99; } print i;"
    assert run(src, optimize_ast=True).strip() == run(src, optimize_ast=False).strip()
