from slang import ast
from slang.optimizer import optimize
from slang.parser import parse


def first_value(src):
    return optimize(parse(src)).body[0].value


def int_lit(node, value):
    return isinstance(node, ast.IntLit) and node.value == value


def bool_lit(node, value):
    return isinstance(node, ast.BoolLit) and node.value is value


def test_constant_folding_arithmetic():
    assert int_lit(first_value("let x = 2 * 3 + 4 - 1;"), 9)
    assert int_lit(first_value("let x = 10 % 3;"), 1)


def test_constant_folding_comparison_and_logic():
    assert bool_lit(first_value("let x = 3 < 5;"), True)
    assert bool_lit(first_value("let x = true && false;"), False)
    assert bool_lit(first_value("let x = !false;"), True)


def test_does_not_fold_division_by_zero():
    v = first_value("let x = 1 / 0;")
    assert isinstance(v, ast.Binary)  # left for the VM to raise at run time


def test_dead_branch_elimination():
    prog = optimize(parse("if (1 < 2) { print 1; } else { print 2; }"))
    # the whole if collapses to the taken block
    assert isinstance(prog.body[0], ast.Block)
    assert isinstance(prog.body[0].body[0], ast.Print)


def test_while_false_removed():
    prog = optimize(parse("while (2 > 3) { print 1; }"))
    assert isinstance(prog.body[0], ast.Block) and prog.body[0].body == []


def test_partial_fold_keeps_variables():
    v = first_value("let x = a + 2 * 3;")
    assert isinstance(v, ast.Binary) and v.op == "+"
    assert int_lit(v.right, 6) and isinstance(v.left, ast.Var)
