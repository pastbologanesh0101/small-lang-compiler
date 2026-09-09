import pytest

from slang.errors import LexError
from slang.lexer import T, tokenize


def types(src):
    return [t.type for t in tokenize(src)]


def test_keywords_vs_identifiers():
    toks = tokenize("let fn iffy if while_ return")
    assert [t.type for t in toks[:6]] == [
        T.LET, T.FN, T.IDENT, T.IF, T.IDENT, T.RETURN
    ]
    assert toks[2].value == "iffy"
    assert toks[4].value == "while_"


def test_two_char_operators_beat_one_char():
    assert types("a == b != c <= d >= e && f || g") == [
        T.IDENT, T.EQ, T.IDENT, T.NE, T.IDENT, T.LE, T.IDENT, T.GE,
        T.IDENT, T.AND, T.IDENT, T.OR, T.IDENT, T.EOF,
    ]


def test_line_and_column_tracking():
    toks = tokenize("let x = 1;\n  y = 2;")
    y = [t for t in toks if t.value == "y"][0]
    assert (y.line, y.col) == (2, 3)


def test_comments_are_skipped():
    src = "let a = 1; // trailing\n/* block\n spanning */ let b = 2;"
    vals = [t.value for t in tokenize(src) if t.type != T.EOF]
    assert vals == ["let", "a", "=", "1", ";", "let", "b", "=", "2", ";"]


def test_unterminated_block_comment():
    with pytest.raises(LexError):
        tokenize("/* never ends")


def test_bad_number_and_char():
    with pytest.raises(LexError):
        tokenize("123abc")
    with pytest.raises(LexError):
        tokenize("a $ b")
