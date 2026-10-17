"""Loads the JSON rule database and provides parameter validation."""
from __future__ import annotations

import difflib
import json
import os
from dataclasses import dataclass, field
from typing import Any

from .sqf import UNKNOWN

DEFAULT_RULE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules")


@dataclass
class Rules:
    pp: dict
    tc: dict
    effects: dict = field(init=False)
    alias: dict = field(init=False)
    canon: dict = field(init=False)
    thresholds: dict = field(init=False)

    def __post_init__(self):
        self.effects = self.pp["effects"]
        self.alias = {k: v for k, v in self.pp.get("name_aliases", {}).items() if not k.startswith("_")}
        self.canon = {k.lower(): k for k in self.effects}
        self.thresholds = {k: v for k, v in self.pp["thresholds"].items() if not k.startswith("_")}

    def normalize_effect(self, name: Any) -> tuple[str | None, str | None]:
        """-> (canonical or None, alias_hint)"""
        if not isinstance(name, str):
            return None, None
        low = name.lower()
        if low in self.canon:
            return self.canon[low], None
        if low in self.alias:
            return None, self.alias[low]
        return None, None

    def suggest(self, name: str) -> str | None:
        m = difflib.get_close_matches(name.lower(), list(self.canon), n=1, cutoff=0.6)
        return self.canon[m[0]] if m else None


def load_rules(rule_dir: str | None = None) -> Rules:
    d = rule_dir or DEFAULT_RULE_DIR
    with open(os.path.join(d, "post_process.json"), encoding="utf-8") as f:
        pp = json.load(f)
    with open(os.path.join(d, "thermal_camera.json"), encoding="utf-8") as f:
        tc = json.load(f)
    return Rules(pp, tc)


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
Issue = tuple  # (rule, severity, message, prov)


def _fmt_range(lo, hi) -> str:
    return f"{'-inf' if lo is None else lo}..{'+inf' if hi is None else hi}"


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_value(spec: dict, v: Any, out: list[Issue], label: str) -> None:
    if v is UNKNOWN:
        return
    kind = spec["kind"]
    prov = spec.get("prov", "wiki")
    oor = spec.get("oor", "warning")
    if kind in ("float", "int"):
        if not _num(v):
            out.append(("PP003", "warning", f"{label}: expected a number, got {v!r}", prov))
            return
        if kind == "int" and float(v) != int(v):
            out.append(("PP003", "warning", f"{label}={v}: expected an integer", prov))
        lo, hi = spec.get("min"), spec.get("max")
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            out.append(("PP003", oor, f"{label}={v} is outside the documented range {_fmt_range(lo, hi)}", prov))
            return
        slo, shi = spec.get("soft_min"), spec.get("soft_max")
        ssev = spec.get("soft_sev", "info")
        gate = spec.get("soft_min_if_ge")
        if slo is not None and v < slo and (gate is None or v >= gate):
            note = spec.get("soft_note") or spec.get("why", "")
            out.append(("PP003", ssev, f"{label}={v} is unusually low (heuristic bound {slo}). {note}".strip(), "heuristic"))
        elif shi is not None and v > shi:
            note = spec.get("why", "")
            out.append(("PP003", ssev, f"{label}={v} is unusually high (heuristic bound {shi}). {note}".strip(), "heuristic"))
    elif kind == "bool":
        if isinstance(v, bool):
            return
        if _num(v) and v in (0, 1):
            return
        out.append(("PP003", "warning", f"{label}: expected true/false, got {v!r}", prov))
    elif kind == "boolnum":
        if isinstance(v, bool):
            out.append(("PP017", "info", f"{label}={v}: Arma 3 expects a number (0 = monochrome, other = colour)", "wiki"))
        elif not _num(v):
            out.append(("PP003", "warning", f"{label}: expected a number, got {v!r}", prov))
    elif kind == "color":
        if not isinstance(v, list):
            out.append(("PP003", "warning", f"{label}: expected [r,g,b,a] array, got {v!r}", prov))
            return
        if len(v) != 4:
            out.append(("PP003", "warning", f"{label}: colour arrays have 4 components, got {len(v)}", prov))
        for c, comp in zip(v, "rgba"):
            if c is UNKNOWN:
                continue
            if not _num(c):
                out.append(("PP003", "warning", f"{label}.{comp}: expected number, got {c!r}", prov))
        for idx, (c, (lo, hi)) in enumerate(zip(v, spec["comp"])):
            if c is UNKNOWN or not _num(c):
                continue
            if lo == hi:
                if c != lo:
                    out.append(("PP003", "info", f"{label}.{'rgba'[idx]}={c}: documented to be {lo}", prov))
            elif c < lo or c > hi:
                out.append(("PP003", oor, f"{label}.{'rgba'[idx]}={c} is outside the documented range {lo}..{hi}", prov))
    elif kind == "array":
        if not isinstance(v, list):
            out.append(("PP003", "warning", f"{label}: expected an array", prov))
            return
        items = spec["items"]
        if len(v) != len(items):
            out.append(("PP002", "warning", f"{label}: expected {len(items)} elements, got {len(v)}", prov))
        for it, val in zip(items, v):
            check_value(it, val, out, f"{label}.{it['name']}")


def pack_color_corrections(params: list) -> tuple[list, bool]:
    """Flat handle-syntax arrays (15 or 22 numbers) -> packed layout. Returns (params, was_flat)."""
    n = len(params)
    if n in (15, 22) and not any(isinstance(p, list) for p in params[3:15]):
        packed = params[:3] + [params[3:7], params[7:11], params[11:15]]
        if n == 22:
            packed.append(params[15:22])
        return packed, True
    return params, False


def validate_params(rules: Rules, effect: str, params: Any, syntax: str) -> list[Issue]:
    """Validate an ppEffectAdjust / config params array. `syntax` is 'name' or 'handle'."""
    out: list[Issue] = []
    if not isinstance(params, list):
        return out
    spec = rules.effects[effect]
    plist = params
    if effect == "ColorCorrections":
        plist, flat = pack_color_corrections(params)
        if flat and syntax == "name":
            out.append(("PP012", "error", "flat colour values are not accepted by the by-name syntax; pack colours in [r,g,b,a] sub-arrays", "wiki"))
    n = len(plist)
    if n < spec["min_params"] or n > spec["max_params"]:
        want = f"{spec['min_params']}" if spec["min_params"] == spec["max_params"] else f"{spec['min_params']}-{spec['max_params']}"
        out.append(("PP002", "error", f"{effect} takes {want} parameters, got {n}", "wiki"))
    for k, pspec in enumerate(spec["params"]):
        if k >= n:
            break
        check_value(pspec, plist[k], out, pspec["name"])
    return out


def defaults_of(rules: Rules, effect: str) -> list:
    return [p["default"] for p in rules.effects[effect]["params"]]
