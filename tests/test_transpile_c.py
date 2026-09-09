"""The C backend: transpile, compile with cc, run, and require the output to
match the bytecode VM for integer programs."""

import pathlib
import shutil
import subprocess

import pytest

from slang import run, to_c
from slang.parser import parse

cc = shutil.which("cc") or shutil.which("gcc")
pytestmark = pytest.mark.skipif(not cc, reason="no C compiler available")

EX = pathlib.Path(__file__).parent.parent / "examples"


def compile_and_run(src: str, tmp_path) -> str:
    c_path = tmp_path / "prog.c"
    bin_path = tmp_path / "prog"
    c_path.write_text(to_c(parse(src)))
    subprocess.run([cc, "-O2", "-std=c99", "-Wall", "-Werror",
                    "-o", str(bin_path), str(c_path)], check=True,
                   capture_output=True)
    return subprocess.run([str(bin_path)], capture_output=True, text=True,
                          check=True).stdout


@pytest.mark.parametrize("name", ["fib.sl", "gcd.sl", "primes.sl"])
def test_c_output_matches_vm(name, tmp_path):
    src = (EX / name).read_text()
    assert compile_and_run(src, tmp_path).strip() == run(src).strip()


def test_generated_c_compiles_clean(tmp_path):
    # -Wall -Werror in compile_and_run means warnings fail the test.
    src = """
    fn add(a, b) { return a + b; }
    let x = add(2, 3);
    let y = 0;
    while (y < x) { print y; y = y + 1; }
    """
    assert compile_and_run(src, tmp_path).strip().splitlines() == ["0", "1", "2", "3", "4"]


def test_nested_function_rejected():
    from slang.errors import CompileError
    with pytest.raises(CompileError):
        to_c(parse("fn outer() { fn inner() { return 1; } return inner(); }"))
