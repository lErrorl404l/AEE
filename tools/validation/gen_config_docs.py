#!/usr/bin/env python3
"""Regenerate docs/wiki/chapters/configuration.qmd from the initSettings files.

Scans addons/*/initSettings.inc.sqf + stringtable.xml and emits a settings
reference table grouped by CBA category. Run from the repo root:

    python3 tools/validation/gen_config_docs.py

Output is written to docs/wiki/chapters/configuration.qmd.
"""

import glob
import os
import re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def addon_titlecase(addon):
    """addons/compat_ace3 -> ACE3; addons/compat_realweather -> Compat_RealWeather."""
    name = addon.removeprefix("addons/")
    if name == "compat_ace3":
        return "ACE3"
    if name == "compat_acm":
        return "ACM"
    if name == "compat_kat":
        return "KAT"
    if name == "compat_acre2":
        return "ACRE2"
    if name == "compat_tfar":
        return "TFAR"
    if name == "compat_realweather":
        return "Compat_RealWeather"
    return name.title().replace("_", "")


def parse_stringtable(path):
    """Map Key ID -> description text."""
    out = {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return out
    for key in tree.iter("Key"):
        kid = key.get("ID", "")
        eng = None
        for child in key:
            if child.tag == "English":
                eng = child.text or ""
        out[kid] = eng
    return out


def parse_settings(path):
    """Extract (name, type, category, default, global) tuples from an initSettings file."""
    settings = []
    with open(path) as f:
        content = f.read()
    # Each block is [ QGVAR(name), "TYPE", [LLSTRING.., LLSTRING..], "category"/[cat,sub], default, global, {} ]
    blocks = re.findall(
        r"\[\s*QGVAR\(([a-zA-Z0-9_]+)\),\s*\"([A-Z]+)\",\s*\[LLSTRING\([^\]]+\)\],\s*(\[.*?\]|\"[^\"]*\"),\s*((?:\[[^\]]*\]|[^\n,]+)),",
        content,
        re.DOTALL,
    )
    for name, stype, cat_raw, default in blocks:
        cat_raw = cat_raw.strip()
        if cat_raw.startswith("["):
            m = re.findall(r'"([^"]+)"', cat_raw)
            cat = " → ".join(m) if m else cat_raw
        else:
            cat = cat_raw.strip('"')
        # Slider defaults come as [min, max, default, decimals] — show only the default value
        default = default.strip()
        dm = re.match(r"\[([^\]]*)\]", default)
        if dm and stype == "SLIDER":
            parts = [p.strip() for p in dm.group(1).split(",")]
            if len(parts) >= 3:
                default = parts[2]
        settings.append((name, stype, cat, default))
    return settings


def main():
    out = []
    out.append("---")
    out.append('title: "Configuration"')
    out.append("---")
    out.append("")
    out.append("# Configuration {#sec-configuration}")
    out.append("")
    out.append(
        "All settings register with `CBA_fnc_addSetting` and appear in the "
        "CBA Settings menu under the **AEE** categories. Values marked *global* "
        "must match across all clients."
    )
    out.append("")

    all_settings = []
    for init_path in sorted(
        glob.glob(os.path.join(ROOT, "addons", "*", "initSettings.inc.sqf"))
    ):
        addon_dir = os.path.dirname(init_path)
        addon = os.path.basename(addon_dir)
        str_path = os.path.join(addon_dir, "stringtable.xml")
        st = parse_stringtable(str_path)
        settings = parse_settings(init_path)
        for name, stype, cat, default in settings:
            desc_key = f"STR_AEE_{addon_titlecase(addon)}_{name}_Description"
            desc = st.get(desc_key, "")
            all_settings.append((cat, addon, name, stype, default, desc))

    # Group by category, preserving category sort order
    cats = {}
    for cat, addon, name, stype, default, desc in all_settings:
        cats.setdefault(cat, []).append((addon, name, stype, default, desc))

    for cat in sorted(cats):
        out.append(f"## {cat}")
        out.append("")
        out.append("| Setting | Type | Default | Addon | Purpose |")
        out.append("|---|---|---|---|---|")
        for addon, name, stype, default, desc in cats[cat]:
            out.append(
                f"| `aee_{addon.removeprefix('addons/')}_{name}` | {stype} | `{default}` | {addon.removeprefix('addons/')} | {desc} |"
            )
        out.append("")

    with open(os.path.join(ROOT, "docs/wiki/chapters/configuration.qmd"), "w") as f:
        f.write("\n".join(out))
    print(f"Wrote {len(all_settings)} settings across {len(cats)} categories")


if __name__ == "__main__":
    main()
