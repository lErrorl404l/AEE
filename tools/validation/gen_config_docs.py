#!/usr/bin/env python3
"""Regenerate docs/wiki/chapters/configuration.qmd from the settings sources.

The settings sources are addons/*/initSettings.inc.sqf and their sibling
stringtable.xml.  A setting registers in one of two ways:

  1. an AEE_SETTING_* macro from addons/main/script_macros.hpp; or
  2. an explicit `[QGVAR(x), "TYPE", ..., ] call CBA_fnc_addSetting` block.

The tool parses both.  It must never drop a setting: a regression that
found fewer settings than the file already documents would silently truncate
the chapter, which is exactly what happened when only the explicit form was
parsed.  Write mode therefore refuses to remove a name the file already
lists unless --allow-removals is given.

Run from the repo root:

    python3 tools/validation/gen_config_docs.py            # write the file
    python3 tools/validation/gen_config_docs.py --check    # compare, no write

The output is deterministic.  Descriptions come from the stringtable and are
never invented.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
DOC = REPO / "docs/wiki/chapters/configuration.qmd"
PREFIX = "aee"

INTRO = (
    "All settings register with `CBA_fnc_addSetting` and appear in the "
    "CBA Settings menu under the **AEE** categories. Values marked "
    "*global* must match across all clients."
)

# Prose carried with the radio group.  It explains why the settings register
# only when a host radio mod is present.
RADIO_NOTE = (
    "This category registers only when ACRE2 or TFAR is loaded. The radio\n"
    "simulation feeds the ACRE2 and TFAR compat layers; without either host\n"
    "mod its settings and computed state have no consumer, so they are not\n"
    "registered."
)

# The exhaust plume publishes per-vehicle values, not CBA settings.  The
# table is documentation only and is carried forward verbatim.
EXHAUST_SECTION = """\
## AEE FX → Exhaust plume

Per-vehicle published values.  A mission or a mod sets these on a vehicle
object.  They are not CBA settings.

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `aee_exhaustTier` | STRING | unset | Tier override, one of `land`, `heli`, `jet`, `ab`. Wins over the class selection |
| `aee_exhaustAfterburner` | BOOL | unset | A truthy value selects the afterburner tier, because no verified config key distinguishes an afterburning jet from a dry one |
| `aee_enginePowerFraction` | NUMBER | unset | Engine power fraction in 0..1. Overrides the real reader and the declared idle |
| `aee_engineRatedPowerW` | NUMBER | `150000` | Rated engine power in watts for the derived ground load. Overrides the declared default |
| `aee_exhaustGasTempC` | NUMBER | unset | Measured exhaust gas temperature in Celsius. Overrides the class row |
| `aee_exhaustPlumeM` | NUMBER | unset | Measured plume depth in metres. Overrides the class row |

The class row comes from the tier table in `fnc_applyExhaustShimmer.sqf`,
and `fnc_calculateExhaustPlume.sqf` interpolates it from the engine power
fraction.  The endpoints are declared defaults and not measurements.  When
no published value is set, the power fraction comes from the real reader,
`collectiveRTD` for a helicopter and `throttleRTD` for fixed wing, which is
gated on the advanced helicopter flight model and is unavailable when it is
off.  A land vehicle and a gated-off client use the declared idle fraction.
"""

# The night-vision grain ceilings moved from optics to nightvision.  The old
# names are kept so a link to earlier documentation still resolves.
LEGACY_SECTION = """\
## AEE Optics → Intensity (historical)

The night-vision grain ceilings moved to the Night Vision addon and now
register as `aee_nightvision_nightGrainMax`, `aee_nightvision_rainGrainMax`
and `aee_nightvision_fogGrainMax`. The older names are kept here.

| Setting | Type | Default | Addon | Purpose |
|---|---|---|---|---|
| `aee_optics_nightGrainMax` | SLIDER | `0.7` | optics | Night noise floor, the perceived darkness of night vision |
| `aee_optics_rainGrainMax` | SLIDER | `0.4` | optics | Rain-on-eye noise at night |
| `aee_optics_fogGrainMax` | SLIDER | `0.15` | optics | Fog haze grain added to the night grain effect |
"""

_MACRO = re.compile(
    r"AEE_SETTING_(?P<kind>CHECKBOX_LOCAL|CHECKBOX|SLIDER)\s*\((?P<args>[^)]*)\)"
)
_ADD_SETTING = re.compile(r"call CBA_fnc_addSetting")
_QGVAR = re.compile(r"QGVAR\((\w+)\)")
_NAMES_IN_DOC = re.compile(r"`(aee_[A-Za-z0-9_]+)`")
_QUOTED = re.compile(r'"([^"]*)"')

Checkbox = "CHECKBOX"


@dataclass(frozen=True, slots=True)
class Setting:
    """One CBA setting, ready for the reference table."""

    name: str
    key: str
    stype: str
    category: str
    subcategory: str
    default: str
    is_global: bool
    addon: str
    description: str

    @property
    def group(self) -> str:
        if self.subcategory:
            return f"{self.category} → {self.subcategory}"
        return self.category


def strip_comments(text: str) -> str:
    """Remove // and /* */ comments, leaving string literals intact."""
    out: list[str] = []
    i = 0
    size = len(text)
    while i < size:
        char = text[i]
        if char == '"':
            end = i + 1
            while end < size and text[end] != '"':
                end += 2 if text[end] == "\\" else 1
            out.append(text[i : end + 1])
            i = end + 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = size if end == -1 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i)
            i = size if end == -1 else end + 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


def split_top_level(text: str) -> list[str]:
    """Split on commas that sit outside quotes and outside [] and {}."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quoted = False
    for char in text:
        if char == '"':
            quoted = not quoted
            current.append(char)
            continue
        if not quoted:
            if char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    parts.append("".join(current).strip())
    return [part for part in parts if part]


def unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def bracket_before(text: str, index: int) -> str | None:
    """Return the array body that closes just before the call at index."""
    end = index - 1
    while end >= 0 and text[end] in " \t\r\n":
        end -= 1
    if end < 0 or text[end] != "]":
        return None
    depth = 0
    cursor = end
    while cursor >= 0:
        if text[cursor] == "]":
            depth += 1
        elif text[cursor] == "[":
            depth -= 1
            if depth == 0:
                return text[cursor + 1 : end]
        cursor -= 1
    return None


def category_of(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if raw.startswith("["):
        names = _QUOTED.findall(raw)
        if len(names) >= 2:
            return names[0], names[1]
        return (names[0], "") if names else ("", "")
    return unquote(raw), ""


def explicit_default(stype: str, raw: str) -> str:
    """The stored value for an explicit block: the index for LIST and the
    middle value for SLIDER, the literal otherwise."""
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return raw
    parts = split_top_level(raw[1:-1])
    if stype == "SLIDER" and len(parts) >= 3:
        return parts[2]
    if stype == "LIST" and parts:
        return parts[-1]
    return raw


def macro_settings(addon: str, text: str) -> list[Setting]:
    """Settings registered by the AEE_SETTING_* macros."""
    found: list[Setting] = []
    for match in _MACRO.finditer(text):
        kind = match.group("kind")
        args = split_top_level(match.group("args"))
        if kind == "SLIDER" and len(args) == 7:
            key, category, subcategory, _mn, _mx, default, _step = args
            stype = "SLIDER"
        elif kind != "SLIDER" and len(args) == 4:
            key, category, subcategory, default = args
            stype = Checkbox
        else:
            continue
        found.append(
            Setting(
                name=f"{PREFIX}_{addon}_{key}",
                key=key,
                stype=stype,
                category=unquote(category),
                subcategory=unquote(subcategory),
                default=default.strip(),
                is_global=kind != "CHECKBOX_LOCAL",
                addon=addon,
                description="",
            )
        )
    return found


def explicit_settings(addon: str, text: str) -> list[Setting]:
    """Settings registered by an explicit CBA_fnc_addSetting block."""
    found: list[Setting] = []
    for match in _ADD_SETTING.finditer(text):
        body = bracket_before(text, match.start())
        if body is None:
            continue
        parts = split_top_level(body)
        if len(parts) < 6:
            continue
        name_match = _QGVAR.search(parts[0])
        if name_match is None:
            continue
        key = name_match.group(1)
        stype = unquote(parts[1])
        category, subcategory = category_of(parts[3])
        found.append(
            Setting(
                name=f"{PREFIX}_{addon}_{key}",
                key=key,
                stype=stype,
                category=category,
                subcategory=subcategory,
                default=explicit_default(stype, parts[4]),
                is_global=parts[5].strip() == "true",
                addon=addon,
                description="",
            )
        )
    return found


def parse_stringtable(path: Path) -> dict[str, str]:
    """Map a lower-case key ID to its English text."""
    table: dict[str, str] = {}
    if not path.exists():
        return table
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return table
    for key in tree.iter("Key"):
        key_id = key.get("ID", "")
        if not key_id:
            continue
        english = ""
        for child in key:
            if child.tag == "English":
                english = "".join(child.itertext())
        table[key_id.lower()] = " ".join(english.split())
    return table


def description_for(table: dict[str, str], key: str) -> str:
    """Look up <any component>_<key>_Description, ignoring component case.

    A few keys use a shortened stem (agsmAvailable binds AGSM, gsuitEquipped
    binds GSuit).  When the exact key is absent, match a stem that is a
    prefix of the setting name or the other way round.
    """
    lower = key.lower()
    suffix = f"_{lower}_description"
    for key_id, text in table.items():
        if key_id.startswith("str_aee_") and key_id.endswith(suffix):
            return text
    stem_end = len("_description")
    for key_id, text in table.items():
        if not (key_id.startswith("str_aee_") and key_id.endswith("_description")):
            continue
        stem = key_id[len("str_aee_") : -stem_end]
        stem = stem.rsplit("_", 1)[-1]
        if not stem:
            continue
        if lower.startswith(stem) or stem.startswith(lower):
            return text
    return ""


def collect_settings() -> list[Setting]:
    """Every CBA setting across every addon, deduplicated by name."""
    by_name: dict[str, Setting] = {}
    for init_path in sorted(ADDONS.rglob("initSettings.inc.sqf")):
        addon = init_path.parent.name
        text = strip_comments(init_path.read_text(encoding="utf-8"))
        table = parse_stringtable(init_path.parent / "stringtable.xml")
        for setting in macro_settings(addon, text) + explicit_settings(addon, text):
            if setting.name in by_name:
                continue
            by_name[setting.name] = Setting(
                name=setting.name,
                key=setting.key,
                stype=setting.stype,
                category=setting.category,
                subcategory=setting.subcategory,
                default=setting.default,
                is_global=setting.is_global,
                addon=setting.addon,
                description=description_for(table, setting.key),
            )
    return [by_name[name] for name in sorted(by_name)]


def cell(text: str) -> str:
    """A single-line markdown table cell."""
    return " ".join(text.split()).replace("|", "\\|")


def render(settings: list[Setting]) -> str:
    """Render the complete chapter.  Raises if a setting would be dropped."""
    groups: dict[str, list[Setting]] = {}
    for setting in settings:
        groups.setdefault(setting.group, []).append(setting)

    lines: list[str] = [
        "---",
        'title: "Configuration"',
        "---",
        "",
        "# Configuration {#sec-configuration}",
        "",
        INTRO,
        "",
    ]
    for group in sorted(groups, key=str.lower):
        rows = sorted(groups[group], key=lambda s: s.name)
        lines.append(f"## {group}")
        lines.append("")
        if group == ("AEE Radio → Link"):
            lines.append(RADIO_NOTE)
            lines.append("")
        lines.append("| Setting | Type | Default | Global | Addon | Purpose |")
        lines.append("|---|---|---|---|---|---|")
        for setting in rows:
            lines.append(
                f"| `{setting.name}` | {cell(setting.stype)} | "
                f"`{cell(setting.default)}` | "
                f"{'yes' if setting.is_global else 'no'} | {setting.addon} | "
                f"{cell(setting.description)} |"
            )
        lines.append("")
    lines.append(EXHAUST_SECTION)
    lines.append("")
    lines.append(LEGACY_SECTION)

    rendered = "\n".join(lines).rstrip("\n") + "\n"
    emitted = _NAMES_IN_DOC.findall(rendered)
    if len(emitted) < len(settings):
        raise RuntimeError(
            f"refusing to emit: {len(emitted)} names for {len(settings)} settings"
        )
    return rendered


def names_in_doc(text: str) -> set[str]:
    return set(_NAMES_IN_DOC.findall(text))


def check(path: Path = DOC) -> int:
    """Return 0 when the file equals the generated text, 1 otherwise."""
    rendered = render(collect_settings())
    if not path.exists():
        print(f"missing: {path}")
        return 1
    if path.read_text(encoding="utf-8") != rendered:
        print(f"stale: {path}")
        return 1
    print(f"fresh: {path}")
    return 0


def write(path: Path = DOC, allow_removals: bool = False) -> int:
    rendered = render(collect_settings())
    if path.exists() and not allow_removals:
        missing = names_in_doc(path.read_text(encoding="utf-8")) - names_in_doc(
            rendered
        )
        if missing:
            print(
                "refusing to write: the new document would drop "
                f"{len(missing)} documented name(s): {', '.join(sorted(missing))}"
            )
            return 1
    path.write_text(rendered, encoding="utf-8")
    print(f"wrote {len(collect_settings())} settings to {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    parser.add_argument(
        "--allow-removals",
        action="store_true",
        help="permit a write that removes an already-documented name",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()
    return write(allow_removals=args.allow_removals)


if __name__ == "__main__":
    sys.exit(main())
