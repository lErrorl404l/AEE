#!/usr/bin/env python3
"""Rewrite the AEE tree from the compartmentalisation map.

One map drives the 24 -> 45 addon migration.  This tool reads
``docs/architecture/addon-map.json`` (every source file and symbol -> its
destination addon) and ``docs/architecture/settings-map.json`` (every old
setting name -> its new name), then rewrites the references the move leaves
stale:

  * source paths, e.g. ``addons/optics/functions/eye/...`` -> the destination
    addon prefix and ``z\\aee\\addons\\main\\...`` -> ``z\\aee\\addons\\lib\\...``;
  * ``EFUNC(<old>,<name>)`` / ``EGVAR(<old>,<name>)`` component tokens when the
    named function or global moves addon;
  * setting names ``aee_<old>_<leaf>`` -> the new name;
  * ``STR_AEE_<Old>_<key>`` stringtable keys when the owning module moves.

The rewrite is a post-move reference fixer.  After a step's ``git mv`` the
old location is gone and the new location exists.  A rule fires only when its
destination addon directory exists on disk, so the tool is a no-op before any
move and idempotent afterwards: a second ``--apply`` makes no change, and
``--check`` after ``--apply`` is clean.  An ambiguous reference (a path whose
files do not all move to one addon, such as ``addons/optics/``) is never
rewritten.

CLI
---
    python3 tools/compartmentalise/rewrite_paths.py --check
        Report what WOULD change.  Exit 1 when a change is pending, 0 when the
        tree is clean.
    python3 tools/compartmentalise/rewrite_paths.py --apply
        Write the changes.  Exit 0.
    python3 tools/compartmentalise/rewrite_paths.py --step 3
        Apply only the slice of the nine-step migration whose destinations are
        created by step 3 (eye + vision).  Omit for every enabled rule.
    python3 tools/compartmentalise/rewrite_paths.py --to cartography
        Apply only the rules whose destination addon is ``cartography``.
    python3 tools/compartmentalise/rewrite_paths.py --root /path/to/tree
        Point at a tree other than the repository root (used by the self-test).

The two map files and this tool's own directory are never rewritten.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_MAP_REL = Path("docs/architecture/addon-map.json")
SETTINGS_MAP_REL = Path("docs/architecture/settings-map.json")

TEXT_SUFFIXES = frozenset(
    {
        ".sqf",
        ".hpp",
        ".h",
        ".cpp",
        ".inc",
        ".xml",
        ".md",
        ".py",
        ".txt",
        ".json",
        ".cfg",
        ".qmd",
        ".toml",
        ".yml",
        ".yaml",
        ".sh",
    }
)
SKIP_DIRS = frozenset({".git", ".opencode", "__pycache__", "node_modules", ".venv"})
SKIP_REL = frozenset({str(ADDON_MAP_REL), str(SETTINGS_MAP_REL)})
SKIP_PREFIXES = ("tools/compartmentalise/",)

# The nine migration steps (plan section 5), by the destination addon each
# creates.  A rule is in a step when its destination is in the step's set.
STEPS: dict[int, frozenset[str]] = {
    1: frozenset({"lib"}),
    2: frozenset({"diagnostics"}),
    3: frozenset({"eye", "vision"}),
    4: frozenset({"symbology", "cartography", "hud"}),
    5: frozenset({"weather", "lighting", "persistence"}),
    6: frozenset({"strain", "altitude", "dive", "clothing"}),
    7: frozenset({"thermal_display"}),
    8: frozenset({"flight", "vehicles", "hydrology"}),
    9: frozenset({"particles", "weatherfx", "blast", "ambience", "ltm", "magnetism"}),
}

_SYM_RE = re.compile(
    r"(EFUNC|EGVAR)\((\s*)([A-Za-z0-9_]+)(\s*,\s*)([A-Za-z0-9_]+)(\s*)\)"
)
_STR_RE = re.compile(r"STR_AEE_([A-Za-z0-9]+)_([A-Za-z0-9]+)_(Name|Description)\b")


@dataclass(frozen=True)
class PathRule:
    pattern: str
    replacement: str
    dest: str
    is_prefix: bool


@dataclass(frozen=True)
class SettingRule:
    old: str
    new: str
    dest: str


@dataclass(frozen=True)
class Rules:
    path: tuple[PathRule, ...]
    setting: tuple[SettingRule, ...]
    funcs: dict[tuple[str, str], str]
    vars: dict[str, str]
    stringtable: dict[tuple[str, str], str]


def existing_addons(root: Path) -> set[str]:
    addons = root / "addons"
    if not addons.is_dir():
        return set()
    return {p.name for p in addons.iterdir() if p.is_dir()}


def module_of(name: str, addons: set[str]) -> tuple[str, str] | None:
    """Split ``aee_<module>_<leaf>`` using the longest known addon name."""
    if not name.startswith("aee_"):
        return None
    rest = name[4:]
    matches = [a for a in addons if rest == a or rest.startswith(a + "_")]
    if not matches:
        return None
    module = max(matches, key=len)
    leaf = rest[len(module) + 1 :] if rest != module else ""
    return module, leaf


def _annotate(lines: list[str]) -> list[str]:
    """Return a printable line for a report, without a stray trailing newline."""
    return [line.rstrip("\n") for line in lines]


def _compile(
    pairs: list[tuple[str, str]], *, prefix: bool
) -> tuple[re.Pattern[str], dict[str, str]] | None:
    if not pairs:
        return None
    pairs = sorted(pairs, key=lambda p: len(p[0]), reverse=True)
    lookup = {pat: rep for pat, rep in pairs}
    alts = "|".join(re.escape(pat) for pat, _ in pairs)
    tail = "" if prefix else "(?![A-Za-z0-9_.])"
    return re.compile(f"(?<![A-Za-z0-9_])(?:{alts}){tail}"), lookup


def build_path_rules(addon_map: dict) -> list[PathRule]:
    files = {s: d for s, d in addon_map["files"].items() if s.startswith("addons/")}
    globs: dict[str, str] = {}
    for glob, meta in addon_map["data"].items():
        if glob.startswith("addons/"):
            prefix = glob[:-3].rstrip("/") if glob.endswith("/**") else glob
            globs[prefix] = meta["destination"]

    dir_dests: dict[str, set[str]] = defaultdict(set)

    def note(path: str, dest: str) -> None:
        parts = path.split("/")
        for i in range(2, len(parts) + 1):
            dir_dests["/".join(parts[:i])].add(dest)

    for src, dest in files.items():
        note(src, dest)
    for prefix, dest in globs.items():
        note(prefix, dest)

    rules: list[PathRule] = []
    for node, dests in dir_dests.items():
        if len(dests) != 1:
            continue
        parts = node.split("/")
        if len(parts) < 3:  # 'addons' and the addon root: handled below
            continue
        if len(parts) > 3 and len(dir_dests.get("/".join(parts[:-1]), set())) == 1:
            continue  # a broader uniform ancestor below the addon root exists
        dest = next(iter(dests))
        addon = parts[1]
        if dest == addon:
            continue  # the file stays: do not rewrite
        rest = "/".join(parts[2:])
        rest_bwd = rest.replace("/", "\\")
        is_prefix = node not in files
        tail = "/" if is_prefix else ""
        tail_bwd = "\\" if is_prefix else ""
        rules.append(
            PathRule(
                f"addons/{addon}/{rest}{tail}",
                f"addons/{dest}/{rest}{tail}",
                dest,
                is_prefix,
            )
        )
        rules.append(
            PathRule(
                f"z\\aee\\addons\\{addon}\\{rest_bwd}{tail_bwd}",
                f"z\\aee\\addons\\{dest}\\{rest_bwd}{tail_bwd}",
                dest,
                is_prefix,
            )
        )

    for addon, info in addon_map["addons"].items():
        dests = info["destinations"]
        if len(dests) == 1 and dests[0] != addon:
            dest = dests[0]
            rules.append(PathRule(f"addons/{addon}/", f"addons/{dest}/", dest, True))
            rules.append(
                PathRule(
                    f"z\\aee\\addons\\{addon}\\",
                    f"z\\aee\\addons\\{dest}\\",
                    dest,
                    True,
                )
            )
    return rules


def build_funcs(addon_map: dict) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    funcs: dict[tuple[str, str], str] = {}
    for src, dest in addon_map["files"].items():
        parts = src.split("/")
        if len(parts) >= 4 and parts[0] == "addons" and parts[2] == "functions":
            base = parts[-1]
            if base.startswith("fnc_") and base.endswith(".sqf"):
                funcs[(parts[1], base[4:-4])] = dest
    gvars = {
        name: dest
        for name, dest in addon_map["symbols"].items()
        if name.startswith("aee_")
    }
    return funcs, gvars


def build_stringtable(
    settings_map: dict, addons: set[str]
) -> dict[tuple[str, str], str]:
    table: dict[tuple[str, str], str] = {}
    for old, new in settings_map["settings"].items():
        if old == new:
            continue
        old_parts = module_of(old, addons)
        new_parts = module_of(new, addons)
        if old_parts and new_parts and old_parts[1] == new_parts[1]:
            table[(old_parts[0], old_parts[1])] = new_parts[0]
    return table


class Rewriter:
    def __init__(self, rules: Rules, enabled: set[str]) -> None:
        self.enabled = enabled
        self.funcs = rules.funcs
        self.vars = rules.vars
        self.strrules = rules.stringtable

        path = [r for r in rules.path if r.dest in enabled]
        self.prefix = _compile(
            [(r.pattern, r.replacement) for r in path if r.is_prefix], prefix=True
        )
        self.file = _compile(
            [(r.pattern, r.replacement) for r in path if not r.is_prefix], prefix=False
        )

        setting = [s for s in rules.setting if s.dest in enabled]
        self.setting = _compile([(s.old, s.new) for s in setting], prefix=False)

    def rewrite(self, text: str) -> str:
        text = _SYM_RE.sub(self._symbol, text)
        if self.prefix is not None:
            regex, lookup = self.prefix
            text = regex.sub(lambda m: lookup[m.group(0)], text)
        if self.file is not None:
            regex, lookup = self.file
            text = regex.sub(lambda m: lookup[m.group(0)], text)
        if self.setting is not None:
            regex, lookup = self.setting
            text = regex.sub(lambda m: lookup[m.group(0)], text)
        if self.strrules:
            text = _STR_RE.sub(self._stringtable, text)
        return text

    def _symbol(self, match: re.Match[str]) -> str:
        kind, ws1, component, sep, name, ws2 = match.groups()
        if kind == "EGVAR":
            dest = self.vars.get(f"aee_{component}_{name}")
        else:
            dest = self.funcs.get((component, name))
        if dest and dest != component and dest in self.enabled:
            return f"{kind}({ws1}{dest}{sep}{name}{ws2})"
        return match.group(0)

    def _stringtable(self, match: re.Match[str]) -> str:
        token, leaf, suffix = match.groups()
        module = self.strrules.get((token.lower(), leaf))
        if not module or module not in self.enabled:
            return match.group(0)
        if token.isupper():
            new_token = module.upper()
        elif token.islower():
            new_token = module.lower()
        else:
            new_token = "_".join(word.capitalize() for word in module.split("_"))
        return f"STR_AEE_{new_token}_{leaf}_{suffix}"


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_s = rel.as_posix()
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel_s in SKIP_REL or rel_s.startswith(SKIP_PREFIXES):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield rel, path


def load_maps(root: Path) -> tuple[dict, dict]:
    with (root / ADDON_MAP_REL).open(encoding="utf-8") as handle:
        addon_map = json.load(handle)
    with (root / SETTINGS_MAP_REL).open(encoding="utf-8") as handle:
        settings_map = json.load(handle)
    return addon_map, settings_map


def build_rules(addon_map: dict, settings_map: dict, addons: set[str]) -> Rules:
    setting_rules = tuple(
        SettingRule(old, new, module_of(new, addons)[0])
        for old, new in settings_map["settings"].items()
        if old != new and module_of(new, addons)
    )
    funcs, gvars = build_funcs(addon_map)
    return Rules(
        path=tuple(build_path_rules(addon_map)),
        setting=setting_rules,
        funcs=funcs,
        vars=gvars,
        stringtable=build_stringtable(settings_map, addons),
    )


def run(root: Path, *, apply: bool, step: int | None, to: str | None) -> int:
    addon_map, settings_map = load_maps(root)
    addons = set(addon_map.get("target_addons", ())) | set(addon_map.get("addons", {}))
    enabled = existing_addons(root)
    if step is not None:
        enabled &= STEPS.get(step, frozenset())
    if to:
        enabled &= {to}

    rewriter = Rewriter(build_rules(addon_map, settings_map, addons), enabled)
    changed: list[tuple[str, int]] = []
    for rel, path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        new = rewriter.rewrite(text)
        if new == text:
            continue
        lines = sum(1 for a, b in zip(text.splitlines(), new.splitlines()) if a != b)
        changed.append((rel.as_posix(), lines))
        if apply:
            path.write_text(new, encoding="utf-8")

    verb = "applied" if apply else "pending"
    if not changed:
        print(
            f"rewrite_paths: no {verb} changes "
            f"({len(enabled)} destination addon(s) enabled)"
        )
        return 0
    for rel, lines in changed:
        print(f"  {verb}: {rel} ({lines} line(s))")
    total = sum(lines for _, lines in changed)
    print(f"rewrite_paths: {verb} {total} change(s) across {len(changed)} file(s)")
    return 0 if apply else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rewrite_paths.py",
        description="Rewrite the AEE tree from the compartmentalisation map.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="report pending changes and exit non-zero (default)",
    )
    mode.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument(
        "--step",
        type=int,
        choices=sorted(STEPS),
        help="apply only one of the nine migration steps",
    )
    parser.add_argument(
        "--to", metavar="ADDON", help="apply only the rules whose destination is ADDON"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (default: the tool's repo)",
    )
    args = parser.parse_args(argv)
    return run(args.root, apply=args.apply, step=args.step, to=args.to)


if __name__ == "__main__":
    sys.exit(main())
