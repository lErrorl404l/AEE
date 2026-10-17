"""Light-weight SQF tokenizer / constant folder.

This is NOT a full SQF parser. It does just enough to find calls to the
visual commands we care about, recover their literal arguments (with simple
constant propagation) and know which block they sit in. Anything it cannot
resolve becomes UNKNOWN, and checks never fire on UNKNOWN values (no false
positives from dynamic code).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class _Unknown:
    _inst = None

    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self) -> str:  # pragma: no cover
        return "?"

    def __bool__(self) -> bool:
        return False


UNKNOWN = _Unknown()


@dataclass
class Tok:
    kind: str  # id | num | str | punct | op
    val: Any
    line: int


_TOKEN_RE = re.compile(
    r"""
  (?P<pp>^[ \t]*\#[ \t]*(?:define|include|ifdef|ifndef|else|endif|undef|if|elif)\b(?:\\\r?\n|[^\n])*)
 |(?P<ws>\n|[ \t\r]+)
 |(?P<lc>//[^\n]*)
 |(?P<bc>/\*.*?\*/)
 |(?P<str>"(?:[^"]|"")*"|'(?:[^']|'')*')
 |(?P<num>0[xX][0-9A-Fa-f]+|\$[0-9A-Fa-f]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
 |(?P<id>[A-Za-z_][A-Za-z0-9_]*)
 |(?P<op>==|!=|<=|>=|&&|\|\||>>|[-+*/%^<>=!:\#])
 |(?P<punct>[\[\]\{\}\(\),;])
""",
    re.X | re.S | re.M,
)

_IGNORE_RE = re.compile(r"vqa-ignore(-file)?\s*[:=]?\s*([A-Za-z0-9_,\s-]*)")


@dataclass
class Lexed:
    path: str
    toks: list[Tok]
    defines: dict[str, list[Tok]]
    includes: list[str]
    ignores: dict[int, set[str]]
    ignore_file: set[str]
    owners: list[tuple]  # per-token tuple of enclosing block keywords (lowercase)
    match: dict[int, int]  # bracket index -> matching index


def _unquote(s: str) -> str:
    q = s[0]
    return s[1:-1].replace(q + q, q)


def _parse_num(s: str) -> float | int:
    if s.startswith("$"):
        return int(s[1:], 16)
    if s[:2].lower() == "0x":
        return int(s, 16)
    f = float(s)
    return int(f) if re.fullmatch(r"\d+", s) else f


def tokenize(text: str, path: str = "<mem>", extra_defines: dict | None = None) -> Lexed:
    toks: list[Tok] = []
    defines: dict[str, list[Tok]] = dict(extra_defines or {})
    includes: list[str] = []
    ignores: dict[int, set[str]] = {}
    ignore_file: set[str] = set()
    line = 1
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN_RE.match(text, pos)
        if not m:
            pos += 1
            continue
        kind = m.lastgroup
        raw = m.group()
        tl = line
        line += raw.count("\n")
        pos = m.end()
        if kind == "ws":
            continue
        if kind in ("lc", "bc"):
            im = _IGNORE_RE.search(raw)
            if im:
                ids = {x.strip().upper() for x in re.split(r"[,\s]+", im.group(2)) if x.strip()}
                if im.group(1):
                    ignore_file |= ids or {"*"}
                else:
                    ignores.setdefault(tl, set()).update(ids or {"*"})
            continue
        if kind == "pp":
            _handle_directive(raw, tl, defines, includes)
            continue
        if kind == "str":
            toks.append(Tok("str", _unquote(raw), tl))
        elif kind == "num":
            toks.append(Tok("num", _parse_num(raw), tl))
        elif kind == "id":
            toks.append(Tok("id", raw, tl))
        elif kind == "op":
            toks.append(Tok("op", raw, tl))
        else:
            toks.append(Tok("punct", raw, tl))
    toks = _expand_macros(toks, defines)
    toks = _collapse_symbol_macros(toks, path)
    owners, match = _structure(toks)
    return Lexed(path, toks, defines, includes, ignores, ignore_file, owners, match)


# ---------------------------------------------------------------------------
# CBA/ACE style variable macros:  GVAR(x) -> <component>_x   EGVAR(c,x) -> c_x
# These are pure naming macros. Collapsing them into one identifier makes
# `GVAR(ppe) = ppEffectCreate [...]` / `GVAR(ppe) ppEffectAdjust [...]` trackable
# like any other handle variable. The mod prefix is not needed, only consistency.
# ---------------------------------------------------------------------------
_COMPONENT_RE = re.compile(r"^\s*#\s*define\s+COMPONENT\s+([A-Za-z0-9_]+)", re.M)
_component_cache: dict[str, str] = {}


def component_for(path: str) -> str:
    """Name of the CBA component a file belongs to (used to expand GVAR)."""
    import os

    if not path or path.startswith("<"):
        return "mod"
    d = os.path.dirname(os.path.abspath(path))
    start = d
    if start in _component_cache:
        return _component_cache[start]
    comp = None
    cur = d
    for _ in range(8):
        sc = os.path.join(cur, "script_component.hpp")
        if os.path.isfile(sc):
            try:
                with open(sc, encoding="utf-8", errors="replace") as f:
                    m = _COMPONENT_RE.search(f.read())
                comp = m.group(1) if m else os.path.basename(cur)
            except OSError:
                comp = os.path.basename(cur)
            break
        if os.path.isfile(os.path.join(cur, "config.cpp")):
            comp = os.path.basename(cur)
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    comp = comp or os.path.basename(d) or "mod"
    _component_cache[start] = comp
    return comp


_SYMBOL_MACROS = {"gvar": 1, "gvarmain": 1, "egvar": 2, "egvarmain": 2}


def _collapse_symbol_macros(toks: list[Tok], path: str) -> list[Tok]:
    if not any(t.kind == "id" and t.val.lower() in _SYMBOL_MACROS for t in toks):
        return toks
    comp = component_for(path)
    out: list[Tok] = []
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if t.kind == "id" and t.val.lower() in _SYMBOL_MACROS and i + 1 < n and toks[i + 1].kind == "punct" and toks[i + 1].val == "(":
            want = _SYMBOL_MACROS[t.val.lower()]
            args: list[str] = []
            j = i + 2
            ok = False
            while j < n:
                a = toks[j]
                if a.kind in ("id", "num"):
                    args.append(str(a.val))
                    j += 1
                    if j < n and toks[j].kind == "punct" and toks[j].val == ",":
                        j += 1
                        continue
                    if j < n and toks[j].kind == "punct" and toks[j].val == ")":
                        ok = len(args) == want
                    break
                break
            if ok:
                low = t.val.lower()
                if low == "gvar":
                    name = f"{comp}_{args[0]}"
                elif low == "gvarmain":
                    name = f"main_{args[0]}"
                elif low == "egvar":
                    name = f"{args[0]}_{args[1]}"
                else:
                    name = f"{args[0]}_{args[1]}"
                out.append(Tok("id", name, t.line))
                i = j + 1
                continue
        out.append(t)
        i += 1
    return out


def _handle_directive(raw: str, line: int, defines: dict, includes: list) -> None:
    body = raw.replace("\\\r\n", " ").replace("\\\n", " ").strip()
    m = re.match(r"#\s*include\s+[\"<]([^\">]+)[\">]", body)
    if m:
        includes.append(m.group(1))
        return
    m = re.match(r"#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)(\()?(.*)$", body, re.S)
    if m and not m.group(2):  # object-like macros only
        body_txt = m.group(3).strip()
        sub = tokenize_simple(body_txt, line)
        defines[m.group(1)] = sub


def tokenize_simple(text: str, line: int) -> list[Tok]:
    out: list[Tok] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            pos += 1
            continue
        kind, raw = m.lastgroup, m.group()
        pos = m.end()
        if kind in ("ws", "lc", "bc", "pp"):
            continue
        if kind == "str":
            out.append(Tok("str", _unquote(raw), line))
        elif kind == "num":
            out.append(Tok("num", _parse_num(raw), line))
        else:
            out.append(Tok(kind, raw, line))
    return out


def _expand_macros(toks: list[Tok], defines: dict[str, list[Tok]], depth: int = 0) -> list[Tok]:
    if not defines or depth > 3:
        return toks
    out: list[Tok] = []
    changed = False
    for i, t in enumerate(toks):
        if t.kind == "id" and t.val in defines:
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if nxt is not None and nxt.kind == "punct" and nxt.val == "(":
                out.append(t)  # looks function-like; leave it
                continue
            for s in defines[t.val]:
                out.append(Tok(s.kind, s.val, t.line))
            changed = True
        else:
            out.append(t)
    return _expand_macros(out, defines, depth + 1) if changed else out


_OPEN = {"[": "]", "{": "}", "(": ")"}


def _structure(toks: list[Tok]):
    owners: list[tuple] = []
    match: dict[int, int] = {}
    stack: list[tuple[str, int]] = []  # (bracket, index)
    block_stack: list[str] = []
    for i, t in enumerate(toks):
        owners.append(tuple(block_stack))
        if t.kind != "punct":
            continue
        if t.val in _OPEN:
            stack.append((t.val, i))
            if t.val == "{":
                prev = toks[i - 1] if i > 0 else None
                block_stack.append(prev.val.lower() if prev is not None and prev.kind == "id" else "")
        elif t.val in ("]", "}", ")"):
            for k in range(len(stack) - 1, -1, -1):
                if _OPEN[stack[k][0]] == t.val:
                    o = stack[k][1]
                    match[o] = i
                    match[i] = o
                    if stack[k][0] == "{" and block_stack:
                        block_stack.pop()
                    del stack[k:]
                    break
    return owners, match


# ---------------------------------------------------------------------------
# expression evaluation
# ---------------------------------------------------------------------------

class _Fail(Exception):
    pass


class Evaluator:
    """Evaluates small constant expressions. `resolve(name, idx)` returns a value or UNKNOWN."""

    def __init__(self, resolve):
        self.resolve = resolve

    def eval(self, toks: list[Tok], at: int = -1) -> Any:
        if not toks:
            return UNKNOWN
        try:
            self._t, self._i, self._at = toks, 0, at
            v = self._expr()
            if self._i != len(toks):
                return UNKNOWN
            return v
        except _Fail:
            return UNKNOWN
        except (ZeroDivisionError, OverflowError, TypeError):
            return UNKNOWN

    # grammar -------------------------------------------------------------
    def _peek(self):
        return self._t[self._i] if self._i < len(self._t) else None

    def _expr(self):
        v = self._term()
        while True:
            p = self._peek()
            if p is not None and p.kind == "op" and p.val in ("+", "-"):
                self._i += 1
                r = self._term()
                if v is UNKNOWN or r is UNKNOWN:
                    v = UNKNOWN
                elif isinstance(v, (int, float)) and isinstance(r, (int, float)) and not isinstance(v, bool) and not isinstance(r, bool):
                    v = v + r if p.val == "+" else v - r
                elif p.val == "+" and isinstance(v, str) and isinstance(r, str):
                    v = v + r
                else:
                    v = UNKNOWN
            else:
                return v

    def _term(self):
        v = self._unary()
        while True:
            p = self._peek()
            if p is not None and p.kind == "op" and p.val in ("*", "/", "%"):
                self._i += 1
                r = self._unary()
                if v is UNKNOWN or r is UNKNOWN or isinstance(v, (bool, str, list)) or isinstance(r, (bool, str, list)):
                    v = UNKNOWN
                else:
                    v = v * r if p.val == "*" else (v / r if p.val == "/" else v % r)
            else:
                return v

    def _unary(self):
        p = self._peek()
        if p is not None and p.kind == "op" and p.val in ("-", "+"):
            self._i += 1
            v = self._unary()
            if v is UNKNOWN or isinstance(v, (bool, str, list)):
                return UNKNOWN
            return -v if p.val == "-" else v
        return self._primary()

    def _primary(self):
        p = self._peek()
        if p is None:
            raise _Fail
        if p.kind == "num":
            self._i += 1
            return p.val
        if p.kind == "str":
            self._i += 1
            return p.val
        if p.kind == "id":
            low = p.val.lower()
            if low in ("true", "false"):
                self._i += 1
                return low == "true"
            idx = self._i
            self._i += 1
            nxt = self._peek()
            # an identifier followed by something that looks like a command call -> give up
            if nxt is not None and (nxt.kind in ("id", "str", "num") or (nxt.kind == "punct" and nxt.val in ("[", "("))):
                raise _Fail
            return self.resolve(p.val, self._at if self._at >= 0 else idx)
        if p.kind == "punct" and p.val == "(":
            self._i += 1
            v = self._expr()
            q = self._peek()
            if q is None or q.val != ")":
                raise _Fail
            self._i += 1
            return v
        if p.kind == "punct" and p.val == "[":
            return self._array()
        raise _Fail

    def _array(self):
        self._i += 1  # [
        items: list[Any] = []
        p = self._peek()
        if p is not None and p.kind == "punct" and p.val == "]":
            self._i += 1
            return items
        while True:
            items.append(self._expr())
            p = self._peek()
            if p is None:
                raise _Fail
            if p.kind == "punct" and p.val == ",":
                self._i += 1
                continue
            if p.kind == "punct" and p.val == "]":
                self._i += 1
                return items
            raise _Fail


# ---------------------------------------------------------------------------
# call extraction
# ---------------------------------------------------------------------------

BINARY_CMDS = {
    "ppeffectadjust", "ppeffectcommit", "ppeffectenable", "ppeffectforceinnvg",
    "setpipeffect", "setcamuseti", "cameraeffect",
    "camsetfov", "disabletiequipment", "disablenvgequipment", "setvehicletipars",
    "settonemappingparams",
}
UNARY_CMDS = {
    "ppeffectcreate", "ppeffectdestroy", "settiparameter", "setaperture",
    "setaperturenew", "camusenvg", "camcreate", "settonemapping",
}
EITHER_CMDS = {"cutrsc", "cuttext", "titlersc", "titletext", "cutobj", "titleobj"}
# BIS functions that create/replace post-process effects: `[args] call BIS_fnc_x`
FUNC_CALLS = {"bis_fnc_setppeffecttemplate", "bis_fnc_ambientpostprocess"}
ALL_CMDS = BINARY_CMDS | UNARY_CMDS | EITHER_CMDS | FUNC_CALLS
_NOT_LEFT = {"then", "do", "else", "spawn", "call", "exitwith", "if", "while", "waituntil", "private", "return"}


@dataclass
class Call:
    cmd: str  # lowercase
    cmd_raw: str
    file: str
    line: int
    tok: int
    left: Any = None
    left_ref: Any = None  # var name | (var, idx) | list of those
    right: Any = None
    right_ref: Any = None
    assigned_to: str | None = None
    retry: bool = False
    owners: tuple = ()
    has_left: bool = False


@dataclass
class FileFacts:
    lexed: Lexed
    calls: list[Call] = field(default_factory=list)
    assigns: dict[str, list[tuple[int, Any]]] = field(default_factory=dict)
    idents: set[str] = field(default_factory=set)
    strings: set[str] = field(default_factory=set)


def collect_assignments(lx: Lexed) -> dict[str, list[tuple[int, Any]]]:
    """name(lower) -> [(token_index, value)]  (value UNKNOWN when not foldable)."""
    out: dict[str, list[tuple[int, Any]]] = {}
    toks = lx.toks
    ev = Evaluator(lambda name, idx: UNKNOWN)  # pass 1 can't resolve; fine for literals

    for i, t in enumerate(toks):
        if t.kind == "op" and t.val == "=" and i >= 1 and toks[i - 1].kind == "id":
            name = toks[i - 1].val
            if name.lower() in ("private", "params"):
                continue
            end = expr_end(lx, i + 1)
            val = ev.eval(toks[i + 1:end], i)
            out.setdefault(name.lower(), []).append((i, val))
    return out


def expr_end(lx: Lexed, start: int) -> int:
    """Index one past the last token of the expression starting at `start`."""
    toks = lx.toks
    i = start
    n = len(toks)
    while i < n:
        t = toks[i]
        if t.kind == "punct":
            if t.val in ("[", "(", "{"):
                j = lx.match.get(i)
                if j is None:
                    return n
                i = j + 1
                continue
            if t.val in (";", ",", "]", ")", "}"):
                return i
        i += 1
    return n


def make_resolver(lx: Lexed, local: dict, global_assigns: dict):
    def resolve(name: str, idx: int):
        low = name.lower()
        cands = local.get(low)
        if cands is None and not low.startswith("_"):
            cands = global_assigns.get(low)
            idx = 10 ** 9  # global: position independent
        if not cands:
            return UNKNOWN
        before = [(i, v) for i, v in cands if i < idx] if idx < 10 ** 9 else list(cands)
        if not before:
            return UNKNOWN
        vals = [v for _, v in before]
        if any(v is UNKNOWN for v in vals):
            return UNKNOWN
        first = vals[0]
        if all(_same(first, v) for v in vals):
            return first
        return UNKNOWN

    return resolve


def _same(a, b) -> bool:
    try:
        return a == b and type(a) is type(b)
    except Exception:  # pragma: no cover
        return False


def extract_calls(lx: Lexed, global_assigns: dict) -> FileFacts:
    ff = FileFacts(lx)
    ff.assigns = collect_assignments(lx)
    resolve = make_resolver(lx, ff.assigns, global_assigns)
    ev = Evaluator(resolve)
    toks = lx.toks

    for t in toks:
        if t.kind == "id":
            ff.idents.add(t.val.lower())
        elif t.kind == "str":
            ff.strings.add(t.val)

    for i, t in enumerate(toks):
        if t.kind != "id":
            continue
        low = t.val.lower()
        if low not in ALL_CMDS:
            continue
        c = Call(low, t.val, lx.path, t.line, i, owners=lx.owners[i])

        if low in FUNC_CALLS:
            prev = toks[i - 1] if i > 0 else None
            if prev is None or prev.kind != "id" or prev.val.lower() not in ("call", "spawn"):
                continue  # referenced, not invoked here
            c.has_left, c.left, c.left_ref = _left_operand(lx, i - 1, ev, resolve)
            ff.calls.append(c)
            continue

        # ---- left operand
        has_left = False
        if low in BINARY_CMDS or low in EITHER_CMDS:
            has_left, c.left, c.left_ref = _left_operand(lx, i, ev, resolve)
            if low in EITHER_CMDS and not has_left:
                c.left = None
        c.has_left = has_left

        # ---- right operand
        end = expr_end(lx, i + 1)
        rslice = toks[i + 1:end]
        c.right = ev.eval(rslice, i)
        c.right_ref = _ref_of(rslice)
        if rslice and rslice[0].kind == "punct" and rslice[0].val == "[" and lx.match.get(i + 1) == end - 1:
            c.right_ref = [_ref_of(toks[a:b]) for a, b in _split_top(lx, i + 2, end - 1)]

        # ---- assignment target (for ppEffectCreate)
        if low == "ppeffectcreate" and i >= 2 and toks[i - 1].kind == "op" and toks[i - 1].val == "=" and toks[i - 2].kind == "id":
            c.assigned_to = toks[i - 2].val
        # retry loop detection
        if low == "ppeffectcreate":
            c.retry = any(o in ("while", "waituntil") for o in c.owners)
        ff.calls.append(c)
    return ff


def _ref_of(sl: list[Tok]):
    if len(sl) == 1 and sl[0].kind == "id":
        return sl[0].val
    return None


def _left_operand(lx: Lexed, i: int, ev: Evaluator, resolve):
    toks = lx.toks
    if i == 0:
        return False, None, None
    p = toks[i - 1]
    if p.kind == "id":
        if p.val.lower() in _NOT_LEFT:
            return False, None, None
        low = p.val.lower()
        if low in ("true", "false"):
            return True, low == "true", None
        return True, resolve(p.val, i), p.val
    if p.kind == "str":
        return True, p.val, None
    if p.kind == "num":
        return True, p.val, None
    if p.kind == "punct" and p.val in (")", "]"):
        o = lx.match.get(i - 1)
        if o is None:
            return False, None, None
        inner = toks[o + 1:i - 1]
        if p.val == "]":
            refs = []
            vals = []
            # list of handles/vars e.g. [_h1,_h2]
            parts = _split_top(lx, o + 1, i - 1)
            for a, b in parts:
                sl = toks[a:b]
                refs.append(_ref_of(sl))
                vals.append(ev.eval(sl, i))
            return True, vals, refs
        # parenthesised: (_h select 1) | (_h # 1)
        if len(inner) == 3 and inner[0].kind == "id" and inner[2].kind == "num" and (
            (inner[1].kind == "id" and inner[1].val.lower() == "select") or (inner[1].kind == "op" and inner[1].val == "#")
        ):
            return True, UNKNOWN, (inner[0].val, int(inner[2].val))
        return True, ev.eval(inner, i), None
    return False, None, None


def _split_top(lx: Lexed, a: int, b: int) -> list[tuple[int, int]]:
    parts = []
    start = a
    i = a
    while i < b:
        t = lx.toks[i]
        if t.kind == "punct" and t.val in ("[", "(", "{"):
            j = lx.match.get(i, b)
            i = j + 1
            continue
        if t.kind == "punct" and t.val == ",":
            parts.append((start, i))
            start = i + 1
        i += 1
    if start < b:
        parts.append((start, b))
    return parts
