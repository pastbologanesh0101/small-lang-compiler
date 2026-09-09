import pytest

from slang import ast
from slang.errors import ParseError
from slang.parser import parse


def test_precedence_and_associativity():
    prog = parse("let x = 1 + 2 * 3 - 4;")
    # (1 + (2*3)) - 4
    e = prog.body[0].value
    assert isinstance(e, ast.Binary) and e.op == "-"
    assert isinstance(e.left, ast.Binary) and e.left.op == "+"
    assert e.left.right.op == "*"


def test_left_associative_subtraction():
    e = parse("let x = 10 - 3 - 2;").body[0].value
    # (10 - 3) - 2  == 5, not 10 - (3 - 2) == 9
    assert e.op == "-" and e.left.op == "-"
    assert e.left.left.value == 10 and e.right.value == 2


def test_comparison_below_arithmetic():
    e = parse("let b = 1 + 2 < 3 * 4;").body[0].value
    assert e.op == "<"
    assert e.left.op == "+" and e.right.op == "*"


def test_unary_binds_tight():
    e = parse("let x = -2 * 3;").body[0].value
    assert e.op == "*" and isinstance(e.left, ast.Unary)


def test_function_and_call():
    prog = parse("fn add(a, b) { return a + b; } print add(2, 3);")
    fn = prog.body[0]
    assert isinstance(fn, ast.Function) and fn.params == ["a", "b"]
    call = prog.body[1].expr
    assert isinstance(call, ast.Call) and call.callee == "add" and len(call.args) == 2


def test_if_else_if_chain():
    prog = parse("if (a) { print 1; } else if (b) { print 2; } else { print 3; }")
    node = prog.body[0]
    assert isinstance(node, ast.If)
    assert isinstance(node.otherwise, ast.Block)
    assert isinstance(node.otherwise.body[0], ast.If)


def test_assignment_vs_expr_statement():
    prog = parse("x = 5; foo();")
    assert isinstance(prog.body[0], ast.Assign)
    assert isinstance(prog.body[1], ast.ExprStmt)


@pytest.mark.parametrize("src", [
    "let x = ;",
    "fn f( { }",
    "if x { }",           # missing parens
    "let 3 = x;",
    "print 1",            # missing semicolon
    "return 1;",          # ok syntactically; compiler rejects at top level
])
def test_parse_errors_have_location(src):
    if src == "return 1;":
        parse(src)  # this one parses fine
        return
    with pytest.raises(ParseError) as ei:
        parse(src)
    assert ei.value.line >= 1
