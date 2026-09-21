#!/usr/bin/env python3
"""Minimal SQF evaluator (issue #204).

Executes the ACTUAL solver SQF files in the test suite instead of a
hand-transcribed Python mirror.  The mirror approach failed: the
mirror replicated the SQF's bugs (the shivering term applied to inert
objects) AND drifted from the source, and neither was caught because
the mirror test was not in the gate suite.  If a test cannot execute
the SQF it is not testing the mod.

Scope: the SQF subset used by the thermal solver functions.  This is
a TEST-HARNESS interpreter, not a general SQF engine:

  statements   private _x = EXPR;  EXPR;  if (C) then {..} else {..};
               for "_i" from A to B do {..};  params [[..],..];
  expressions  numbers, strings, arrays [a,b], vars _x
               a + b  a - b  a * b  a / b  a ^ b
               a < b  a > b  a <= b  a >= b  a == b  a != b
               a && b  a || b  !a
               (a max b)  (a min b)  (exp x)
               arr select i  [a, b] select C   (boolean select)
               args call FNC  (function value in a variable)
               FUNC(getMaterialThermal)  (resolved via the registry)
  globals      overcast, diag_deltaTime, rain - injected as numbers

Engine commands outside this subset are resolved through the `globals`
dict passed to SqfProgram.run.  The solver functions use only
FUNC(getMaterialThermal) (registry lookup, stubbed with the real
registry from fnc_getMaterialThermal.sqf) and the `overcast` global.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ─── Tokeniser ──────────────────────────────────────────────────────────────
TOKEN_RE = re.compile(
    r"""
    \s+                                  # whitespace
  | //[^\n]*                             # line comment
  | \#[^\n]*                             # preprocessor line (skip in header)
  | "(?:\\.|[^"\\])*"                    # string
  | \d+\.\d+(?:[eE][+-]?\d+)?|\d+(?:[eE][+-]?\d+)?| \d+\.\d+|\d+    # number
  | [a-zA-Z_][a-zA-Z0-9_]*               # identifier / command
  | &&|\|\|                             # logical operators (before singles)
  | <=|>=|==|!=                         # comparison operators (before singles)
  | \[|\]|\{|\}|\(|\)|,|;                # punctuation
  | [+\-*/^<>=!&|]                       # operators
    """,
    re.VERBOSE,
)


@dataclass
class Tok:
    kind: str  # num, str, id, op, punct
    value: Any
    pos: int


def tokenize(text: str) -> list[Tok]:
    toks: list[Tok] = []
    for m in TOKEN_RE.finditer(text):
        s = m.group(0)
        if not s.strip():
            continue
        if s.startswith("//") or s.startswith("#"):
            continue
        if s.startswith('"'):
            toks.append(Tok("str", s[1:-1], m.start()))
        elif re.fullmatch(r"\d+\.\d+(?:[eE][+-]?\d+)?|\d+(?:[eE][+-]?\d+)?", s):
            toks.append(Tok("num", float(s), m.start()))
        elif s in ("&&", "||"):
            toks.append(Tok("punct", s, m.start()))
        elif s in "[]{}();,+-*/^<>=!&|":
            toks.append(Tok("punct", s, m.start()))
        else:
            toks.append(Tok("id", s, m.start()))
    return toks


# ─── AST ────────────────────────────────────────────────────────────────────
@dataclass
class Num:
    v: float


@dataclass
class Str:
    v: str


@dataclass
class Var:
    name: str


@dataclass
class Arr:
    items: list


@dataclass
class Bin:
    op: str
    left: Any
    right: Any


@dataclass
class Call:
    fn: Any
    args: Any


@dataclass
class Select:
    arr: Any
    idx: Any


@dataclass
class MaxMin:
    op: str  # "max" | "min"
    left: Any
    right: Any


@dataclass
class Exp:
    arg: Any


@dataclass
class Assign:
    name: str
    expr: Any


BINARY_COMMANDS = {"getVariable", "isEqualType"}


@dataclass
class ExprStmt:
    expr: Any


@dataclass
class If:
    cond: Any
    then: list
    els: list


class ExitSignal(Exception):
    """Raised by `if (cond) exitWith {value}` - stops the program and
    returns the exit value (issue #162: fnc_readState uses exitWith)."""


@dataclass
class ExitWith:
    cond: Any
    value: list


@dataclass
class For:
    var: str
    lo: Any
    hi: Any
    body: list


@dataclass
class Params:
    specs: list  # (name, default)


@dataclass
class Lambda:
    params: list
    body: list
    closure: dict


# ─── Parser (recursive descent) ─────────────────────────────────────────────
class SqfParser:
    def __init__(self, toks: list[Tok]):
        self.toks = toks
        self.i = 0

    def peek(self) -> Tok | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def peekv(self) -> str | None:
        """Value of the current token, or None at EOF.  Avoids the
        type-narrowing problem of reading .value off an Optional."""
        t = self.peek()
        return t.value if t is not None else None

    def next(self) -> Tok:
        t = self.peek()
        assert t is not None, "unexpected EOF"
        self.i += 1
        return t

    def expect(self, val: str) -> Tok:
        t = self.next()
        if t.value != val:
            raise SyntaxError(f"expected {val}, got {t.value} @ {t.pos}")
        return t

    # ── statements ──
    def parse_program(self) -> list:
        stmts = []
        while self.peek() is not None:
            stmts.append(self.parse_stmt())
        return stmts

    def parse_stmt(self):
        t = self.peek()
        assert t is not None
        if t.value == "private":
            self.next()
            name = self.next()
            assert name.value.startswith("_"), f"private {name.value}"
            self.expect("=")
            expr = self.parse_expr()
            self.optional_semi()
            return Assign(name.value, expr)
        if t.kind == "id" and t.value.startswith("_"):
            # bare assignment inside a block: _x = expr;
            name = self.next()
            if self.peekv() == "=":
                self.next()
                expr = self.parse_expr()
                self.optional_semi()
                return Assign(name.value, expr)
            # not an assignment - rewind and treat as expression
            self.i -= 1
            expr = self.parse_expr()
            self.optional_semi()
            return ExprStmt(expr)
        if t.value == "params":
            self.next()
            specs = self.parse_params()
            self.optional_semi()
            return Params(specs)
        if t.value == "if":
            self.next()
            # SQF allows `if !(cond)` - the condition may start with a
            # unary operator before the opening paren (issue #162)
            if self.peekv() in ("!", "-"):
                cond = self.parse_unary()
            else:
                self.expect("(")
                cond = self.parse_expr()
                self.expect(")")
            if self.peekv() == "exitWith":
                self.next()
                value = self.parse_block()
                self.optional_semi()
                return ExitWith(cond, value)
            self.expect("then")
            then = self.parse_block()
            els = []
            if self.peekv() == "else":
                self.next()
                els = self.parse_block()
            self.optional_semi()
            return If(cond, then, els)
        if t.value == "for":
            self.next()
            var = self.next()
            # loop var is a quoted string: for "_i" from 1 to 12 do
            if var.kind == "str":
                loop_var = var.value
            elif var.kind == "id":
                loop_var = var.value.strip('"')
            else:
                raise SyntaxError(f"for loop var must be a string, got {var}")
            self.expect("from")
            lo = self.parse_expr()
            self.expect("to")
            hi = self.parse_expr()
            self.expect("do")
            body = self.parse_block()
            self.optional_semi()
            return For(loop_var, lo, hi, body)
        if t.value == "{":
            # bare lambda in expression position handled by parse_expr;
            # here treat as a statement lambda (unlikely in solver).
            return ExprStmt(self.parse_expr())
        expr = self.parse_expr()
        self.optional_semi()
        return ExprStmt(expr)

    def optional_semi(self):
        if self.peekv() == ";":
            self.next()

    def parse_params(self) -> list:
        self.expect("[")
        specs = []
        while self.peekv() != "]":
            self.expect("[")
            name = self.next()
            # SQF params names are QUOTED strings: ["_obj", default, type]
            if name.kind == "str":
                name_value = name.value
            elif name.kind == "id" and name.value.startswith("_"):
                name_value = name.value
            else:
                raise SyntaxError(f"param name must be a string, got {name}")
            self.expect(",")
            default = self.parse_expr()
            # optional [type] tag
            if self.peekv() == ",":
                # could be type tag array or more; consume the type tag
                # array "[0]" / "[true]" / '[""]' if present
                save = self.i
                self.next()  # comma
                if self.peekv() == "[":
                    self.next()
                    depth = 1
                    while self.peek() is not None and depth > 0:
                        v = self.next().value
                        if v == "[":
                            depth += 1
                        elif v == "]":
                            depth -= 1
                    self.expect("]")  # close param entry
                else:
                    self.i = save  # no type tag; comma belongs to next entry
                    self.expect(",")
            else:
                self.expect("]")
            specs.append((name_value, default))
            if self.peekv() == ",":
                self.next()
        self.expect("]")
        return specs

    def parse_lambda_params(self) -> list:
        """Simple lambda param list: params ["_x", "_y"]."""
        self.expect("[")
        names = []
        while self.peekv() != "]":
            t = self.next()
            if t.kind != "str":
                raise SyntaxError(f"lambda param must be a string, got {t.value}")
            names.append(t.value)
            if self.peekv() == ",":
                self.next()
        self.expect("]")
        return names

    def parse_block(self) -> list:
        self.expect("{")
        stmts = []
        while self.peekv() != "}":
            stmts.append(self.parse_stmt())
        self.expect("}")
        return stmts

    # ── expressions (SQF precedence: ^ > * / > + - > comparisons > && ||) ──
    def parse_expr(self):
        return self.parse_logical()

    def parse_logical(self):
        left = self.parse_cmp()
        while self.peekv() in ("&&", "||"):
            op = self.next().value
            right = self.parse_cmp()
            left = Bin(op, left, right)
        return left

    def parse_cmp(self):
        left = self.parse_add()
        while self.peekv() in (
            "<",
            ">",
            "<=",
            ">=",
            "==",
            "!=",
        ):
            op = self.next().value
            right = self.parse_add()
            left = Bin(op, left, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.peekv() in ("+", "-"):
            op = self.next().value
            right = self.parse_mul()
            left = Bin(op, left, right)
        return left

    def parse_mul(self):
        left = self.parse_pow()
        while self.peekv() in ("*", "/"):
            op = self.next().value
            right = self.parse_pow()
            left = Bin(op, left, right)
        return left

    def parse_pow(self):
        left = self.parse_unary()
        if self.peekv() == "^":
            self.next()
            right = self.parse_pow()  # right-assoc
            return Bin("^", left, right)
        return left

    def parse_unary(self):
        t = self.peek()
        if t is not None and t.value == "-":
            self.next()
            return Bin("neg", Num(0.0), self.parse_unary())
        if t is not None and t.value == "!":
            self.next()
            return Bin("not", Num(0.0), self.parse_unary())
        # command-like prefix: max/min/exp applied to a following expression
        if t is not None and t.value in ("exp",) and self._is_cmd_use(t.value):
            self.next()
            return Exp(self.parse_unary())
        return self.parse_postfix()

    def _is_cmd_use(self, name: str) -> bool:
        """A bare identifier is a command only if the next token is an
        expression (not an operator / punctuation that ends it)."""
        nxt = self.peek()
        if nxt is None:
            return False
        return nxt.value not in (",", ")", "]", "}", ";")

    def parse_postfix(self):
        left = self.parse_primary()
        while True:
            t = self.peek()
            if t is None:
                return left
            if t.value == "select":
                self.next()
                idx = self.parse_unary()
                left = Select(left, idx)
            elif t.value == "call":
                self.next()
                fn = self.parse_unary()
                left = Call(fn, left)
            elif t.value == "max" or t.value == "min":
                self.next()
                right = self.parse_unary()
                left = MaxMin(t.value, left, right)
            elif t.value in BINARY_COMMANDS:
                # binary command form: NS getVariable [k, d] - the
                # left operand is the namespace, the command's arg is
                # the right expression.  Resolved as Call(cmd,
                # [left, argArray]) (issue #162).
                cmd = self.next().value
                right = self.parse_postfix()
                left = Call(Var(cmd), Arr([left, right]))
            else:
                return left

    def parse_primary(self):
        t = self.next()
        if t.value == "if":
            # inline if-expression: if (C) then {..} else {..}
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            self.expect("then")
            then = self.parse_block()
            els = []
            if self.peekv() == "else":
                self.next()
                els = self.parse_block()
            return If(cond, then, els)
        if t.value == "(":
            # grouping parens: (expr)
            expr = self.parse_expr()
            self.expect(")")
            return expr
        if t.kind == "num":
            return Num(t.value)
        if t.kind == "str":
            return Str(t.value)
        if t.value == "[":
            items = []
            while self.peekv() != "]":
                items.append(self.parse_expr())
                if self.peekv() == ",":
                    self.next()
            self.expect("]")
            return Arr(items)
        if t.value == "{":
            # lambda: { params ["_x"]; ... } or bare { ... }
            save = self.i
            params = []
            if self.peekv() == "params":
                self.next()
                # Simple lambda form: params ["_x", "_y"] - a bare array
                # of quoted names, no defaults/type tags.
                params = self.parse_lambda_params()
                self.optional_semi()
            else:
                self.i = save
            body = []
            while self.peekv() != "}":
                body.append(self.parse_stmt())
            self.expect("}")
            return Lambda(params, body, {})
        if t.kind == "id":
            if t.value == "FUNC":
                # FUNC(getMaterialThermal) - resolved by the harness
                self.expect("(")
                fn_name = self.next()
                self.expect(")")
                return Var(f"__FUNC__{fn_name.value}")
            if t.value == "EFUNC":
                self.expect("(")
                mod = self.next()
                self.expect(",")
                fn_name = self.next()
                self.expect(")")
                return Var(f"__EFUNC__{mod.value}_{fn_name.value}")
            return Var(t.value)
        raise SyntaxError(f"unexpected token {t.value} @ {t.pos}")


# ─── Runtime ────────────────────────────────────────────────────────────────
class SqfRuntime:
    def __init__(self, globals_: dict[str, Any] | None = None):
        self.globals = globals_ or {}
        self.scopes: list[dict[str, Any]] = [{}]

    def get(self, name: str) -> Any:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name.startswith("__FUNC__") or name.startswith("__EFUNC__"):
            return self.globals.get(name)
        if name in self.globals:
            return self.globals[name]
        raise NameError(f"undefined {name}")

    def set(self, name: str, value: Any):
        self.scopes[-1][name] = value

    def push(self):
        self.scopes.append({})

    def pop(self):
        self.scopes.pop()

    def eval(self, node: Any) -> Any:
        if isinstance(node, Num):
            return node.v
        if isinstance(node, Str):
            return node.v
        if isinstance(node, Var):
            return self.get(node.name)
        if isinstance(node, Arr):
            return [self.eval(i) for i in node.items]
        if isinstance(node, Lambda):
            node.closure = dict(self.scopes[-1])
            return node
        if isinstance(node, If):
            # if-expression: returns the block's last value
            if self.eval(node.cond):
                self.push()
                r = self.run(node.then)
                self.pop()
                return r
            elif node.els:
                self.push()
                r = self.run(node.els)
                self.pop()
                return r
            return None
        if isinstance(node, Bin):
            if node.op == "neg":
                return -self.eval(node.right)
            if node.op == "not":
                return not self.eval(node.right)
            l = self.eval(node.left)
            r = self.eval(node.right)
            if node.op == "+":
                return l + r
            if node.op == "-":
                return l - r
            if node.op == "*":
                return l * r
            if node.op == "/":
                return l / r
            if node.op == "^":
                return l**r
            if node.op == "<":
                return l < r
            if node.op == ">":
                return l > r
            if node.op == "<=":
                return l <= r
            if node.op == ">=":
                return l >= r
            if node.op == "==":
                return l == r
            if node.op == "!=":
                return l != r
            if node.op == "&&":
                return bool(l) and bool(r)
            if node.op == "||":
                return bool(l) or bool(r)
            raise ValueError(f"unknown op {node.op}")
        if isinstance(node, MaxMin):
            l = self.eval(node.left)
            r = self.eval(node.right)
            return max(l, r) if node.op == "max" else min(l, r)
        if isinstance(node, Exp):
            return math.exp(self.eval(node.arg))
        if isinstance(node, Select):
            arr = self.eval(node.arr)
            idx = self.eval(node.idx)
            if isinstance(idx, bool):
                return arr[1] if idx else arr[0]
            return arr[int(idx)]
        if isinstance(node, Call):
            fn = self.eval(node.fn)
            args = self.eval(node.args)
            if not isinstance(args, list):
                args = [args]
            if isinstance(fn, Lambda):
                self.push()
                for i, p in enumerate(fn.params):
                    self.set(p, args[i] if i < len(args) else None)
                # closure vars visible (lambda declared in the solver scope)
                for k, v in fn.closure.items():
                    if k not in self.scopes[-1]:
                        self.scopes[-1].setdefault(k, v)
                result = self.run(fn.body)
                self.pop()
                return result
            if callable(fn):
                return fn(*args)
            raise ValueError(f"cannot call {fn}")
        raise ValueError(f"cannot eval {node}")

    def run(self, stmts: list) -> Any:
        result = None
        try:
            for s in stmts:
                result = self.exec_stmt(s)
        except ExitSignal as e:
            result = e.args[0] if e.args else None
        return result

    def exec_stmt(self, s: Any) -> Any:
        if isinstance(s, ExitWith):
            # if (cond) exitWith {value} - a top-level exit
            if self.eval(s.cond):
                raise ExitSignal(self.run(s.value))
            return None
        if isinstance(s, Assign):
            self.set(s.name, self.eval(s.expr))
            return None
        if isinstance(s, ExprStmt):
            return self.eval(s.expr)
        if isinstance(s, If):
            # SQF if/else blocks share the ENCLOSING scope - a variable
            # assigned inside a block is visible after it.  Do NOT push
            # a scope here (pushing discards the assignment on pop).
            if self.eval(s.cond):
                self.run(s.then)
            elif s.els:
                self.run(s.els)
            return None
        if isinstance(s, For):
            lo = int(self.eval(s.lo))
            hi = int(self.eval(s.hi))
            for i in range(lo, hi + 1):
                self.set(s.var, float(i))
                self.run(s.body)
            return None
        if isinstance(s, Params):
            # The harness pre-binds params from the call args.  Re-binding
            # here would overwrite the float args with the AST defaults
            # (a Num node), corrupting every subsequent comparison.
            # Only bind params that are not already set.
            for name, default in s.specs:
                if name not in self.scopes[-1]:
                    self.set(name, default)
            return None
        raise ValueError(f"cannot exec {s}")


# ─── Harness ────────────────────────────────────────────────────────────────
def load_sqf(path: str | Path) -> list:
    text = Path(path).read_text(encoding="utf-8")
    # Strip /* */ block comments and the #include / preprocessor header
    # lines before tokenising.  The solver files open with a long
    # /* ... */ docstring and an #include line.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"^#include.*$", "", text, flags=re.MULTILINE)
    return SqfParser(tokenize(text)).parse_program()


def run_sqf(
    path: str | Path,
    args: list[Any],
    globals_: dict[str, Any] | None = None,
) -> Any:
    """Run an SQF function file with the given args."""
    rt = SqfRuntime(globals_)
    stmts = load_sqf(path)
    # bind params from the first Params statement
    for s in stmts:
        if isinstance(s, Params):
            for i, (name, default) in enumerate(s.specs):
                rt.set(name, args[i] if i < len(args) else default)
            break
    return rt.run(stmts)
