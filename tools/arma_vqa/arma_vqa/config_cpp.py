"""Tiny config.cpp / .hpp / description.ext reader.

Reads class trees and property values well enough to inspect
CfgOpticsEffect, optics modes (opticsPPEffects / visionMode / thermalMode)
and nothing else. Inheritance from classes defined in *other* files is not
resolved: such properties are simply absent (checks skip absent values).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .sqf import UNKNOWN, Evaluator, Lexed, expr_end


@dataclass
class CfgClass:
    name: str
    parent: str | None
    line: int
    file: str
    props: dict[str, tuple[Any, int]] = field(default_factory=dict)  # lower name -> (value, line)
    children: dict[str, "CfgClass"] = field(default_factory=dict)
    path: tuple[str, ...] = ()


def parse_config(lx: Lexed) -> CfgClass:
    root = CfgClass("<root>", None, 1, lx.path)
    ev = Evaluator(lambda n, i: UNKNOWN)
    _parse_body(lx, ev, 0, len(lx.toks), root)
    return root


def _skip_stmt(lx: Lexed, i: int, end: int) -> int:
    while i < end:
        t = lx.toks[i]
        if t.kind == "punct" and t.val in ("{", "[", "("):
            j = lx.match.get(i)
            i = (j + 1) if j is not None else end
            continue
        if t.kind == "punct" and t.val == ";":
            return i + 1
        i += 1
    return end


def _parse_body(lx: Lexed, ev: Evaluator, i: int, end: int, cls: CfgClass) -> None:
    toks = lx.toks
    while i < end:
        t = toks[i]
        if t.kind == "id" and t.val.lower() == "class":
            if i + 1 >= end or toks[i + 1].kind != "id":
                i += 1
                continue
            name = toks[i + 1].val
            j = i + 2
            parent = None
            if j < end and toks[j].kind == "op" and toks[j].val == ":":
                if j + 1 < end and toks[j + 1].kind == "id":
                    parent = toks[j + 1].val
                j += 2
            if j < end and toks[j].kind == "punct" and toks[j].val == "{":
                close = lx.match.get(j, end)
                child = cls.children.get(name.lower())
                if child is None:
                    child = CfgClass(name, parent, t.line, lx.path, path=cls.path + (name,))
                    cls.children[name.lower()] = child
                else:
                    child.parent = parent or child.parent
                _parse_body(lx, ev, j + 1, close, child)
                i = close + 1
                if i < end and toks[i].kind == "punct" and toks[i].val == ";":
                    i += 1
                continue
            # forward declaration
            i = _skip_stmt(lx, j, end)
            continue

        if t.kind == "id":
            low = t.val.lower()
            if low == "delete":
                i = _skip_stmt(lx, i, end)
                continue
            j = i + 1
            is_array = False
            if j + 1 < end and toks[j].kind == "punct" and toks[j].val == "[" and toks[j + 1].kind == "punct" and toks[j + 1].val == "]":
                is_array = True
                j += 2
            if j < end and toks[j].kind == "op" and toks[j].val == "+" and j + 1 < end and toks[j + 1].val == "=":
                j += 1  # +=
            if j < end and toks[j].kind == "op" and toks[j].val == "=":
                j += 1
                if is_array and j < end and toks[j].kind == "punct" and toks[j].val == "{":
                    val, _ = _parse_cfg_array(lx, ev, j)
                    cls.props[low] = (val, t.line)
                    i = _skip_stmt(lx, j, end)
                    continue
                e = expr_end(lx, j)
                v = ev.eval(toks[j:e], j)
                if v is UNKNOWN and e - j == 1 and toks[j].kind == "id":
                    v = toks[j].val  # bare word
                cls.props[low] = (v, t.line)
                i = _skip_stmt(lx, e, end)
                continue
        i = _skip_stmt(lx, i, end) if t.kind != "punct" or t.val != ";" else i + 1


def _parse_cfg_array(lx: Lexed, ev: Evaluator, i: int):
    """Parse `{a, b, {c, d}}` starting at the '{' token index i."""
    close = lx.match.get(i, i)
    items: list[Any] = []
    k = i + 1
    start = k
    while k <= close:
        t = lx.toks[k] if k < len(lx.toks) else None
        if k == close or (t is not None and t.kind == "punct" and t.val == ","):
            sl = lx.toks[start:k]
            if sl:
                items.append(_cfg_elem(lx, ev, start, k))
            start = k + 1
            if k == close:
                break
        elif t is not None and t.kind == "punct" and t.val in ("{", "[", "("):
            k = lx.match.get(k, k)
        k += 1
    return items, close


def _cfg_elem(lx: Lexed, ev: Evaluator, a: int, b: int):
    sl = lx.toks[a:b]
    if sl and sl[0].kind == "punct" and sl[0].val == "{":
        sub, _ = _parse_cfg_array(lx, ev, a)
        return sub
    v = ev.eval(sl, -1)
    if v is UNKNOWN and len(sl) == 1 and sl[0].kind == "id":
        return sl[0].val
    return v


def walk(cls: CfgClass):
    yield cls
    for c in cls.children.values():
        yield from walk(c)
