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
               toLower s  (string lower-case; the thermal paint
                          resolver's case-insensitive slot pass)
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
import struct
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
  | >>                                  # config-path operator (before single >)
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
        elif s in ("&&", "||", ">>"):
            toks.append(Tok("punct", s, m.start()))
        elif s in "[]{}();,+-*/^<>=!&|":
            toks.append(Tok("punct", s, m.start()))
        else:
            # SQF local variable names are case-insensitive (_P and _p are
            # one variable), so a local is normalised to lower case here; a
            # harness that kept the case would pass code the engine breaks.
            toks.append(
                Tok("id", s.lower() if re.match(r"_[A-Za-z]", s) else s, m.start())
            )
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
class UnaryCmd:
    op: str  # "count" | "abs"
    arg: Any


@dataclass
class Assign:
    name: str
    expr: Any
    private: bool = False


BINARY_COMMANDS = {
    "getVariable",
    # NS setVariable [k, v] - the write twin of getVariable.  The consistency
    # monitor publishes its state this way; without it the command parses as a
    # bare identifier and the write is silently dropped.
    "setVariable",
    "isEqualType",
    "isEqualTypeAny",
    "isEqualTo",
    "isNotEqualTo",
    # hashmap getOrDefault [key, default] - the drag kernel reads the drag
    # table by model name.  Resolved against the HashMap the caller binds.
    "getOrDefault",
    # hashmap get key: the generated data tables are read this way.
    "get",
    # array set [index, value]: in-place element write.
    "set",
    "pushBack",
    "deleteAt",
    "sort",
    # Vector and modulo commands used by fnc_outlineTopo (binary form).
    "vectorDiff",
    "vectorAdd",
    "vectorMultiply",
    "vectorDotProduct",
    "vectorDistance",
    "vectorDistanceSqr",
    "vectorCrossProduct",
    "mod",
    # number toFixed decimals - binary form, returns a STRING (HUD range).
    "toFixed",
    # y atan2 x returns DEGREES; pos1 distance pos2 returns metres.
    "atan2",
    "distance",
    "distance2D",
    # Object class test used by the wildlife neighbourhood sampler.  In the
    # harness the objects are strings, so this is an equality test.
    "isKindOf",
    # array param [index, default]: the element, or the default when the
    # index is out of range or the element is nil.
    "param",
    # haystack find needle: a string's substring index or an array's element
    # index, -1 when absent (the surface-name classifiers).
    "find",
    # Object state writes used by the aircraft fuel kernel.  The harness
    # resolves each through globals_, so a test binds a recorder.
    "setFuel",
    "setCenterOfMass",
    # Damage reads and writes used by fnc_updateDamageSystem.
    "getHitPointDamage",
    "setHitPointDamage",
}


def _sqf_isKindOf(obj: Any, cls: Any) -> bool:
    return obj == cls


def _sqf_isEqualTo(a: Any, b: Any) -> bool:
    return a == b


def _sqf_isNotEqualTo(a: Any, b: Any) -> bool:
    return a != b


def _sqf_getVariable(container: Any, spec: Any) -> Any:
    """SQF `namespace getVariable [key, default]`.  A namespace is a dict in
    the harness, so this is a dict lookup with a default."""
    key = spec[0]
    default = spec[1] if len(spec) > 1 else None
    if isinstance(container, dict):
        return container.get(key, default)
    return default


def _sqf_setVariable(container: Any, spec: Any) -> None:
    """SQF `namespace setVariable [key, value]`.  A non-dict namespace (an
    engine object the test did not supply) drops the write."""
    if isinstance(container, dict):
        container[spec[0]] = spec[1]
    return None


def _sqf_getOrDefault(container: Any, spec: Any) -> Any:
    """SQF hashmap getOrDefault [key, default].  The harness holds the table
    as a plain dict, so this is a dict lookup with a default."""
    key = spec[0]
    default = spec[1] if len(spec) > 1 else None
    if isinstance(container, dict):
        return container.get(key, default)
    return default


def _sqf_format(spec: Any) -> str:
    """SQF format ["G%1", _code].  Replace %1..%9 with the arguments; a %%
    is a literal percent.  The operand is the [fmt, args..] array."""
    fmt = str(spec[0])
    args = list(spec[1:])
    out: list[str] = []
    i = 0
    while i < len(fmt):
        ch = fmt[i]
        if ch == "%" and i + 1 < len(fmt):
            nxt = fmt[i + 1]
            if nxt.isdigit():
                index = int(nxt) - 1
                out.append(_sqf_str(args[index]) if 0 <= index < len(args) else "")
                i += 2
                continue
            if nxt == "%":
                out.append("%")
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _sqf_type_tag(value: Any) -> str:
    """SQF type category, so int and float both read as NUMBER."""
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, (int, float)):
        return "NUMBER"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, list):
        return "ARRAY"
    if value is None:
        return "NIL"
    # A Code value is a block.  The harness represents one as a Lambda or, for
    # an injected engine function, as a Python callable.
    if isinstance(value, Lambda) or callable(value):
        return "CODE"
    return "OBJECT"


def _sqf_isEqualType(a: Any, b: Any) -> bool:
    return _sqf_type_tag(a) == _sqf_type_tag(b)


def _sqf_isEqualTypeAny(value: Any, types: Any) -> bool:
    """SQF `value isEqualTypeAny array`: true when the type of `value`
    matches the type of any element of `types`."""
    tag = _sqf_type_tag(value)
    return any(_sqf_type_tag(t) == tag for t in types)


def _sqf_parse_simple_array(text: Any) -> list:
    """SQF `parseSimpleArray`: parse an SQF literal and return its array.

    The literal is parsed by the same tokeniser and parser, so a string, a
    number or a bare identifier evaluates without executing code.  Anything
    that is not a top-level array, or that raises while parsing or evaluating,
    returns an empty array, matching the engine on malformed input.
    """
    if not isinstance(text, str):
        return []
    try:
        stmts = SqfParser(tokenize(text)).parse_program()
        value = SqfRuntime({}).run(stmts)
    except Exception:
        return []
    return value if isinstance(value, list) else []


# Unary commands applied to a following expression.  Without these the
# parser reads the name as a variable and the operand as a new statement,
# which is how `(count _v) == 0` raised "expected ), got _v".
UNARY_COMMANDS = {
    "count",
    # createHashMapFromArray [[key, value], ...]: the generated tables.
    "createHashMapFromArray",
    "abs",
    "toLower",
    # toLowerANSI X - the Pandolf terrain kernel lower-cases the surface name.
    "toLowerANSI",
    "finite",
    "round",
    "tan",
    "ceil",
    "cos",
    "sin",
    "sqrt",
    # log X (base 10) and ln X (natural) - the eye-adaptation kernels
    # (mesopic weight, pupil diameter) need both.
    "log",
    "ln",
    # linearConversion [min, max, x, a, b, clamp] - the aperture map needs
    # it; the operand is the six-element array.
    "linearConversion",
    # floor X and ceil X - the sidereal-time kernel (fnc_siderealTime) needs
    # floor for the Julian-day-at-0h-UT reduction.
    "floor",
    # Inverse trig returns DEGREES in SQF (asin/acos/atan), matching the
    # degree-taking sin/cos/tan above.
    "asin",
    "acos",
    "atan",
    "vectorMagnitude",
    "vectorNormalized",
    # str X - SQF number/other to display string (HUD heading/grid).
    "str",
    # Engine terrain and object queries used by the wildlife neighbourhood
    # sampler.  The runtime supplies them through `globals_`; without a stub
    # the call is an error, so a test must bind them.
    "surfaceType",
    "surfaceIsWater",
    "getTerrainHeightASL",
    "nearestTerrainObjects",
    # Objects within a radius and a unit's own vehicle and ASL position: the
    # compass kernel's local ferrous sources.
    "nearestObjects",
    "vehicle",
    "getPosASL",
    # HashMap value list used by the wildlife vegetation-score helper.
    "values",
    # isClass X - config class-existence test used by fnc_wildlifeTick.
    "isClass",
    # Config font glyph check (fnc_fontFamilyUsable): getArray reads a
    # CfgFontFamilies fonts[] list and fileExists tests the glyph .fxy.  Both
    # are engine commands the caller binds through globals_.
    "getArray",
    "fileExists",
    # parseSimpleArray "text" - the literal parser the dev dispatcher uses to
    # read an extension request.  A non-array or unparsable text returns [].
    "parseSimpleArray",
    # typeName X - the SQF type category.  compile X - the console `eval` op
    # compiles agent input; the harness returns the text (a test does not run
    # eval).
    "typeName",
    "compile",
    # isNil "_name" - the dev dispatcher reports a nothing-returning operation
    # as the text "nil" so the reply always marshals across the extension.
    "isNil",
    # toUpper X - the drag kernel upper-cases the drag-model name.
    "toUpper",
    # format [fmt, args..] - the drag kernel builds the G-series name with
    # format ["G%1", _code].  The operand is the [fmt, args..] array.
    "format",
    # Object queries used by the aircraft fuel kernel (fnc_updateFuelSystem).
    # The harness resolves each through globals_, so a test must bind them.
    "local",
    "isNull",
    "alive",
    "typeOf",
    "fuel",
    # Damage queries used by fnc_updateDamageSystem.
    "getAllHitPointsDamage",
    "isDamageAllowed",
    # Slot queries and carried-item queries used by the clothing library:
    # `uniform _unit`, `items _unit`, `weaponCargo (unitBackpack _unit)`.
    # Each resolves through globals_, so a test binds the unit surface.
    "uniform",
    "vest",
    "headgear",
    "goggles",
    "backpack",
    "primaryWeapon",
    "secondaryWeapon",
    "handgunWeapon",
    "primaryWeaponItems",
    "secondaryWeaponItems",
    "handgunItems",
    "items",
    "assignedItems",
    "hmd",
    "binocular",
    "weaponCargo",
    "unitBackpack",
    # Config reads used by the clothing classifiers and their override walk.
    "getText",
    "getNumber",
    "configName",
    "inheritsFrom",
    # Array copy (`+assignedItems _unit`).
    "copy",
}


# Mutating array builtins.  The interpreter holds Python lists by reference,
# so append/pop on the list mutate the variable's value, as SQF does.
def _sqf_set(arr: Any, spec: Any) -> None:
    """arr set [index, value]: writes in place, padding with nil (SQF grows
    an array written past its end); a hashmap set [key, value] stores."""
    key, value = spec[0], spec[1]
    if isinstance(arr, dict):
        arr[key] = value
        return None
    i = int(key)
    while len(arr) <= i:
        arr.append(None)
    arr[i] = value
    return None


def _sqf_pushBack(arr: list, value: Any) -> None:
    arr.append(value)
    return None


def _sqf_deleteAt(arr: list, index: Any) -> Any:
    return arr.pop(int(index))


def _sqf_sort(arr: list, ascending: Any = True) -> None:
    arr.sort(reverse=not bool(ascending))
    return None


# Vector and modulo builtins.  These are command-style in SQF
# (_a vectorDiff _b) and are reached through the BINARY_COMMANDS path,
# which resolves the command name to a callable in BUILTINS.
def _sqf_str(value: Any) -> str:
    """SQF str: whole floats print without a decimal point, others as-is."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    return str(value)


def _sqf_toFixed(value: Any, decimals: Any) -> str:
    """SQF toFixed: round half away from zero, pad to the requested places."""
    d = int(decimals)
    factor = 10**d
    scaled = value * factor
    if scaled >= 0:
        rounded = math.floor(scaled + 0.5)
    else:
        rounded = math.ceil(scaled - 0.5)
    return f"{rounded / factor:.{d}f}"


def _sqf_vectorDiff(a: list, b: list) -> list:
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _sqf_vectorAdd(a: list, b: list) -> list:
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _sqf_vectorMultiply(v: list, s: float) -> list:
    return [v[0] * s, v[1] * s, v[2] * s]


def _sqf_vectorDotProduct(a: list, b: list) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sqf_vectorDistance(a: list, b: list) -> float:
    return math.dist(a, b)


def _sqf_vectorDistanceSqr(a: list, b: list) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _sqf_vectorCrossProduct(a: list, b: list) -> list:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


BUILTINS: dict[str, Any] = {
    "pushBack": _sqf_pushBack,
    "deleteAt": _sqf_deleteAt,
    "sort": _sqf_sort,
    "isEqualTo": _sqf_isEqualTo,
    "isEqualType": _sqf_isEqualType,
    "isEqualTypeAny": _sqf_isEqualTypeAny,
    "isNotEqualTo": _sqf_isNotEqualTo,
    "getOrDefault": _sqf_getOrDefault,
    "getVariable": _sqf_getVariable,
    "setVariable": _sqf_setVariable,
    "get": lambda m, k: m.get(k) if isinstance(m, dict) else None,
    "set": _sqf_set,
    "createHashMapFromArray": lambda pairs: {p[0]: p[1] for p in pairs},
    "isKindOf": _sqf_isKindOf,
    "param": lambda a, spec: (
        a[int(spec[0])]
        if isinstance(a, list)
        and 0 <= int(spec[0]) < len(a)
        and a[int(spec[0])] is not None
        else (spec[1] if len(spec) > 1 else None)
    ),
    "find": lambda h, n: (
        float(h.find(n))
        if isinstance(h, str)
        else (float(h.index(n)) if n in h else -1.0)
    ),
    "vectorDiff": _sqf_vectorDiff,
    "vectorAdd": _sqf_vectorAdd,
    "vectorMultiply": _sqf_vectorMultiply,
    "vectorDotProduct": _sqf_vectorDotProduct,
    "vectorDistance": _sqf_vectorDistance,
    "vectorDistanceSqr": _sqf_vectorDistanceSqr,
    "vectorCrossProduct": _sqf_vectorCrossProduct,
    "mod": lambda a, b: math.fmod(a, b),
    "floor": math.floor,
    "toFixed": _sqf_toFixed,
    "atan2": lambda a, b: math.degrees(math.atan2(a, b)),
    "distance": lambda a, b: math.dist(a, b),
    "distance2D": lambda a, b: math.dist(a[:2], b[:2]),
    "pi": math.pi,
    "true": True,
    "false": False,
    "nil": None,
}


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


@dataclass
class Each:
    """forEach (keep=True, returns None) / apply (keep=False, returns ARRAY)."""

    code: Any
    arr: Any
    keep: bool


@dataclass
class While:
    cond: list
    body: list


@dataclass
class Switch:
    """SQF `switch (v) do { case X: {..}; default {..}; }`.

    cases is a list of (value_expr | None, block) in source order; None
    marks the default.  The engine evaluates the case expressions in
    order and runs the first whose value equals the switch value.
    """

    expr: Any
    cases: list


@dataclass
class FindIf:
    """findIf: return the index of the first element whose block is truthy."""

    arr: Any
    code: Any


@dataclass
class Continue:
    """SQF `continue` - skip to the next loop iteration."""


@dataclass
class Destructure:
    """SQF `array params ["_a", "_b"]` - the array-destructuring form.

    Distinct from the leading `params [..]` statement (the function's own
    argument declaration): this form binds names from an arbitrary array.
    The harness added it for the RPT regression test, which executes the
    real cache-read block ending in `_plan params ["_segments", "_labels"]`."""

    arr: Any
    names: list


class ContinueSignal(Exception):
    """Raised by `continue` and caught by the enclosing for/while loop."""


# ─── Parser (recursive descent) ─────────────────────────────────────────────
class SqfParser:
    def __init__(self, toks: list[Tok]):
        self.toks = toks
        self.i = 0
        # Depth of `select`-index parsing.  A chained `a select b select c` is
        # left-associative: it means `(a select b) select c`.  While parsing
        # the index of a select, a following `select` belongs to the outer
        # chain, not to the index, so parse_postfix stops there.
        self.stop_select = 0

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
            return Assign(name.value, expr, True)
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
                loop_var = var.value.lower()
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
        if t.value == "while":
            self.next()
            cond = self.parse_block()
            self.expect("do")
            body = self.parse_block()
            self.optional_semi()
            return While(cond, body)
        if t.value == "continue":
            self.next()
            self.optional_semi()
            return Continue()
        if t.value == "{":
            # bare lambda in expression position handled by parse_expr;
            # here treat as a statement lambda (unlikely in solver).  Consume
            # the statement terminator like the generic path below, or the
            # next parse_stmt reads the stray semicolon as a primary.
            expr = self.parse_expr()
            self.optional_semi()
            return ExprStmt(expr)
        expr = self.parse_expr()
        self.optional_semi()
        return ExprStmt(expr)

    def optional_semi(self):
        if self.peekv() == ";":
            self.next()

    def parse_param_spec(self) -> tuple:
        """One `[name, default, type, ...]` spec: the name and the default.

        The type tag and the dimension count are validated by the engine,
        not read by the harness, so they are skipped.
        """
        self.expect("[")
        name = self.next()
        # SQF params names are QUOTED strings: ["_obj", default, type]
        if name.kind == "str":
            name_value = name.value.lower()
        elif name.kind == "id" and name.value.startswith("_"):
            name_value = name.value
        else:
            raise SyntaxError(f"param name must be a string, got {name}")
        default = None
        if self.peekv() == ",":
            self.next()
            default = self.parse_expr()
        # Optional trailing components: [type] and/or a dimension count,
        # e.g. ["_eye", [0,0,0], [[]], 3] or ["_hSens", 0, [0]].
        while self.peekv() == ",":
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
            else:
                self.parse_expr()
        self.expect("]")
        return (name_value, default)

    def parse_params(self) -> list:
        self.expect("[")
        specs = []
        while self.peekv() != "]":
            specs.append(self.parse_param_spec())
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
            names.append(t.value.lower())
            if self.peekv() == ",":
                self.next()
        self.expect("]")
        return names

    def parse_lambda_specs(self) -> list:
        """Lambda params in either form: `["_x"]` or `[["_x", 0, [0]]]`.

        A block does carry defaulted params - the inventory walk's
        resolver declares `[["_item"], ["_category", [], [[]]]]` - so the
        harness must bind the default when the call omits the argument.
        """
        self.expect("[")
        specs = []
        while self.peekv() != "]":
            if self.peekv() == "[":
                specs.append(self.parse_param_spec())
            else:
                t = self.next()
                if t.kind != "str":
                    raise SyntaxError(f"lambda param must be a string, got {t.value}")
                specs.append((t.value.lower(), None))
            if self.peekv() == ",":
                self.next()
        self.expect("]")
        return specs

    def parse_switch(self):
        """switch (v) do { case X: {..}; default {..}; }.

        The `:` after a case value is not tokenised (the tokeniser has no
        colon), so the block follows the value expression directly.
        """
        self.expect("(")
        expr = self.parse_expr()
        self.expect(")")
        self.expect("do")
        self.expect("{")
        cases = []
        while self.peekv() != "}":
            t = self.next()
            if t.value == "case":
                cases.append((self.parse_expr(), self.parse_block()))
            elif t.value == "default":
                cases.append((None, self.parse_block()))
            else:
                raise SyntaxError(f"expected case or default, got {t.value}")
            self.optional_semi()
        self.expect("}")
        return Switch(expr, cases)

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
            # membership: `_x in _array` (the inventory walk's skip lists).
            "in",
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
        while self.peekv() in ("*", "/", ">>"):
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
        if t is not None and t.value == "+":
            # Unary plus: SQF `+array` copies the array.  The ecology tick
            # refills its pending queue with `+_agents` so the queue never
            # aliases the live registry, and without this rule the tick
            # cannot be executed by the harness at all.
            self.next()
            return UnaryCmd("copy", self.parse_unary())
        if t is not None and t.value == "-":
            self.next()
            return Bin("neg", Num(0.0), self.parse_unary())
        if t is not None and t.value == "!":
            self.next()
            return Bin("not", Num(0.0), self.parse_unary())
        if t is not None and t.value == "+":
            # prefix + copies an array: `+assignedItems _unit`.
            self.next()
            return UnaryCmd("copy", self.parse_unary())
        if t is not None and t.value == "switch":
            self.next()
            return self.parse_switch()
        # Prefix `call`: `call FUNC(x)` runs the function value with no args.
        # The postfix `args call FUNC(x)` form is handled in parse_postfix.
        if t is not None and t.value == "call" and self._is_cmd_use(t.value):
            self.next()
            return Call(self.parse_unary(), Arr([]))
        # command-like prefix: max/min/exp applied to a following expression
        if (
            t is not None
            and t.kind == "id"
            and t.value in ("exp",)
            and self._is_cmd_use(t.value)
        ):
            self.next()
            return Exp(self.parse_unary())
        if (
            t is not None
            and t.kind == "id"
            and t.value in UNARY_COMMANDS
            and self._is_cmd_use(t.value)
        ):
            self.next()
            return UnaryCmd(t.value, self.parse_unary())
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
                if self.stop_select > 0:
                    return left
                self.next()
                self.stop_select += 1
                try:
                    idx = self.parse_unary()
                finally:
                    self.stop_select -= 1
                left = Select(left, idx)
            elif t.value == "call":
                self.next()
                fn = self.parse_unary()
                left = Call(fn, left)
            elif t.value == "max" or t.value == "min":
                self.next()
                right = self.parse_unary()
                left = MaxMin(t.value, left, right)
            elif t.value == "forEach":
                self.next()
                right = self.parse_unary()
                if isinstance(left, Lambda):
                    left = Each(code=left, arr=right, keep=True)
                else:
                    left = Each(code=right, arr=left, keep=True)
            elif t.value == "apply":
                self.next()
                right = self.parse_unary()
                if isinstance(left, Lambda):
                    left = Each(code=left, arr=right, keep=False)
                else:
                    left = Each(code=right, arr=left, keep=False)
            elif t.value == "findIf":
                self.next()
                right = self.parse_unary()
                left = FindIf(arr=left, code=right)
            elif t.value in BINARY_COMMANDS:
                # binary command form: NS getVariable [k, d] - the
                # left operand is the namespace, the command's arg is
                # the right expression.  Resolved as Call(cmd,
                # [left, argArray]) (issue #162).
                cmd = self.next().value
                right = self.parse_postfix()
                left = Call(Var(cmd), Arr([left, right]))
            elif t.value == "params":
                # array-destructuring form: _plan params ["_a", "_b"].  The
                # leading `params [..]` statement (function args) is handled
                # in parse_stmt; this form follows an expression.
                self.next()
                left = Destructure(left, self.parse_lambda_params())
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
            # grouping parens: (expr).  Clear the select-stop guard: a select
            # inside the parens is a nested expression, not the outer chain.
            saved = self.stop_select
            self.stop_select = 0
            try:
                expr = self.parse_expr()
            finally:
                self.stop_select = saved
            self.expect(")")
            return expr
        if t.kind == "num":
            return Num(t.value)
        if t.kind == "str":
            return Str(t.value)
        if t.value == "[":
            items = []
            saved = self.stop_select
            self.stop_select = 0
            try:
                while self.peekv() != "]":
                    items.append(self.parse_expr())
                    if self.peekv() == ",":
                        self.next()
            finally:
                self.stop_select = saved
            self.expect("]")
            return Arr(items)
        if t.value == "{":
            # lambda: { params ["_x"]; ... } or bare { ... }
            saved_stop = self.stop_select
            self.stop_select = 0
            save = self.i
            params = []
            if self.peekv() == "params":
                self.next()
                # Either form: params ["_x", "_y"] or the full spec form
                # with defaults, [["_x", 0, [0]]].
                params = self.parse_lambda_specs()
                self.optional_semi()
            else:
                self.i = save
            body = []
            while self.peekv() != "}":
                body.append(self.parse_stmt())
            self.expect("}")
            self.stop_select = saved_stop
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
            if t.value in ("QGVAR", "QEGVAR"):
                # QGVAR(name) is a namespaced variable name.  The harness
                # cannot resolve the addon prefix, so it returns a stable
                # placeholder string.  A caller that reads and writes the same
                # QGVAR in one run still agrees, because the placeholder is
                # deterministic.
                self.expect("(")
                if t.value == "QGVAR":
                    name = self.next()
                    self.expect(")")
                    return Str(f"__QGVAR__{name.value}")
                mod = self.next()
                self.expect(",")
                name = self.next()
                self.expect(")")
                return Str(f"__QEGVAR__{mod.value}_{name.value}")
            return Var(t.value)
        raise SyntaxError(f"unexpected token {t.value} @ {t.pos}")


# ─── Runtime ────────────────────────────────────────────────────────────────
_CONSTANTS_PATH = (
    Path(__file__).resolve().parents[2] / "addons" / "lib" / "constants.hpp"
)
_CONSTANTS_CACHE: dict[str, float] | None = None


def constants_defines() -> dict[str, float]:
    """The shared physical constants, parsed from addons/lib/constants.hpp.

    The mod's preprocessor expands each #define name before the engine sees the
    SQF.  The harness does not preprocess, so it injects the same names as
    globals; a kernel that reads KELVIN_OFFSET would otherwise NameError.
    """
    global _CONSTANTS_CACHE
    if _CONSTANTS_CACHE is None:
        text = _CONSTANTS_PATH.read_text(encoding="utf-8")
        _CONSTANTS_CACHE = {
            m.group(1): float(m.group(2))
            for m in re.finditer(
                r"^#define\s+([A-Za-z_]\w*)\s+([0-9]+(?:\.[0-9]+)?)", text, re.M
            )
        }
    return _CONSTANTS_CACHE


def _f32(value: Any) -> Any:
    """Round a number to IEEE single precision, the engine's number type."""
    if isinstance(value, float):
        return (
            struct.unpack("f", struct.pack("f", value))[0]
            if math.isfinite(value)
            else value
        )
    if isinstance(value, list):
        return [_f32(v) for v in value]
    return value


class SqfRuntime:
    # When True every evaluated number is rounded to float32, as Arma's
    # engine stores it.  A kernel that relies on double precision (a raw
    # Julian Day, a large product of an angle rate) fails under it.
    float32 = False

    def __init__(self, globals_: dict[str, Any] | None = None):
        # true/false/nil and the mutating array builtins are engine words, not
        # variables; inject them before any call-supplied global so a caller
        # can still override.  The shared constants follow, then the caller's
        # globals win last.
        self.globals: dict[str, Any] = dict(BUILTINS)
        self.globals.update(constants_defines())
        if globals_:
            # Injected locals follow the same case-insensitive rule.
            self.globals.update(
                {
                    (k.lower() if re.match(r"_[A-Za-z]", k) else k): v
                    for k, v in globals_.items()
                }
            )
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

    def _run_block(self, lam: Lambda) -> Any:
        """Run a `{ ... }` block in a fresh scope with its closure bound.

        SQF `a && { b }` / `a || { b }` evaluate the block lazily; the parser
        represents that block as a Lambda, so the boolean operators call it.
        """
        self.push()
        for k, v in lam.closure.items():
            if k not in self.scopes[-1]:
                self.scopes[-1].setdefault(k, v)
        r = self.run(lam.body)
        self.pop()
        return r

    def eval(self, node: Any) -> Any:
        value = self._eval(node)
        if self.float32 and isinstance(value, float):
            return _f32(value)
        return value

    def _eval(self, node: Any) -> Any:
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
        if isinstance(node, Destructure):
            # array params [names]: bind each name from the array in the
            # CURRENT scope.  A short array binds None, matching the engine's
            # "0 elements provided, N expected" guard boundary.
            arr = self.eval(node.arr)
            if not isinstance(arr, list):
                arr = []
            for i, name in enumerate(node.names):
                self.set(name, arr[i] if i < len(arr) else None)
            return None
        if isinstance(node, Bin):
            if node.op == "neg":
                return -self.eval(node.right)
            if node.op == "not":
                return not self.eval(node.right)
            # A `{ ... }` block operand is SQF code and is run, not truthy by
            # itself.  A `{ ... }` on the right of && or || is the engine's
            # short-circuit idiom (`count _c == 0 && {_c select 0 == x}`), so
            # it must NOT run when the left operand already settles the
            # result; only the plain-value operands keep the harness's eager
            # rule, so guard-boundary tests keep seeing both.
            left = self.eval(node.left)
            if isinstance(left, Lambda):
                left = self._run_block(left)
            if isinstance(node.right, Lambda) and (
                (node.op == "&&" and not left) or (node.op == "||" and left)
            ):
                return bool(left)
            right = self.eval(node.right)
            if isinstance(right, Lambda):
                right = self._run_block(right)
            if node.op == "+":
                return left + right
            if node.op == "-":
                return left - right
            if node.op == "*":
                return left * right
            if node.op == "/":
                return left / right
            if node.op == "^":
                return left**right
            if node.op == "<":
                return left < right
            if node.op == ">":
                return left > right
            if node.op == "<=":
                return left <= right
            if node.op == ">=":
                return left >= right
            if node.op == "==":
                return left == right
            if node.op == "!=":
                return left != right
            if node.op == "in":
                # SQF membership: `_x in _array`.  A string in a string is
                # a substring test in the engine; the kernels use arrays.
                return left in right
            if node.op == "&&":
                return bool(left) and bool(right)
            if node.op == "||":
                return bool(left) or bool(right)
            if node.op == ">>":
                # config path operator: configFile >> "CfgX" >> "Y".
                # The harness has no config tree, so the path joins into a
                # stable string; isClass/config tests stub the lookup.
                return f"{left}/{right}"
            raise ValueError(f"unknown op {node.op}")
        if isinstance(node, MaxMin):
            left = self.eval(node.left)
            right = self.eval(node.right)
            return max(left, right) if node.op == "max" else min(left, right)
        if isinstance(node, Exp):
            return math.exp(self.eval(node.arg))
        if isinstance(node, UnaryCmd):
            if node.op == "isNil":
                # SQF isNil takes a variable NAME (a string) or a value. A
                # string operand names the variable to test; a missing variable
                # and a nil value both read as nil.
                arg = node.arg
                if isinstance(arg, Str):
                    try:
                        return self.get(arg.v) is None
                    except NameError:
                        return True
                return self.eval(arg) is None
            value = self.eval(node.arg)
            if node.op == "copy":
                # Unary plus: a shallow copy of an array, the operand for
                # anything else (SQF `+x` on a number is the number).
                return list(value) if isinstance(value, list) else value
            if node.op == "count":
                return len(value)
            if node.op == "abs":
                return abs(value)
            if node.op == "toLower":
                return str(value).lower()
            if node.op == "toLowerANSI":
                return str(value).lower()
            if node.op == "toUpper":
                return str(value).upper()
            if node.op == "format":
                return _sqf_format(value)
            if node.op == "finite":
                return math.isfinite(value)
            if node.op == "tan":
                # SQF tan takes degrees; Python math.tan takes radians.
                return math.tan(math.radians(value))
            if node.op == "round":
                # SQF round is half away from zero; Python round is banker's.
                if value >= 0:
                    return float(math.floor(value + 0.5))
                return float(math.ceil(value - 0.5))
            if node.op == "str":
                return _sqf_str(value)
            if node.op == "ceil":
                return float(math.ceil(value))
            if node.op == "cos":
                # SQF trig takes degrees.
                return math.cos(math.radians(value))
            if node.op == "sin":
                return math.sin(math.radians(value))
            if node.op == "sqrt":
                return math.sqrt(value)
            if node.op == "log":
                return math.log10(value)
            if node.op == "ln":
                return math.log(value)
            if node.op == "linearConversion":
                # value is [min, max, x, a, b, clamp].
                lo, hi, x, a, b = value[0], value[1], value[2], value[3], value[4]
                clamp = value[5] if len(value) > 5 else True
                if lo == hi:
                    return a
                t = (x - lo) / (hi - lo)
                if clamp:
                    t = max(0.0, min(1.0, t))
                return a + t * (b - a)
            if node.op == "floor":
                return float(math.floor(value))
            if node.op == "asin":
                return math.degrees(math.asin(value))
            if node.op == "acos":
                return math.degrees(math.acos(value))
            if node.op == "atan":
                return math.degrees(math.atan(value))
            if node.op == "vectorMagnitude":
                return math.sqrt(sum(float(c) ** 2 for c in value[:3]))
            if node.op == "vectorNormalized":
                mag = math.sqrt(value[0] ** 2 + value[1] ** 2 + value[2] ** 2)
                if mag == 0:
                    return [0.0, 0.0, 0.0]
                return [value[0] / mag, value[1] / mag, value[2] / mag]
            if node.op == "parseSimpleArray":
                return _sqf_parse_simple_array(value)
            if node.op == "typeName":
                return _sqf_type_tag(value)
            if node.op == "compile":
                return value
            if node.op == "copy":
                return list(value) if isinstance(value, list) else value
            # Every remaining unary command is an engine query that the
            # caller supplies through globals_ (surfaceType, isNull,
            # uniform, items, getText, ...).  A command that is registered
            # but not bound is a test error, reported as such.
            fn = self.globals.get(node.op)
            if callable(fn):
                return fn(value)
            raise ValueError(f"unknown unary command {node.op}")
        if isinstance(node, Switch):
            value = self.eval(node.expr)
            default = None
            for case_value, block in node.cases:
                if case_value is None:
                    default = block
                    continue
                # The engine evaluates the case expressions in source
                # order and runs the first that equals the switch value.
                if self.eval(case_value) == value:
                    self.push()
                    try:
                        return self.run(block)
                    finally:
                        self.pop()
            if default is not None:
                self.push()
                try:
                    return self.run(default)
                finally:
                    self.pop()
            return None
        if isinstance(node, Each):
            arr = self.eval(node.arr)
            code = self.eval(node.code)
            out: list = []
            for i, el in enumerate(arr):
                self.push()
                self.set("_x", el)
                self.set("_foreachindex", float(i))
                # Do NOT re-bind code.closure here: the block runs in the
                # current scope chain, so outer variables are already visible.
                # Re-binding a captured snapshot resets a variable that an
                # earlier iteration wrote, so an accumulator never grows.
                if isinstance(code, Lambda):
                    r = self.run(code.body)
                else:
                    r = None
                # SQF forEach shares the enclosing scope: an assignment to an
                # outer variable inside the block is visible after the loop.
                # Propagate those writes before the block scope is popped.
                inner = self.scopes[-1]
                for k, v in list(inner.items()):
                    if k in ("_x", "_foreachindex"):
                        continue
                    for outer in reversed(self.scopes[:-1]):
                        if k in outer:
                            outer[k] = v
                            break
                self.pop()
                if not node.keep:
                    out.append(r)
            return out if not node.keep else None
        if isinstance(node, FindIf):
            arr = self.eval(node.arr)
            code = self.eval(node.code)
            for i, el in enumerate(arr):
                self.push()
                self.set("_x", el)
                self.set("_foreachindex", float(i))
                if isinstance(code, Lambda):
                    r = self.run(code.body)
                else:
                    r = None
                inner = self.scopes[-1]
                for k, v in list(inner.items()):
                    if k in ("_x", "_foreachindex"):
                        continue
                    for outer in reversed(self.scopes[:-1]):
                        if k in outer:
                            outer[k] = v
                            break
                self.pop()
                if r:
                    return float(i)
            return -1.0
        if isinstance(node, Select):
            arr = self.eval(node.arr)
            idx = self.eval(node.idx)
            if isinstance(idx, bool):
                return arr[1] if idx else arr[0]
            if isinstance(idx, list):
                # SQF range select: arr select [start, count].  Works on an
                # array and on a string (HUD grid slice).
                start = int(idx[0])
                if len(idx) > 1:
                    return arr[start : start + int(idx[1])]
                return arr[start:]
            return arr[int(idx)]
        if isinstance(node, Call):
            fn = self.eval(node.fn)
            args = self.eval(node.args)
            if not isinstance(args, list):
                args = [args]
            if isinstance(fn, Lambda):
                self.push()
                for i, spec in enumerate(fn.params):
                    name, default = spec if isinstance(spec, tuple) else (spec, None)
                    if i < len(args):
                        self.set(name, args[i])
                    elif default is not None:
                        # An omitted argument binds the EVALUATED default,
                        # never the AST node.
                        self.set(name, self.eval(default))
                    else:
                        self.set(name, None)
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
            value = self.eval(s.expr)
            if s.private:
                # private declares in the CURRENT scope (it shadows an outer
                # variable of the same, case-insensitive, name).
                self.set(s.name, value)
            else:
                # A plain assignment writes the nearest scope that already
                # holds the name, else creates it in the current scope.
                for scope in reversed(self.scopes):
                    if s.name in scope:
                        scope[s.name] = value
                        break
                else:
                    self.set(s.name, value)
            return None
        if isinstance(s, ExprStmt):
            return self.eval(s.expr)
        if isinstance(s, If):
            # An if/else block is a new SQF scope: a `private` (or a first)
            # assignment inside it is local to the block, while a plain
            # assignment to an outer variable writes that variable (the
            # Assign rule above).  SQF `if` is an expression: return the
            # executed branch's value.
            branch = s.then if self.eval(s.cond) else s.els
            if not branch:
                return None
            self.push()
            try:
                return self.run(branch)
            finally:
                self.pop()
        if isinstance(s, For):
            lo = int(self.eval(s.lo))
            hi = int(self.eval(s.hi))
            for i in range(lo, hi + 1):
                self.push()
                self.set(s.var, float(i))
                try:
                    self.run(s.body)
                except ContinueSignal:
                    pass
                finally:
                    self.pop()
            return None
        if isinstance(s, While):
            guard = 0
            while bool(self.run(s.cond)):
                try:
                    self.run(s.body)
                except ContinueSignal:
                    pass
                guard += 1
                if guard > 1000000:
                    raise RuntimeError("while loop guard exceeded")
            return None
        if isinstance(s, Continue):
            raise ContinueSignal()
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
    float32: bool = False,
) -> Any:
    """Run an SQF function file with the given args.

    float32=True evaluates every number in IEEE single precision, the
    engine's number type, so precision bugs show in the test suite.
    """
    rt = SqfRuntime(globals_)
    rt.float32 = float32
    if float32:
        args = [
            _f32(float(a))
            if isinstance(a, int) and not isinstance(a, bool)
            else _f32(a)
            for a in args
        ]
    stmts = load_sqf(path)
    # bind params from the first Params statement
    for s in stmts:
        if isinstance(s, Params):
            for i, (name, default) in enumerate(s.specs):
                # A missing arg must bind the EVALUATED default, not the raw
                # AST node parse_params stored (a Num/Str/Arr object), or a
                # later `max`/arithmetic on it raises.
                rt.set(name, args[i] if i < len(args) else rt.eval(default))
            break
    return rt.run(stmts)
