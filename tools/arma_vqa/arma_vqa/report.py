"""Text / Markdown / JSON reporting."""
from __future__ import annotations

import json
from collections import defaultdict

from .analyze import Finding, Result
from .catalog import RULES, SEV_ORDER

_SEV_TAG = {"error": "ERROR", "warning": "WARN ", "info": "info "}
_COLOR = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
_RESET = "\033[0m"


def filter_findings(findings: list[Finding], min_sev: str) -> list[Finding]:
    m = SEV_ORDER[min_sev]
    return [f for f in findings if SEV_ORDER[f.sev] >= m]


def summary_line(res: Result, findings: list[Finding]) -> str:
    c = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        c[f.sev] += 1
    return f"{len(res.files)} files scanned: {c['error']} errors, {c['warning']} warnings, {c['info']} info" + (
        f" ({res.suppressed} suppressed by vqa-ignore)" if res.suppressed else "")


def to_text(res: Result, findings: list[Finding], sims: list[dict], color: bool = False) -> str:
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_file[f.file].append(f)
    out: list[str] = []
    for fn in sorted(by_file):
        out.append(fn)
        for f in sorted(by_file[fn], key=lambda x: (x.line, -SEV_ORDER[x.sev])):
            tag = _SEV_TAG[f.sev]
            if color:
                tag = f"{_COLOR[f.sev]}{tag}{_RESET}"
            loc = f"{f.line:>4}" if f.line else "   -"
            out.append(f"  {loc}  {tag} {f.rule:<6} {f.message}  [{f.prov}]")
        out.append("")
    if sims:
        out.append("Offline render scenarios")
        for s in sims:
            if s["kind"] == "map":
                c = s["metrics"]["colorGrid"]["lines"]
                out.append(f"  - {s['scenario']}: grid line contrast " + " / ".join('-' if v is None else f'{v:.2f}' for v in c) + " (land / sea / forest / 2 satellite stand-ins)")
                continue
            if s["kind"] == "ti":
                m = s["metrics"]
                out.append(f"  - {s['scenario']}: window {m['output_low']:.2f}..{m['output_high']:.2f}, ~{m['grey_levels']} grey levels"
                           + (f"  -> {s['image']}" if s.get("image") else ""))
            else:
                m = s["metrics"]
                out.append(f"  - {s['scenario']}: levels {m['levels_remaining']}/256, clipL {m['clip_low_pct']:.0f}%, clipH {m['clip_high_pct']:.0f}%, "
                           f"lumaShift {m['mean_luma_shift']:+.2f}, sat x{m['saturation_ratio']:.2f}, contrast x{m['contrast_ratio']:.2f}"
                           + (f"  -> {s['image']}" if s.get("image") else ""))
        out.append("")
    out.append(summary_line(res, findings))
    out.append("Provenance tags: wiki / wiki-note / community / inferred / heuristic / model. Run `explain RULEID` for details.")
    if res.layers:
        out.append(f"{len(res.layers)} UI layer(s) in use - `layers` prints who shows what where.")
    if res.grids:
        out.append(f"{len(res.grids)} terrain grid(s) - `grid` prints the numbers each zoom level shows.")
    return "\n".join(out)


def to_markdown(res: Result, findings: list[Finding], sims: list[dict]) -> str:
    out = ["# Arma 3 visual QA report", "", summary_line(res, findings), ""]
    for sev in ("error", "warning", "info"):
        items = [f for f in findings if f.sev == sev]
        if not items:
            continue
        out += [f"## {sev.capitalize()} ({len(items)})", "", "| Rule | Location | Message | Source |", "|---|---|---|---|"]
        for f in items:
            loc = f"`{f.file}:{f.line}`" if f.line else f"`{f.file}`"
            msg = f.message.replace("|", "\\|")
            out.append(f"| {f.rule} | {loc} | {msg} | {f.prov} |")
        out.append("")
    if sims:
        out += ["## Offline render scenarios", ""]
        for s in sims:
            out.append(f"- **{s['scenario']}**" + (f" - `{s['image']}`" if s.get("image") else ""))
        out.append("")
    return "\n".join(out)


def to_json(res: Result, findings: list[Finding], sims: list[dict]) -> str:
    return json.dumps({
        "summary": res.counts() | {"files": len(res.files), "suppressed": res.suppressed},
        "findings": [f.to_dict() for f in findings],
        "simulation": sims,
        "layers": res.layers,
        "grids": res.grids,
    }, indent=2, default=str)


def explain(rule: str) -> str:
    r = RULES.get(rule.upper())
    if not r:
        return f"unknown rule {rule}. Known: {', '.join(sorted(RULES))}"
    return (f"{rule.upper()}  {r['title']}\n"
            f"  default severity : {r['sev']}\n"
            f"  provenance       : {r['prov']}\n"
            f"  why              : {r['why']}\n"
            + (f"  source           : {r['url']}\n" if r['url'] else ""))
