"""A Pratt (precedence-climbing) parser: tokens -> AST.

Statement parsing is plain recursive descent; expression parsing uses a prefix
+ infix table keyed by token type, which keeps operator precedence in one
readable place.
"""

from __future__ import annotations

from . import ast
from .errors import ParseError
from .lexer import T, Token, tokenize

# Binding power for infix operators (higher = tighter).
PRECEDENCE = {
    T.OR: 1,
    T.AND: 2,
    T.EQ: 3, T.NE: 3,
    T.LT: 4, T.GT: 4, T.LE: 4, T.GE: 4,
    T.PLUS: 5, T.MINUS: 5,
    T.STAR: 6, T.SLASH: 6, T.PERCENT: 6,
}


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # -- token helpers ------------------------------------------
    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type is not T.EOF:
            self.pos += 1
        return tok

    def check(self, ttype: T) -> bool:
        return self.cur.type is ttype

    def match(self, *ttypes: T) -> Token | None:
        if self.cur.type in ttypes:
            return self.advance()
        return None

    def expect(self, ttype: T, what: str) -> Token:
        if not self.check(ttype):
            raise ParseError(f"expected {what}, got {self.cur.value!r}",
                             self.cur.line, self.cur.col)
        return self.advance()

    # -- entry point ------------------------------------------
    def parse_program(self) -> ast.Program:
        prog = ast.Program()
        while not self.check(T.EOF):
            prog.body.append(self.statement())
        return prog

    # -- statements -----------------------------------------
    def statement(self) -> ast.Stmt:
        t = self.cur.type
        if t is T.LET:
            return self.let_stmt()
        if t is T.FN:
            return self.function()
        if t is T.IF:
            return self.if_stmt()
        if t is T.WHILE:
            return self.while_stmt()
        if t is T.RETURN:
            return self.return_stmt()
        if t is T.PRINT:
            return self.print_stmt()
        if t is T.LBRACE:
            return self.block()
        return self.expr_or_assign()

    def let_stmt(self) -> ast.Let:
        kw = self.advance()
        name = self.expect(T.IDENT, "variable name").value
        self.expect(T.ASSIGN, "'='")
        value = self.expression()
        self.expect(T.SEMI, "';'")
        return ast.Let(name, value, kw.line)

    def function(self) -> ast.Function:
        kw = self.advance()
        name = self.expect(T.IDENT, "function name").value
        self.expect(T.LPAREN, "'('")
        params: list[str] = []
        if not self.check(T.RPAREN):
            params.append(self.expect(T.IDENT, "parameter name").value)
            while self.match(T.COMMA):
                params.append(self.expect(T.IDENT, "parameter name").value)
        self.expect(T.RPAREN, "')'")
        body = self.block()
        return ast.Function(name, params, body, kw.line)

    def if_stmt(self) -> ast.If:
        kw = self.advance()
        self.expect(T.LPAREN, "'('")
        cond = self.expression()
        self.expect(T.RPAREN, "')'")
        then = self.block()
        otherwise = None
        if self.match(T.ELSE):
            otherwise = self.if_stmt_as_block() if self.check(T.IF) else self.block()
        return ast.If(cond, then, otherwise, kw.line)

    def if_stmt_as_block(self) -> ast.Block:
        inner = self.if_stmt()
        return ast.Block([inner], inner.line)

    def while_stmt(self) -> ast.While:
        kw = self.advance()
        self.expect(T.LPAREN, "'('")
        cond = self.expression()
        self.expect(T.RPAREN, "')'")
        body = self.block()
        return ast.While(cond, body, kw.line)

    def return_stmt(self) -> ast.Return:
        kw = self.advance()
        value = None
        if not self.check(T.SEMI):
            value = self.expression()
        self.expect(T.SEMI, "';'")
        return ast.Return(value, kw.line)

    def print_stmt(self) -> ast.Print:
        kw = self.advance()
        value = self.expression()
        self.expect(T.SEMI, "';'")
        return ast.Print(value, kw.line)

    def block(self) -> ast.Block:
        lb = self.expect(T.LBRACE, "'{'")
        body: list[ast.Stmt] = []
        while not self.check(T.RBRACE) and not self.check(T.EOF):
            body.append(self.statement())
        self.expect(T.RBRACE, "'}'")
        return ast.Block(body, lb.line)

    def expr_or_assign(self) -> ast.Stmt:
        expr = self.expression()
        if isinstance(expr, ast.Var) and self.check(T.ASSIGN):
            self.advance()
            value = self.expression()
            self.expect(T.SEMI, "';'")
            return ast.Assign(expr.name, value, expr.line)
        self.expect(T.SEMI, "';'")
        return ast.ExprStmt(expr, expr.line)

    # -- expressions (Pratt) -------------------------------
    def expression(self, min_bp: int = 0) -> ast.Expr:
        left = self.prefix()
        while True:
            bp = PRECEDENCE.get(self.cur.type, 0)
            if bp <= min_bp:
                break
            op = self.advance()
            right = self.expression(bp)   # left-assoc: recurse with this bp
            left = ast.Binary(op.value, left, right, op.line)
        return left

    def prefix(self) -> ast.Expr:
        tok = self.cur
        if tok.type is T.INT:
            self.advance()
            return ast.IntLit(int(tok.value), tok.line)
        if tok.type in (T.TRUE, T.FALSE):
            self.advance()
            return ast.BoolLit(tok.type is T.TRUE, tok.line)
        if tok.type in (T.MINUS, T.NOT):
            self.advance()
            operand = self.expression(7)  # unary binds tighter than any binary
            return ast.Unary(tok.value, operand, tok.line)
        if tok.type is T.LPAREN:
            self.advance()
            inner = self.expression()
            self.expect(T.RPAREN, "')'")
            return inner
        if tok.type is T.IDENT:
            self.advance()
            if self.check(T.LPAREN):
                return self.finish_call(tok)
            return ast.Var(tok.value, tok.line)
        raise ParseError(f"unexpected token {tok.value!r} in expression",
                         tok.line, tok.col)

    def finish_call(self, name_tok: Token) -> ast.Call:
        self.expect(T.LPAREN, "'('")
        args: list[ast.Expr] = []
        if not self.check(T.RPAREN):
            args.append(self.expression())
            while self.match(T.COMMA):
                args.append(self.expression())
        self.expect(T.RPAREN, "')'")
        return ast.Call(name_tok.value, args, name_tok.line)


def parse(source: str) -> ast.Program:
    return Parser(tokenize(source)).parse_program()
