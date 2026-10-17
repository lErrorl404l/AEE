"""Command line interface."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .analyze import Analyzer, Finding
from .catalog import RULES, SEV_ORDER
from .report import explain, filter_findings, summary_line, to_json, to_markdown, to_text
from .rules import load_rules
from .sqf import UNKNOWN, Evaluator, tokenize


def _parse_array(text: str):
    lx = tokenize(text)
    v = Evaluator(lambda n, i: UNKNOWN).eval(lx.toks, -1)
    if not isinstance(v, list):
        raise SystemExit(f"could not parse '{text}' as an SQF array literal")
    return v


def cmd_scan(a) -> int:
    from . import sim

    rules = load_rules(a.rules)
    vanilla = set()
    if a.vanilla_classes:
        with open(a.vanilla_classes, encoding="utf-8") as f:
            vanilla = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
    an = Analyzer(rules, vanilla, set(a.ignore or []))
    res = an.scan(a.path)
    sims: list[dict] = []
    if not a.no_sim:
        from . import mapview

        cal = sim.load_calibration(a.calibration)
        scs = sim.build_scenarios(res, rules)
        sims, sf = sim.run_scenarios(scs, rules, cal, a.sim_out)
        msum, mf = mapview.preview_scenarios(res, rules, cal, a.sim_out)
        for e in msum:
            sims.append({"scenario": f"map: {e['style']}", "kind": "map", "metrics": e["configured"], "image": None,
                         "assumed": e["assumed"], "through": [x["scenario"] for x in e["scenarios"]]})
        sf = list(sf) + list(mf)
        ign = {i.upper() for i in (a.ignore or [])}
        seen = set()
        for rule, sev, msg, prov, origin in sf:
            if rule in ign or (rule, msg) in seen:
                continue
            seen.add((rule, msg))
            rel = os.path.relpath(origin, res.root) if origin not in ("*", "") and os.path.isabs(origin) else (origin if origin != "*" else "(whole mod)")
            res.findings.append(Finding(rule, sev, rel, 0, msg, prov))
    findings = filter_findings(res.findings, a.min_severity)
    if a.format == "json":
        out = to_json(res, findings, sims)
    elif a.format == "md":
        out = to_markdown(res, findings, sims)
    else:
        out = to_text(res, findings, sims, color=sys.stdout.isatty() and not a.output)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(f"wrote {a.output}\n{summary_line(res, findings)}")
    else:
        print(out)
    if a.fail_on == "none":
        return 0
    worst = max((SEV_ORDER[f.sev] for f in res.findings), default=-1)
    return 1 if worst >= SEV_ORDER[a.fail_on] else 0


def cmd_limits(a) -> int:
    rules = load_rules(a.rules)
    pp = rules.pp
    print("POST-PROCESS EFFECTS  (base priority = conventional slot; higher = applied later)\n")
    names = [a.effect] if a.effect else list(pp["effects"])
    for n in names:
        key = rules.canon.get(n.lower())
        if not key:
            print(f"unknown effect {n}; known: {', '.join(pp['effects'])}")
            return 2
        e = pp["effects"][key]
        bp = e["base_priority"]
        print(f"{key}   base priority: {bp if bp is not None else 'n/a (advanced - ppEffectAdjust by name only, no commit needed)'}   params: {e['min_params']}"
              + ("" if e["min_params"] == e["max_params"] else f"-{e['max_params']}"))
        for p in e["params"]:
            rng = ""
            if "min" in p or "max" in p:
                rng = f"range {p.get('min', '-inf')}..{p.get('max', '+inf')}"
            elif p["kind"] == "color":
                rng = "comp " + ", ".join(f"{lo}..{hi}" for lo, hi in p["comp"])
            print(f"    {p['name']:<24} {p['kind']:<8} default {json.dumps(p['default']):<28} {rng}  [{p.get('prov', 'wiki')}]")
        for note in e.get("notes", []):
            print(f"    note: {note}")
        print()
    if not a.effect:
        tp = rules.tc["ti_parameters"]
        print("THERMAL IMAGING (setTIParameter / getTIParameters)")
        for k, v in tp.items():
            if k.startswith("_"):
                continue
            print(f"    {k:<18} default {v['default']}  {v['desc']}")
        print(f"    {tp['_note']}")
        print("\nTI MODES (setCamUseTI)")
        for k, v in rules.tc["ti_modes"].items():
            if k.startswith("_"):
                continue
            print(f"    {k}  {v}")
        print("\nAPERTURE   setAperture: <=0 auto, effect saturates ~100 (guide: ~50 outdoor day, ~30 indoor, <20 very bright)")
        print("           setApertureNew [min, std, max, stdLum] or [-1]; setAperture overrides it when HDR is on")
        print("\nPiP EFFECTS (setPiPEffect)  0 normal, 1 NVG, 2 TI, 3 colour correction (8 values), 7/8 alt TI, 9..70 alt TI 3..64")
        print("\nQA thresholds (heuristic, editable in rules/post_process.json):")
        for k, v in rules.thresholds.items():
            print(f"    {k:<32} {v}")
    return 0


def cmd_explain(a) -> int:
    if a.rule == "all":
        for r in sorted(RULES):
            print(explain(r))
    else:
        print(explain(a.rule))
    return 0


def cmd_sim(a) -> int:
    from . import sim

    rules = load_rules(a.rules)
    key = rules.canon.get(a.effect.lower())
    if not key:
        print(f"unknown effect {a.effect}")
        return 2
    cal = sim.load_calibration(a.calibration)
    params = _parse_array(a.params)
    from .rules import validate_params

    for rule, sev, msg, prov in validate_params(rules, key, params, "handle"):
        print(f"  {sev:<7} {rule} {msg}  [{prov}]")
    r = sim.quick_render(key, params, rules, cal, a.out)
    if not r["simulated"]:
        print(f"{key} cannot be simulated offline (needs depth/sun data)")
    for rule, sev, msg, prov in r["findings"]:
        print(f"  {sev:<7} {rule} {msg}")
    m = r["metrics"]
    print(f"levels {m['levels_remaining']}/256  clipL {m['clip_low_pct']:.0f}%  clipH {m['clip_high_pct']:.0f}%  lumaShift {m['mean_luma_shift']:+.2f}  "
          f"sat x{m['saturation_ratio']:.2f}  contrast x{m['contrast_ratio']:.2f}\nwrote {a.out}")
    return 0


def cmd_ti(a) -> int:
    from . import sim

    scene = sim.make_thermal_scene()
    panels = [("default (0.1 / 0.8) WHOT", sim.render_thermal(scene, 0.1, 0.8, 0)),
              (f"Start {a.start:g} Width {a.width:g} WHOT", sim.render_thermal(scene, a.start, a.width, 0))]
    for m in a.modes:
        panels.append((f"same, mode {m}", sim.render_thermal(scene, a.start, a.width, m)))
    tm = sim.thermal_metrics(a.start, a.width)
    lines = [f"output window {tm['output_low']:.2f}..{tm['output_high']:.2f}  grey levels ~{tm['grey_levels']}  "
             f"clipped top {tm['thermal_range_clipped_top_pct']:.0f}%  bottom {tm['thermal_range_clipped_bottom_pct']:.0f}%"]
    sim.compose_sheet("thermal output range", panels, lines).save(a.out)
    print(lines[0] + f"\nwrote {a.out}")
    return 0


def cmd_calibrate(a) -> int:
    from . import sim

    cal = sim.load_calibration(a.calibration)
    pairs = []
    for before, after, params in a.pair:
        b, f = sim.load_pair(before, after)
        pairs.append((b, f, _parse_array(params)))
    if a.effect == "ColorCorrections":
        ranked = sim.fit_color_corrections(pairs, cal)
        keys = ("cc_model", "cc_pivot", "cc_brightness")
    else:
        ranked = sim.fit_dynamic_blur(pairs, cal)
        keys = ("blur_sigma_per_unit",)
    print(f"{len(pairs)} screenshot pair(s), effect {a.effect}. Mean absolute pixel error per candidate (0 = identical, 1 = opposite):")
    for r in ranked[:8]:
        print("  " + f"{r['error']:.4f}  " + "  ".join(f"{k}={r[k]}" for k in keys if r.get(k) is not None))
    best = ranked[0]
    note = ""
    if best["error"] > a.max_error:
        note = (f"\nWARNING: best error {best['error']:.3f} is above {a.max_error}. None of the candidate models reproduces these "
                "screenshots. Likely causes: other effects or HDR/tone-mapping in the 'after' shot, a moving scene between shots, "
                "or the real maths differs from every candidate. Do not trust the fitted values for absolute numbers.")
    if len(ranked) > 1 and ranked[1]["error"] - best["error"] < 0.002:
        note += "\nNOTE: the top two candidates are almost tied; capture another pair with different parameters to tell them apart."
    out = {k: best[k] for k in keys if best.get(k) is not None}
    out["_fit"] = {"effect": a.effect, "pairs": len(pairs), "mean_abs_error": round(best["error"], 5)}
    if a.out:
        merged = {}
        if os.path.exists(a.out):
            with open(a.out, encoding="utf-8") as f:
                merged = json.load(f)
        merged.update({k: v for k, v in out.items() if k != "_fit"})
        merged.setdefault("_fit", {})[a.effect] = out["_fit"]
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        print(f"wrote {a.out}  (use it with: scan ... --calibration {a.out})")
    print(note.strip() if note else "")
    return 0


def _scan_quiet(a) -> "Analyzer":
    rules = load_rules(getattr(a, "rules", None))
    an = Analyzer(rules)
    an.scan(a.path)
    return an


def cmd_layers(a) -> int:
    """The UI layer table: which script puts what on which cut/title layer."""
    an = _scan_quiet(a)
    res = an.res
    if a.format == "json":
        print(json.dumps(res.layers, indent=2, default=str))
        return 0
    if not res.layers:
        print("no cutRsc / cutText / cutObj / titleRsc / titleText calls found")
        return 0
    print("UI LAYERS  (cut* layers: 0 is the back-most; named layers are numbered in order of first use at runtime)\n")
    over_map = []
    for row in res.layers:
        print(f"{row['layer']}   [{row['kind']}]")
        for u in row["uses"]:
            bits = [u["what"], u["cmd"]]
            if u["resource"]:
                bits.append(f"\"{u['resource']}\"")
            if u["effect"]:
                bits.append(u["effect"])
            if u["speed"] is not None:
                bits.append(f"speed {u['speed']:g}")
            sm = u["showInMap"]
            if u["what"] == "show":
                bits.append("hidden in map" if sm is False else ("shown over the map" if sm else "showInMap unknown"))
                if u["drawOverHUD"] is False:
                    bits.append("under the HUD")
            print("    " + "  ".join(bits) + f"   {u['at']}")
            if u["what"] == "show" and sm is not False:
                over_map.append((row["layer"], u))
        print()
    if over_map:
        print(f"{len(over_map)} show command(s) stay visible when the map is opened (showInMap is true or default); pass false to hide them there.")
    print("Not known (wiki silent): how title* resources stack against cut* layers, and whether a string layer and a BIS_fnc_rscLayer layer of the same name are one layer.")
    return 0


def cmd_grid(a) -> int:
    """What the terrain's map grid will print: label ranges and corner references per zoom class."""
    from . import mapview

    rules = load_rules(getattr(a, "rules", None))
    an = Analyzer(rules)
    res = an.scan(a.path)
    gm = [g for g in res.grids if not a.world or g["world"].lower() == a.world.lower()]
    if a.format == "json":
        print(json.dumps(gm, indent=2, default=str))
        return 0
    if not gm:
        print("no CfgWorlds >> <world> >> Grid class found" + (f" for {a.world}" if a.world else ""))
        return 0
    for g in gm:
        print(f"{g['world']}   mapSize {g['mapSize']}   offsetX {g['offsetX']}   offsetY {g['offsetY']}   ({os.path.relpath(g['file'], res.root)})")
        for z in g["zooms"]:
            head = f"  {z['name']:<6} zoomMax {z['zoomMax']!s:<8} step {z['stepX']}/{z['stepY']}  format {z['formatX']}/{z['formatY']}"
            if z.get("inherits"):
                head += f"  (inherits {z['inherits']})"
            print(head)
            if "corners" in z:
                c = z["corners"]
                print(f"         labels X {z['labelsX'][0]}..{z['labelsX'][1]}  Y {z['labelsY'][0]}..{z['labelsY'][1]}   SW {c['SW']}   SE {c['SE']}   NW {c['NW']}   NE {c['NE']}   centre {c['centre']}")
        print()
    print("Label arithmetic is the community BIS_fnc_gridToPos conversion (posX = offsetX + stepX*gridX; posY = mapSize - offsetY - stepY*gridY), inverted. It is not read from the engine.")
    if a.png:
        models = [m for m in res.grid_models if not a.world or m.world.lower() == a.world.lower()]
        mapview.grid_sheet(models[0], rules, a.png, a.zoom)
        print(f"wrote {a.png}")
    return 0


def cmd_map(a) -> int:
    from . import mapview, sim

    rules = load_rules(getattr(a, "rules", None))
    an = Analyzer(rules)
    res = an.scan(a.path)
    cal = sim.load_calibration(a.calibration)
    if a.zoom:
        cal["map_zoom"] = a.zoom
    msum, mf = mapview.preview_scenarios(res, rules, cal, a.out, limit=a.limit)
    if not res.map_styles:
        print("no map control (RscMapControl-like class) found in the scanned configs")
        return 0
    if not msum:
        print("map controls found, but none sets colorGrid / colorGridMap, so there is nothing to preview")
        return 0
    state = {None: "unknown (map findings stay info)", True: "yes", False: "no"}[cal.get("pp_on_map")]
    print(f"post-process applied to the map screen: {state}\n")
    for e in msum:
        c = e["configured"]["colorGrid"]
        print(f"{e['style']}   labels: {e['labels']}" + (f"   defaults assumed for: {', '.join(e['assumed'])}" if e["assumed"] else ""))
        print("   grid line contrast  " + "  ".join(f"{n.split(' (')[0]}: {'-' if v is None else f'{v:.2f}'}" for n, v in zip(mapview.BAND_NAMES, c["lines"])))
        print("   grid number contrast " + "  ".join(f"{n.split(' (')[0]}: {'-' if v is None else f'{v:.2f}'}" for n, v in zip(mapview.BAND_NAMES, c["text"])))
        for sc in e["scenarios"]:
            m = sc["metrics"]["colorGrid"]
            print(f"   through {sc['scenario']}: lines " + "  ".join('-' if v is None else f'{v:.2f}' for v in m["lines_pp"]))
    print()
    for rule, sev, msg, prov, origin in mf:
        print(f"  {sev:<7} {rule} {msg}  [{prov}]")
    print(f"\nwrote previews to {a.out}")
    return 0


def cmd_map_pp(a) -> int:
    """Does post-process change the map screen? Compare two screenshots of the same map view, effect off and on."""
    from . import sim

    b, f = sim.load_pair(a.before, a.after)
    mae = sim._mae(b, f)
    applies = mae > a.threshold
    print(f"mean absolute difference between the two screenshots: {mae:.4f}   (threshold {a.threshold})")
    if applies:
        print("=> the effect changed the map screenshot: post-process IS applied to the map screen. Map findings will use their normal severity.")
    else:
        print("=> no measurable change: post-process does NOT appear to be applied to the map screen. MAPSIM002 will be suppressed.")
    print("Make sure both shots show the same map position/zoom and that only the post-process effect differs; any other change counts as a difference.")
    if a.out:
        merged = {}
        if os.path.exists(a.out):
            with open(a.out, encoding="utf-8") as fh:
                merged = json.load(fh)
        merged["pp_on_map"] = bool(applies)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=2)
        print(f"wrote pp_on_map={str(bool(applies)).lower()} to {a.out}  (use it with: scan ... --calibration {a.out})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arma_vqa", description="Offline visual QA for Arma 3 mods (post-process, thermal, NVG, aperture, PiP).")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="scan one or more mod folders (or files); several paths are analysed together so cross-mod priority collisions and class references are visible")
    s.add_argument("path", nargs="+")
    s.add_argument("--format", choices=["text", "json", "md"], default="text")
    s.add_argument("--min-severity", choices=["info", "warning", "error"], default="info")
    s.add_argument("--fail-on", choices=["error", "warning", "none"], default="error", help="exit code 1 when a finding of this severity exists")
    s.add_argument("--sim-out", metavar="DIR", help="write rendered preview sheets (PNG) to DIR")
    s.add_argument("--no-sim", action="store_true", help="skip the offline render model")
    s.add_argument("--calibration", metavar="JSON")
    s.add_argument("--rules", metavar="DIR", help="alternate rules directory")
    s.add_argument("--vanilla-classes", metavar="FILE", help="text file with extra known class names (CfgOpticsEffect, RscTitles, CfgTitles)")
    s.add_argument("--ignore", nargs="*", metavar="RULE")
    s.add_argument("--output", "-o", metavar="FILE")
    s.set_defaults(fn=cmd_scan)

    l = sub.add_parser("limits", help="print documented limits, defaults and priorities")
    l.add_argument("effect", nargs="?")
    l.add_argument("--rules")
    l.set_defaults(fn=cmd_limits)

    e = sub.add_parser("explain", help="explain a rule id (or 'all')")
    e.add_argument("rule")
    e.set_defaults(fn=cmd_explain)

    m = sub.add_parser("sim", help="render one effect with given params, e.g. sim ColorCorrections \"[1,0.4,0,[0,0,0,0],[1,1,1,0],[1,1,1,0]]\"")
    m.add_argument("effect")
    m.add_argument("params")
    m.add_argument("--out", default="sim.png")
    m.add_argument("--calibration")
    m.add_argument("--rules")
    m.set_defaults(fn=cmd_sim)

    c = sub.add_parser("calibrate", help="fit the offline renderer to real in-game screenshots (before/after pairs)")
    c.add_argument("--effect", choices=["ColorCorrections", "DynamicBlur"], default="ColorCorrections")
    c.add_argument("--pair", nargs=3, action="append", required=True, metavar=("BEFORE.png", "AFTER.png", "PARAMS"),
                   help="screenshot without the effect, screenshot with it, and the ppEffectAdjust array used, e.g. \"[1,1.3,0,[0,0,0,0],[1,1,1,0.5],[0.299,0.587,0.114,0]]\". Repeat with different params.")
    c.add_argument("--out", metavar="JSON", help="write/merge the fitted values into this calibration file")
    c.add_argument("--calibration", metavar="JSON", help="start from an existing calibration file")
    c.add_argument("--max-error", type=float, default=0.06, help="warn when the best candidate is worse than this mean abs error")
    c.set_defaults(fn=cmd_calibrate)

    ly = sub.add_parser("layers", help="table of cutRsc / cutText / cutObj / titleRsc layers: who shows what where, and what stays visible over the map")
    ly.add_argument("path", nargs="+")
    ly.add_argument("--format", choices=["text", "json"], default="text")
    ly.add_argument("--rules")
    ly.set_defaults(fn=cmd_layers)

    gr = sub.add_parser("grid", help="what the terrain's map Grid class prints: label ranges and corner references per zoom class")
    gr.add_argument("path", nargs="+")
    gr.add_argument("--world", help="only this CfgWorlds class")
    gr.add_argument("--zoom", help="zoom class for --png (default: finest)")
    gr.add_argument("--png", metavar="FILE", help="draw a preview with the real labels")
    gr.add_argument("--format", choices=["text", "json"], default="text")
    gr.add_argument("--rules")
    gr.set_defaults(fn=cmd_grid)

    mp = sub.add_parser("map", help="render a synthetic map from the mod's map-control colours, measure grid line/number visibility, optionally through its post-process stack")
    mp.add_argument("path", nargs="+")
    mp.add_argument("--out", default="map_preview", metavar="DIR")
    mp.add_argument("--zoom", help="grid zoom class for the labels (default: finest)")
    mp.add_argument("--limit", type=int, default=3, help="how many post-process scenarios to run")
    mp.add_argument("--calibration", metavar="JSON")
    mp.add_argument("--rules")
    mp.set_defaults(fn=cmd_map)

    mpp = sub.add_parser("map-pp", help="decide from two screenshots whether post-process is applied to the map screen")
    mpp.add_argument("--before", required=True, metavar="PNG", help="map screenshot with the effect off")
    mpp.add_argument("--after", required=True, metavar="PNG", help="the same map view with the effect on")
    mpp.add_argument("--threshold", type=float, default=0.01)
    mpp.add_argument("--out", metavar="JSON", help="record pp_on_map in this calibration file")
    mpp.set_defaults(fn=cmd_map_pp)

    t = sub.add_parser("ti", help="preview a setTIParameter output window")
    t.add_argument("--start", type=float, default=0.1)
    t.add_argument("--width", type=float, default=0.8)
    t.add_argument("--modes", type=int, nargs="*", default=[1, 2])
    t.add_argument("--out", default="ti.png")
    t.set_defaults(fn=cmd_ti)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except BrokenPipeError:  # pragma: no cover
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
