"""Static analysis: links handles to effects, builds an effect model, runs the rules."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from . import mapcfg, sqf, ui
from .catalog import RULES
from .config_cpp import CfgClass, parse_config, walk
from .rules import Rules, defaults_of, load_rules, validate_params
from .sqf import UNKNOWN, Call, FileFacts

SKIP_DIRS = {".git", ".hg", ".svn", ".hemttout", "node_modules", "__pycache__", ".vscode", ".idea", "venv", ".venv"}
SQF_EXT = {".sqf"}
CFG_EXT = {".cpp", ".hpp", ".h", ".ext"}
WAIT_IDS = {"sleep", "uisleep", "waituntil", "ppeffectcommitted", "spawn", "execvm", "canceltimer"}
NVG_WORDS = ("nvg", "nightvision", "night_vision", "currentvisionmode", "visionmode", "camusenvg")
COMPARE_OPS = {"<", ">", "<=", ">=", "==", "!="}
# vanilla optics effects follow OpticsBlurN / OpticsCHAberaN (the wiki's own example uses ...5)
_VANILLA_OPTICS_RE = re.compile(r"^Optics(Blur|CHAbera)\d+$", re.I)
CMP_IDS = {"isequalto", "isnotequalto"}
_AMBIG = object()


@dataclass
class Finding:
    rule: str
    sev: str
    file: str
    line: int
    message: str
    prov: str = ""

    def to_dict(self) -> dict:
        d = {"rule": self.rule, "severity": self.sev, "file": self.file, "line": self.line,
             "message": self.message, "provenance": self.prov}
        d["title"] = RULES.get(self.rule, {}).get("title", "")
        d["url"] = RULES.get(self.rule, {}).get("url", "")
        return d


@dataclass
class Op:
    file: str
    line: int
    tok: int
    value: Any = None
    syntax: str = "handle"


@dataclass
class Instance:
    uid: int
    kind: str  # handle | named | config
    effect_raw: Any
    effect: str | None
    priority: Any
    file: str
    line: int
    tok: int = -1
    retry: bool = False
    var: str | None = None
    name: str = ""
    guarded: bool = False
    adjusts: list[Op] = field(default_factory=list)
    commits: list[Op] = field(default_factory=list)
    enables: list[Op] = field(default_factory=list)
    destroys: list[Op] = field(default_factory=list)
    forces: list[Op] = field(default_factory=list)
    escaped: bool = False  # handle is returned / stored / passed on, so later use is invisible to us

    @property
    def label(self) -> str:
        if self.effect:
            n = self.effect
        elif isinstance(self.effect_raw, str):
            n = self.effect_raw
        else:
            n = f"effect({self.var or 'unresolved'})"
        p = "" if self.priority is None or self.priority is UNKNOWN else f"@{self.priority:g}"
        return f"{n}{p}" + (f" ({self.name})" if self.name else "")


@dataclass
class Optic:
    name: str
    file: str
    line: int
    effects: list[str]
    vision: list[str] | None
    thermal: list[Any] | None


@dataclass
class Result:
    root: str
    files: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)
    ti_calls: list[dict] = field(default_factory=list)
    optics: list[Optic] = field(default_factory=list)
    optic_effects: dict[str, Instance] = field(default_factory=dict)
    layers: list[dict] = field(default_factory=list)       # UI layer table (cut*/title* commands)
    grids: list[dict] = field(default_factory=list)        # terrain Grid classes and the labels they print
    grid_models: list = field(default_factory=list)        # the same as mapcfg.GridModel objects (for the preview)
    map_styles: list[dict] = field(default_factory=list)   # colours/scales of map controls found in configs
    suppressed: int = 0

    def counts(self) -> dict[str, int]:
        c = {"error": 0, "warning": 0, "info": 0}
        for f in self.findings:
            c[f.sev] += 1
        return c


class Analyzer:
    def __init__(self, rules: Rules | None = None, vanilla_classes: set[str] | None = None,
                 ignore: set[str] | None = None):
        self.rules = rules or load_rules()
        self.vanilla = {c.lower() for c in self.rules.tc.get("known_vanilla_optics_effects", [])}
        self.vanilla |= {c.lower() for c in self.rules.ui.get("known_vanilla_ui_classes", {}).get("classes", [])}
        if vanilla_classes:
            self.vanilla |= {c.lower() for c in vanilla_classes}
        self.ignore = {i.upper() for i in (ignore or set())}
        self.res = Result(root="")
        self._uid = 0
        self._ignores: dict[str, dict[int, set[str]]] = {}
        self._file_ignore: dict[str, set[str]] = {}
        self._seen: set = set()
        self._once: set = set()
        # scan-wide facts gathered before the per-file checks run
        self._roots: list[str] = []
        self.preinit_funcs: set[str] = set()   # CfgFunctions entries with preInit = 1 (lowercase)
        self.templates: set[str] = set()       # CfgPostProcessTemplates class names (lowercase)
        self.camera_effects: set[str] = set()  # CfgCameraEffects class names (lowercase)
        self.loaded_eh = False                 # a "Loaded" mission event handler exists somewhere
        self.cam_addons: set[str] = set()      # addon roots that contain camCreate + cameraEffect
        self.cam_any = False
        self._tpl_calls: list = []
        self.rsc_titles: dict[str, tuple] = {}   # RscTitles class (lowercase) -> (file, line, name)
        self.cfg_titles: dict[str, tuple] = {}   # CfgTitles class (lowercase) -> (file, line, name)
        ui.configure(self.rules.ui.get("title_effect_types", {}))
        self.ui = ui.UiModel()
        self._worlds: list[mapcfg.GridModel] = []

    # ------------------------------------------------------------------ util
    def add(self, rule: str, file: str, line: int, msg: str, sev: str | None = None, prov: str | None = None) -> None:
        cat = RULES[rule]
        sev = sev or cat["sev"]
        prov = prov or cat["prov"]
        if rule in self.ignore or "*" in self.ignore:
            return
        fi = self._file_ignore.get(file, set())
        if rule in fi or "*" in fi:
            self.res.suppressed += 1
            return
        li = self._ignores.get(file, {})
        for ln in (line, line - 1):
            s = li.get(ln)
            if s and (rule in s or "*" in s):
                self.res.suppressed += 1
                return
        key = (rule, file, line, msg)
        if key in self._seen:
            return
        self._seen.add(key)
        self.res.findings.append(Finding(rule, sev, self._rel(file), line, msg, prov))

    def once(self, key) -> bool:
        if key in self._once:
            return False
        self._once.add(key)
        return True

    def _rel(self, p: str) -> str:
        try:
            return os.path.relpath(p, self.res.root) if self.res.root and os.path.isabs(p) else p
        except ValueError:
            return p

    def _mod_of(self, path: str) -> str:
        """Which scanned root a file belongs to (label for cross-mod messages)."""
        for r in self._roots:
            rr = r if os.path.isdir(r) else os.path.dirname(r)
            if path == r or path.startswith(rr.rstrip(os.sep) + os.sep):
                return os.path.basename(rr.rstrip(os.sep)) or rr
        return ""

    def _addon_root(self, path: str) -> str:
        """Nearest ancestor directory holding a config.cpp (the addon), else the file's directory."""
        d = os.path.dirname(path)
        cur = d
        for _ in range(12):
            if os.path.isfile(os.path.join(cur, "config.cpp")):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        return d

    def _new(self, **kw) -> Instance:
        self._uid += 1
        inst = Instance(uid=self._uid, **kw)
        self.res.instances.append(inst)
        return inst

    # ------------------------------------------------------------------ scan
    def scan(self, root) -> Result:
        """Scan one path or a list of paths. Several roots are analysed together so that
        priority collisions and class references between mods are visible."""
        roots = [os.path.abspath(r) for r in ([root] if isinstance(root, str) else list(root))]
        self._roots = roots
        dirs = [r if os.path.isdir(r) else os.path.dirname(r) for r in roots]
        self.res.root = dirs[0] if len(dirs) == 1 else os.path.commonpath(dirs)
        paths: list[str] = []
        for r in roots:
            for p in self._discover(r):
                if p not in paths:
                    paths.append(p)
        self.res.files = paths
        by_base = {os.path.basename(p).lower(): p for p in paths}
        inc_cache: dict[str, dict] = {}

        def defs_for(path: str, depth: int = 0) -> dict:
            if path in inc_cache:
                return inc_cache[path]
            inc_cache[path] = {}
            try:
                text = _read(path)
            except OSError:
                return {}
            lx0 = sqf.tokenize(text, path)
            out: dict = {}
            if depth < 3:
                for inc in lx0.includes:
                    tgt = by_base.get(os.path.basename(inc.replace("\\", "/")).lower())
                    if tgt and tgt != path:
                        out.update(defs_for(tgt, depth + 1))
            out.update(lx0.defines)
            inc_cache[path] = out
            return out

        sqf_files: list[sqf.Lexed] = []
        cfg_files: list[sqf.Lexed] = []
        for p in paths:
            ext = os.path.splitext(p)[1].lower()
            try:
                text = _read(p)
            except OSError:
                continue
            extra = {}
            lx_probe = sqf.tokenize(text, p)
            for inc in lx_probe.includes:
                tgt = by_base.get(os.path.basename(inc.replace("\\", "/")).lower())
                if tgt and tgt != p:
                    extra.update(defs_for(tgt, 1))
            lx = sqf.tokenize(text, p, extra) if extra else lx_probe
            self._ignores[p] = lx.ignores
            self._file_ignore[p] = lx.ignore_file
            (sqf_files if ext in SQF_EXT else cfg_files).append(lx)

        # global variable assignments (cross-file constants like MYMOD_prio = 1600)
        global_assigns: dict[str, list] = {}
        for lx in sqf_files:
            for name, lst in sqf.collect_assignments(lx).items():
                if not name.startswith("_"):
                    global_assigns.setdefault(name, []).extend([(0, v) for _, v in lst])

        facts = [sqf.extract_calls(lx, global_assigns) for lx in sqf_files]
        # configs first: CfgFunctions / CfgPostProcessTemplates / CfgCameraEffects inform the script checks
        for lx in cfg_files:
            self._scan_config(lx)
        addon_idents: dict[str, set[str]] = {}
        for ff in facts:
            if any(s.lower() == "loaded" for s in ff.strings):
                self.loaded_eh = True
            addon_idents.setdefault(self._addon_root(ff.lexed.path), set()).update(ff.idents)
        for addon, ids in addon_idents.items():
            if "camcreate" in ids and "cameraeffect" in ids:
                self.cam_addons.add(addon)
                self.cam_any = True
        self._build_model(facts)
        for ff in facts:
            self._check_file(ff)
        self._check_instances()
        self._check_optics()
        self._check_ti_combo()
        self._check_templates()
        self.ui.finish(self)
        self.res.layers = self.ui.layers
        for m in mapcfg._merge(self._worlds):
            mapcfg.check_grid(self, m)
            if m.has_grid:
                self.res.grids.append(mapcfg.grid_report(m))
                self.res.grid_models.append(m)
        self.res.findings.sort(key=lambda f: (f.file, f.line, f.rule))
        return self.res

    def _discover(self, root: str) -> list[str]:
        if os.path.isfile(root):
            return [root]
        out = []
        for d, dirs, files in os.walk(root):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in SQF_EXT or ext in CFG_EXT:
                    p = os.path.join(d, f)
                    try:
                        if os.path.getsize(p) <= 5_000_000:
                            out.append(p)
                    except OSError:
                        pass
        return out

    # ----------------------------------------------------------------- model
    def _build_model(self, facts: list[FileFacts]) -> None:
        self.local_h: dict[tuple, list] = {}
        self.local_arr: dict[tuple, list] = {}
        self.global_h: dict[str, Any] = {}
        self.named: dict[str, Instance] = {}
        self.pip_last: dict[tuple, int] = {}

        # pass A: creations
        for ff in facts:
            lx = ff.lexed
            for c in ff.calls:
                if c.cmd != "ppeffectcreate":
                    continue
                r = c.right
                pairs: list[tuple] = []
                multi = False
                if isinstance(r, list) and r and all(isinstance(e, list) for e in r):
                    multi = True
                    pairs = [(e[0], e[1]) if len(e) == 2 else (UNKNOWN, UNKNOWN) for e in r]
                elif isinstance(r, list) and len(r) == 2:
                    pairs = [(r[0], r[1])]
                else:
                    pairs = [(UNKNOWN, UNKNOWN)]
                for k, (nm, pr) in enumerate(pairs):
                    eff, _alias = self.rules.normalize_effect(nm)
                    inst = self._new(kind="handle", effect_raw=nm, effect=eff,
                                     priority=pr if _isnum(pr) else UNKNOWN, file=c.file, line=c.line,
                                     tok=c.tok, retry=c.retry, var=c.assigned_to)
                    if c.assigned_to:
                        low = c.assigned_to.lower()
                        inst.guarded = _handle_checked(lx, c.assigned_to) or c.retry
                        inst.escaped = _handle_escapes(lx, c.assigned_to, c.tok)
                        if multi:
                            self.local_arr.setdefault((c.file, low, k), []).append((c.tok, inst))
                        else:
                            self.local_h.setdefault((c.file, low), []).append((c.tok, inst))
                            if not low.startswith("_"):
                                self.global_h[low] = _AMBIG if low in self.global_h else inst
                        if multi and not low.startswith("_"):
                            self.global_h[(low, k)] = _AMBIG if (low, k) in self.global_h else inst
                    else:
                        inst.guarded = c.retry
                    self._check_create(c, inst, nm, pr)

        # pass B: operations
        for ff in facts:
            for c in ff.calls:
                self._apply_op(ff, c)

    def _lookup(self, ref: Any, file: str, tok: int) -> Instance | None:
        if isinstance(ref, tuple):
            var, idx = ref
            lst = self.local_arr.get((file, var.lower(), idx))
            gkey: Any = (var.lower(), idx)
        elif isinstance(ref, str):
            lst = self.local_h.get((file, ref.lower()))
            gkey = ref.lower()
        else:
            return None
        if lst:
            before = [i for t, i in lst if t < tok]
            return before[-1] if before else lst[0][1]
        g = self.global_h.get(gkey)
        if g is None or g is _AMBIG:
            return None
        return g

    def _named(self, name: str, file: str, line: int) -> Instance:
        eff, _ = self.rules.normalize_effect(name)
        key = (eff or name).lower()
        inst = self.named.get(key)
        if inst is None:
            base = self.rules.effects[eff]["base_priority"] if eff else None
            inst = self._new(kind="named", effect_raw=name, effect=eff, priority=base if base is not None else UNKNOWN,
                             file=file, line=line)
            self.named[key] = inst
        return inst

    def _targets(self, c: Call, use_right: bool = False) -> list[Instance]:
        val, ref = (c.right, c.right_ref) if use_right else (c.left, c.left_ref)
        out: list[Instance | None] = []
        if isinstance(val, str) and ref is None:
            out.append(self._named(val, c.file, c.line))
        elif isinstance(ref, list):
            for r in ref:
                out.append(self._lookup(r, c.file, c.tok))
        elif ref is not None and not (isinstance(val, bool)):
            out.append(self._lookup(ref, c.file, c.tok))
        return [t for t in out if t is not None]

    def _apply_op(self, ff: FileFacts, c: Call) -> None:
        cmd = c.cmd
        if cmd in ("ppeffectadjust", "ppeffectcommit", "ppeffectenable", "ppeffectforceinnvg"):
            for inst in self._targets(c):
                op = Op(c.file, c.line, c.tok, c.right, "name" if inst.kind == "named" else "handle")
                if cmd == "ppeffectadjust":
                    inst.adjusts.append(op)
                elif cmd == "ppeffectcommit":
                    inst.commits.append(op)
                elif cmd == "ppeffectenable":
                    inst.enables.append(op)
                else:
                    inst.forces.append(op)
            if cmd == "ppeffectforceinnvg" and isinstance(c.left, str) and c.left_ref is None:
                self.add("NV001", c.file, c.line, f"ppEffectForceInNVG called with the effect name \"{c.left}\"; it needs the numeric handle from ppEffectCreate")
            if cmd == "ppeffectforceinnvg" and isinstance(c.right, (int, float, str, list)) and not isinstance(c.right, bool):
                self.add("NV004", c.file, c.line, f"ppEffectForceInNVG needs true/false, got {c.right!r}")
        elif cmd == "ppeffectdestroy":
            for inst in self._targets(c, use_right=True):
                inst.destroys.append(Op(c.file, c.line, c.tok))

    # ----------------------------------------------------- create-time checks
    def _check_create(self, c: Call, inst: Instance, nm: Any, pr: Any) -> None:
        rules = self.rules
        if isinstance(nm, str):
            eff, alias = rules.normalize_effect(nm)
            if eff is None:
                hint = alias or rules.suggest(nm)
                msg = f"unknown effect \"{nm}\"" + (f" - did you mean \"{hint}\"?" if hint else "")
                if alias:
                    msg += " (the wiki priority table lists 'ChromaticAberration' but the effect type is 'ChromAberration')"
                self.add("PP001", c.file, c.line, msg)
            elif rules.effects[eff].get("advanced"):
                self.add("PP005", c.file, c.line, f"{eff} is an advanced effect and cannot be created with ppEffectCreate; use \"{eff}\" ppEffectAdjust [...] directly")
        if _isnum(pr):
            if pr < 0 or float(pr) != int(pr):
                self.add("PP015", c.file, c.line, f"priority {pr} is negative or not a whole number")
        if not inst.guarded and not inst.retry:
            self.add("PP006", c.file, c.line, f"result of ppEffectCreate{' (' + c.assigned_to + ')' if c.assigned_to else ''} is never compared against -1")

    # ------------------------------------------------------------ file checks
    def _check_file(self, ff: FileFacts) -> None:
        lx = ff.lexed
        calls = ff.calls
        path = lx.path
        low_path = path.lower().replace("\\", "/")
        has_cam = "camcreate" in ff.idents and "cameraeffect" in ff.idents
        cam_addon = self._addon_root(path) in self.cam_addons
        ap_calls: list[Call] = []
        pip_state: dict[str, int] = {}
        for c in calls:
            cmd = c.cmd
            if cmd == "ppeffectcommit" and _isnum(c.right) and c.right < 0:
                self.add("PP016", c.file, c.line, f"commit duration {c.right} is negative")
            elif cmd in ("camusenvg", "setcamuseti"):
                if not has_cam and not cam_addon:
                    if self.cam_any:
                        self.add("NV003", c.file, c.line, f"{c.cmd_raw} used here, and camCreate + cameraEffect only appear in other addons of this scan; make sure it runs while that camera is the player's main camera", sev="info")
                    else:
                        self.add("NV003", c.file, c.line, f"{c.cmd_raw} used but nothing in the scanned files calls camCreate + cameraEffect")
                if cmd == "setcamuseti" and _isnum(c.right):
                    modes = self.rules.tc["setCamUseTI_modes"]
                    if c.right not in modes:
                        self.add("TI004", c.file, c.line, f"TI mode {c.right} is outside the documented 0-7 range")
            elif cmd == "camsetfov":
                self._check_fov(c, ff)
            elif cmd == "cameraeffect":
                self._check_camera_effect(c)
            elif cmd in ("disabletiequipment", "disablenvgequipment"):
                if isinstance(c.right, (int, float, str, list)) and not isinstance(c.right, bool):
                    self.add("TI009", c.file, c.line, f"{c.cmd_raw} needs true/false, got {c.right!r}")
            elif cmd == "setvehicletipars":
                self._check_vehicle_ti(c)
            elif cmd in ("settonemapping", "settonemappingparams"):
                self.add("TM001", c.file, c.line, f"{c.cmd_raw}: the BI wiki states this command is not present in Arma 3")
            elif cmd == "bis_fnc_setppeffecttemplate":
                self._tpl_calls.append(c)
                if self.once(("TPL002", path)):
                    self.add("TPL002", c.file, c.line, "BIS_fnc_setPPeffectTemplate creates post-process effects at priorities the wiki does not document; collisions with this mod's own effects cannot be checked")
            elif cmd == "bis_fnc_ambientpostprocess":
                if self.once(("TPL002", path)):
                    self.add("TPL002", c.file, c.line, "BIS_fnc_ambientPostprocess creates post-process effects at priorities the wiki does not document; collisions with this mod's own effects cannot be checked")
            elif cmd == "settiparameter":
                self._check_ti(c)
            elif cmd in ("setaperture", "setaperturenew"):
                ap_calls.append(c)
                self._check_aperture(c, low_path)
            elif cmd == "setpipeffect":
                self._check_pip(c, pip_state)
            elif cmd in ui.UI_CMDS:
                self.ui.check_call(self, c)

        # aperture ordering: setApertureNew first, then setAperture later in same file
        seq = [c for c in ap_calls]
        for i, c1 in enumerate(seq):
            if c1.cmd == "setaperturenew":
                for c2 in seq[i + 1:]:
                    if c2.cmd == "setaperture" and c2.owners == c1.owners:
                        self.add("AP003", c2.file, c2.line, "setAperture is called after setApertureNew and overwrites it with [v,v,v,1] when HDR is on; swap the order")
                        break

        # NVG-context hint
        mentions_nvg = any(any(w in s.lower() for w in NVG_WORDS) for s in ff.strings) or any(any(w in i for w in NVG_WORDS) for i in ff.idents)
        if mentions_nvg:
            for inst in self.res.instances:
                if inst.kind == "handle" and inst.file == path and not inst.escaped and not inst.forces and not self._forced_anywhere(inst):
                    if self.once(("NV002", path)):
                        self.add("NV002", inst.file, inst.line, f"{inst.label} is created in a file that deals with night vision but is never passed to ppEffectForceInNVG")
                    break

    def _forced_anywhere(self, inst: Instance) -> bool:
        return bool(inst.forces)

    def _check_ti(self, c: Call) -> None:
        r = c.right
        ti = self.rules.tc["ti_parameters"]
        if self.once("TI003") and not self.loaded_eh:
            self.add("TI003", c.file, c.line, "setTIParameter values are not saved in savegames, and no \"Loaded\" mission event handler exists in the scanned files to re-apply them after a load")
        if r is UNKNOWN:
            return
        if not (isinstance(r, list) and len(r) == 2):
            self.add("TI005", c.file, c.line, "expected setTIParameter [\"Name\", value]")
            return
        name, val = r
        if name is UNKNOWN:
            return
        if not isinstance(name, str):
            self.add("TI005", c.file, c.line, "parameter name must be a string")
            return
        match = next((k for k in ti if not k.startswith("_") and k.lower() == name.lower()), None)
        if match is None:
            valid = ", ".join(k for k in ti if not k.startswith("_"))
            self.add("TI001", c.file, c.line, f"unknown thermal parameter \"{name}\" (valid: {valid})")
            return
        if val is UNKNOWN:
            self.res.ti_calls.append({"file": c.file, "line": c.line, "name": match, "value": None})
            return
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            self.add("TI005", c.file, c.line, f"value for {match} must be a number, got {val!r}")
            return
        spec = ti[match]
        self.res.ti_calls.append({"file": c.file, "line": c.line, "name": match, "value": float(val)})
        if spec.get("flag"):
            if val not in (0, 1):
                self.add("TI006", c.file, c.line, f"{match}={val}: expected 0 or 1 (default {spec['default']})")
        else:
            if val < spec["min"] or val > spec["max"]:
                self.add("TI002", c.file, c.line, f"{match}={val} is outside 0..1; output is clipped to the displayable range (wiki: output = Start + thermal x Width)")
            if val != spec["default"] and self.once(("TI008", c.file)):
                self.add("TI008", c.file, c.line, f"{match} changed from its default ({spec['default']}); the offline thermal preview follows the documented formula, but tracker T185536 reports the shipped engine behaves like a levels filter instead of clipping")

    def _check_ti_combo(self) -> None:
        tp = self.rules.tc["ti_parameters"]
        cur: dict[str, tuple[float, int]] = {}
        files: dict[str, list[dict]] = {}
        for t in self.res.ti_calls:
            files.setdefault(t["file"], []).append(t)
        for f, calls in files.items():
            start, width = tp["OutputRangeStart"]["default"], tp["OutputRangeWidth"]["default"]
            seen_names: set[str] = set()
            for ti, t in enumerate(calls):
                if t["value"] is None or t["name"] not in ("OutputRangeStart", "OutputRangeWidth"):
                    continue
                seen_names.add(t["name"])
                other = "OutputRangeWidth" if t["name"] == "OutputRangeStart" else "OutputRangeStart"
                if other not in seen_names and any(x["name"] == other for x in calls[ti + 1:]):
                    # the partner is set a few lines later; judge the pair once both are known
                    if t["name"] == "OutputRangeStart":
                        start = t["value"]
                    else:
                        width = t["value"]
                    continue
                if t["name"] == "OutputRangeStart":
                    start = t["value"]
                else:
                    width = t["value"]
                if not (0 <= start <= 1 and 0 <= width <= 1):
                    continue
                if start + width > 1.0 + 1e-9:
                    lost = (start + width - 1.0) / width * 100 if width > 0 else 0
                    self.add("TI002", f, t["line"], f"OutputRangeStart {start:g} + OutputRangeWidth {width:g} = {start + width:g} > 1; the top {lost:.0f}% of the thermal range clips to white")
                if width < 0.125:
                    self.add("TI007", f, t["line"], f"OutputRangeWidth {width:g} leaves about {int(width * 255)} grey levels for the whole thermal image (default 0.8 = ~204); expect flat, banded thermals")

    # --------------------------------------------------------------- camera
    CAM_EFFECTS = {"internal", "external", "fixed", "fixedwithzoom", "terminate"}
    CAM_POSITIONS = {"top", "left", "right", "front", "back", "left front", "right front", "left back",
                     "right back", "left top", "right top", "front top", "back top", "bottom"}

    def _check_fov(self, c: Call, ff: FileFacts) -> None:
        r = c.right
        if _isnum(r) and (r < 0.01 or r > 8.5):
            self.add("CAM001", c.file, c.line, f"camSetFov {r:g} is outside the documented range 0.01 .. 8.5")
        if "camcommit" not in ff.idents and "camcommitprepared" not in ff.idents:
            self.add("CAM002", c.file, c.line, "camSetFov has no camCommit in this file, so the field of view will not change")

    def _check_camera_effect(self, c: Call) -> None:
        r = c.right
        if not isinstance(r, list) or len(r) < 2:
            return
        eff, pos = r[0], r[1]
        if isinstance(eff, str) and eff.strip():
            low = eff.strip().lower()
            if low not in self.CAM_EFFECTS and low not in self.camera_effects and ("cam" + low) not in self.camera_effects:
                self.add("CAM003", c.file, c.line, f"cameraEffect: effect \"{eff}\" is not one of Internal, External, Fixed, FixedWithZoom, Terminate and no CfgCameraEffects class of that name was found in the scan")
        if isinstance(pos, str) and pos.strip() and pos.strip().lower() not in self.CAM_POSITIONS:
            self.add("CAM003", c.file, c.line, f"cameraEffect: position \"{pos}\" is not a documented position (TOP, LEFT, RIGHT, FRONT, BACK, LEFT FRONT, ... BOTTOM)")

    def _check_vehicle_ti(self, c: Call) -> None:
        r = c.right
        if r is UNKNOWN or r is None:
            return
        if not (isinstance(r, list) and len(r) == 3):
            self.add("TI010", c.file, c.line, "setVehicleTIPars expects [engine, wheels, weapon]")
            return
        for name, v in zip(("engine", "wheels", "weapon"), r):
            if v is UNKNOWN:
                continue
            if not _isnum(v):
                self.add("TI010", c.file, c.line, f"setVehicleTIPars {name} must be a number, got {v!r}")
            elif v < 0 or v > 1:
                self.add("TI010", c.file, c.line, f"setVehicleTIPars {name}={v:g} is outside 0 (cold) .. 1 (hot)", sev="warning")

    def _check_templates(self) -> None:
        builtin = {"default", "blackandwhite", "mediterranean", "eastwind", "realisbrown"}
        for c in self._tpl_calls:
            name = "Default"
            if c.has_left and isinstance(c.left, list) and c.left:
                name = c.left[0]
            elif c.has_left and c.left is not None and not isinstance(c.left, list):
                continue
            if not isinstance(name, str) or name is UNKNOWN:
                continue
            if name.lower() not in builtin and name.lower() not in self.templates:
                self.add("TPL001", c.file, c.line, f"post-process template \"{name}\" is neither built in nor defined in CfgPostProcessTemplates in this scan; the function falls back to \"Default\"")

    def _check_aperture(self, c: Call, low_path: str) -> None:
        stem = os.path.basename(low_path)
        func = stem[3:-4] if stem.startswith("fn_") and stem.endswith(".sqf") else ""
        bare = stem[:-4] if stem.endswith(".sqf") else stem
        if "preinit" in low_path or (func and func in self.preinit_funcs) or bare in self.preinit_funcs:
            why = "a pre-init file" if "preinit" in low_path else "a function registered with preInit = 1 in CfgFunctions"
            self.add("AP004", c.file, c.line, f"{c.cmd_raw} in {why}; the engine resets aperture at mission start so this is lost (set it after start, e.g. after a short sleep)")
        r = c.right
        if c.cmd == "setaperture":
            if _isnum(r):
                if r <= 0:
                    pass  # documented idiom for returning to automatic aperture; nothing to flag
                elif r > 100:
                    self.add("AP001", c.file, c.line, f"setAperture {r}: values above ~100 have no further effect")
                elif r < 20:
                    self.add("AP001", c.file, c.line, f"setAperture {r}: below 20 renders a very bright scene (wiki note: ~50 outdoor daylight, ~30 indoor); fine for night, washed out by day")
        else:
            if r is UNKNOWN:
                return
            ok = isinstance(r, list) and ((len(r) == 1 and r[0] in (-1, UNKNOWN)) or len(r) == 4)
            if ok and len(r) == 4:
                ok = all(x is UNKNOWN or _isnum(x) for x in r)
            if not ok:
                self.add("AP002", c.file, c.line, "setApertureNew expects [min, std, max, stdLum] or [-1]")

    def _check_pip(self, c: Call, state: dict) -> None:
        r = c.right
        if not isinstance(r, list) or not r or r[0] is UNKNOWN:
            return
        mode = r[0]
        tc = self.rules.tc
        if not _isnum(mode):
            self.add("PIP001", c.file, c.line, f"PiP effect mode must be a number, got {mode!r}")
            return
        lo, hi = tc["pip_alt_ti_range"]
        modes = tc["pip_modes"]
        if str(int(mode)) not in modes and not (lo <= mode <= hi):
            self.add("PIP001", c.file, c.line, f"PiP effect mode {mode} is not documented (0,1,2,3,7,8 and {lo}..{hi})")
            return
        expect = modes.get(str(int(mode)), {"params": 1})["params"]
        if len(r) != expect:
            self.add("PIP002", c.file, c.line, f"PiP mode {int(mode)} takes {expect} value(s) in the array, got {len(r)}")
        key = c.left if isinstance(c.left, str) else None
        if key:
            if mode == 3:
                state[key] = c.line
            elif mode == 0 and key in state:
                self.add("PIP003", c.file, c.line, f"\"{key}\" went through colour correction (mode 3) earlier; setPiPEffect [0] will not undo it - send [3, 0, ...] to disable instead")

    # --------------------------------------------------------- instance checks
    def _check_instances(self) -> None:
        rules = self.rules
        th = rules.thresholds
        handles = [i for i in self.res.instances if i.kind == "handle"]

        # priority collisions
        groups: dict[float, list[Instance]] = {}
        for i in handles:
            adv = bool(i.effect and self.rules.effects[i.effect].get("advanced"))
            if _isnum(i.priority) and not i.retry and not adv:
                groups.setdefault(float(i.priority), []).append(i)
        for prio, grp in groups.items():
            if len(grp) < 2:
                continue
            for a_i, a in enumerate(grp):
                for b in grp[a_i + 1:]:
                    same_file = a.file == b.file
                    sev = "warning"
                    if same_file:
                        lx = self._lexed(a.file)
                        destroyed_between = any(a.tok < d.tok < b.tok for d in a.destroys)
                        oa, ob = (lx.owners[a.tok], lx.owners[b.tok]) if lx else ((), ())
                        nested = ob[:len(oa)] == oa or oa[:len(ob)] == ob
                        if nested and not destroyed_between:
                            sev = "error"
                    where = f"{self._rel(a.file)}:{a.line} ({a.label}) and {self._rel(b.file)}:{b.line} ({b.label})"
                    ma, mb = self._mod_of(a.file), self._mod_of(b.file)
                    cross = f"[cross-mod: {ma} vs {mb}] " if len(self._roots) > 1 and ma and mb and ma != mb else ""
                    msg = f"{cross}priority {prio:g} is used by {where}; if both exist at once the second ppEffectCreate returns -1 and that effect never appears"
                    if sev == "error":
                        msg += " (same script scope, first handle not destroyed in between)"
                    self.add("PP004", b.file, b.line, msg, sev=sev)

        for i in handles + [n for n in self.res.instances if n.kind == "named"]:
            eff = i.effect
            spec = rules.effects.get(eff) if eff else None
            # parameter validation
            for op in i.adjusts:
                if spec is None:
                    break
                v = op.value
                if v is UNKNOWN:
                    continue
                if not isinstance(v, list):
                    continue
                for rule, sev, msg, prov in validate_params(rules, eff, v, op.syntax):
                    self.add(rule, op.file, op.line, f"{eff}: {msg}", sev=sev, prov=prov)
            # commit semantics
            if spec and not spec.get("advanced") and i.adjusts and not i.escaped:
                for fpath in {o.file for o in i.adjusts}:
                    last_adj = max(o.tok for o in i.adjusts if o.file == fpath)
                    commits_here = [o.tok for o in i.commits if o.file == fpath]
                    commits_elsewhere = [o for o in i.commits if o.file != fpath]
                    if not any(t > last_adj for t in commits_here) and not commits_elsewhere:
                        op = max((o for o in i.adjusts if o.file == fpath), key=lambda o: o.tok)
                        self.add("PP007", op.file, op.line, f"{i.label}: ppEffectAdjust here is never followed by ppEffectCommit, so the new values are not applied")
            # never enabled
            if i.adjusts and not i.escaped and not any(e.value is True for e in i.enables) and not any(e.value is UNKNOWN for e in i.enables):
                if not (spec and spec.get("advanced")):
                    sev = "warning" if i.kind == "handle" else "info"
                    self.add("PP008", i.adjusts[0].file, i.adjusts[0].line, f"{i.label}: no ppEffectEnable true found for this effect", sev=sev)
            # leak
            if i.kind == "handle" and not i.escaped and not i.destroys and not any(e.value is False for e in i.enables):
                self.add("PP009", i.file, i.line, f"{i.label}: handle {i.var or '(unused)'} is never destroyed or disabled")
            # fade cut-off
            self._check_fade_cut(i)
            # named-instance hints
            if i.kind == "named" and i.effect:
                if self.once(("PP011", i.effect)):
                    self.add("PP011", i.file, i.line, f"\"{i.effect}\" is driven by name; other scripts/mods using the same name share and overwrite this instance")
                if rules.effects[i.effect].get("handle_only") and self.once(("PP019", i.effect)):
                    self.add("PP019", i.file, i.line, f"{i.effect} is used by name here but only works with a handle")
            if spec and (spec.get("player_option_dependency") or i.effect == "WetDistortion") and (i.adjusts or i.kind == "handle"):
                if self.once(("PP018", i.effect)):
                    dep = spec.get("player_option_dependency") or "water state (cancels automatically underwater)"
                    self.add("PP018", i.file, i.line, f"{i.effect} depends on: {dep}")

        # per-file ordering & stacking
        by_file: dict[str, list[Instance]] = {}
        for i in handles:
            by_file.setdefault(i.file, []).append(i)
        for fpath, insts in by_file.items():
            known = [i for i in insts if i.effect and _isnum(i.priority)]
            for pair in rules.pp["ordering_pairs"]["pairs"]:
                for a in known:
                    if a.effect != pair["first"]:
                        continue
                    for b in known:
                        if b.effect == pair["then"] and a.priority > b.priority:
                            self.add("PP013", b.file, b.line, f"{a.label} (line {a.line}) has a higher priority than {b.label}, so it is applied AFTER it. {pair['problem']}", sev=pair["sev"])
            ccs = [i for i in insts if i.effect == "ColorCorrections" and i.adjusts]
            if len(ccs) >= th["stacked_color_corrections_warn"] and self.once(("PP014", fpath)):
                self.add("PP014", ccs[0].file, ccs[0].line, f"{len(ccs)} ColorCorrections instances are created in this file (lines {', '.join(str(c.line) for c in ccs)}); their brightness/contrast/colorize compound")

    def _check_fade_cut(self, inst: Instance) -> None:
        lex_cache = {}
        for c1 in inst.commits:
            if not (_isnum(c1.value) and c1.value > 0):
                continue
            nxt = [o for o in inst.enables if o.value is False and o.file == c1.file and o.tok > c1.tok] + \
                  [o for o in inst.destroys if o.file == c1.file and o.tok > c1.tok]
            if not nxt:
                continue
            o2 = min(nxt, key=lambda o: o.tok)
            lx = self._lexed(c1.file)
            if lx is None:
                continue
            between = lx.toks[c1.tok:o2.tok]
            if lx.owners[c1.tok] != lx.owners[o2.tok]:
                continue
            if any(t.kind == "id" and t.val.lower() in WAIT_IDS for t in between):
                continue
            self.add("PP010", o2.file, o2.line, f"{inst.label}: committed with a {c1.value:g}s fade at line {c1.line} but disabled/destroyed immediately after, with no wait in between; the fade never plays")

    def _lexed(self, path: str):
        if not hasattr(self, "_lex_cache"):
            self._lex_cache: dict = {}
        if path not in self._lex_cache:
            try:
                self._lex_cache[path] = sqf.tokenize(_read(path), path)
            except OSError:
                self._lex_cache[path] = None
        return self._lex_cache[path]

    # ---------------------------------------------------------------- config
    def _scan_config(self, lx: sqf.Lexed) -> None:
        root = parse_config(lx)
        # UI resources (cutRsc / titleRsc / cutObj targets) and map config
        for cls in walk(root):
            p0 = cls.path[0].lower() if cls.path else ""
            if len(cls.path) == 2 and p0 == "rsctitles":
                self.rsc_titles.setdefault(cls.name.lower(), (cls.file, cls.line, cls.name))
            elif len(cls.path) == 2 and p0 == "cfgtitles":
                self.cfg_titles.setdefault(cls.name.lower(), (cls.file, cls.line, cls.name))
        self._worlds.extend(mapcfg.collect_worlds(root))
        for mc, anc in mapcfg.collect_map_controls(root):
            self.res.map_styles.append(mapcfg.check_map_control(self, mc, anc))
        # CfgOpticsEffect
        for cls in walk(root):
            if cls.name.lower() == "cfgopticseffect":
                for ch in cls.children.values():
                    self._config_effect(ch)
        # context for the script checks: templates, camera effects, pre-init functions
        for cls in walk(root):
            p0 = cls.path[0].lower() if cls.path else ""
            if p0 == "cfgpostprocesstemplates" and len(cls.path) == 2:
                self.templates.add(cls.name.lower())
            elif p0 == "cfgcameraeffects" and len(cls.path) == 2:
                self.camera_effects.add(cls.name.lower())
            elif p0 == "cfgfunctions" and len(cls.path) == 4:
                pre = cls.props.get("preinit", (None, 0))[0]
                if pre in (1, True, "1", "true"):
                    self.preinit_funcs.add(cls.name.lower())
                    f = cls.props.get("file", (None, 0))[0]
                    if isinstance(f, str) and f:
                        self.preinit_funcs.add(os.path.splitext(os.path.basename(f.replace("\\", "/")))[0].lower())
        # optics zoom / peripheral vision sanity
        for cls in walk(root):
            zs = {k: cls.props[k] for k in ("opticszoommin", "opticszoominit", "opticszoommax") if k in cls.props and _isnum(cls.props[k][0])}
            # weapon optics only: vehicle turrets in the wild (e.g. ACE3 Javelin) use the opposite Min/Max convention
            in_weapon_optics = any(p.lower() == "opticsmodes" for p in cls.path)
            if len(zs) >= 2 and in_weapon_optics:
                order = [k for k in ("opticszoommin", "opticszoominit", "opticszoommax") if k in zs]
                for a, b in zip(order, order[1:]):
                    if zs[a][0] > zs[b][0] + 1e-9:
                        nm = {"opticszoommin": "opticsZoomMin", "opticszoominit": "opticsZoomInit", "opticszoommax": "opticsZoomMax"}
                        self.add("CF005", cls.file, zs[a][1], f"{'::'.join(cls.path)}: {nm[a]}={zs[a][0]:g} is greater than {nm[b]}={zs[b][0]:g}; these are FOV values, so the expected order is Min <= Init <= Max")
                        break
            pv = cls.props.get("opticsdisableperipherialvision")
            if pv is not None and _isnum(pv[0]) and (pv[0] < 0 or pv[0] > 1):
                self.add("CF006", cls.file, pv[1], f"{'::'.join(cls.path)}: opticsDisablePeripherialVision={pv[0]:g} is outside 0..1")
        # optics modes / weapon-level props
        for cls in walk(root):
            if any(k in cls.props for k in ("opticsppeffects", "visionmode", "thermalmode")):
                eff = cls.props.get("opticsppeffects", ([], 0))[0]
                vis = cls.props.get("visionmode", (None, 0))[0]
                thm = cls.props.get("thermalmode", (None, 0))[0]
                self.res.optics.append(Optic("::".join(cls.path), cls.file, cls.line,
                                             [e for e in eff if isinstance(e, str)] if isinstance(eff, list) else [],
                                             [v for v in vis if isinstance(v, str)] if isinstance(vis, list) else None,
                                             thm if isinstance(thm, list) else None))

    def _config_effect(self, cls: CfgClass) -> None:
        typ = cls.props.get("type", (None, cls.line))
        params = cls.props.get("params", (None, cls.line))
        prio = cls.props.get("priority", (None, cls.line))
        eff, alias = self.rules.normalize_effect(typ[0]) if typ[0] is not None else (None, None)
        inst = self._new(kind="config", effect_raw=typ[0], effect=eff, priority=prio[0] if _isnum(prio[0]) else UNKNOWN,
                         file=cls.file, line=cls.line, name=cls.name)
        self.res.optic_effects[cls.name.lower()] = inst
        if typ[0] is None:
            return  # probably inherits type from a vanilla class
        if eff is None:
            hint = alias or (self.rules.suggest(typ[0]) if isinstance(typ[0], str) else None)
            self.add("CF004", cls.file, typ[1], f"CfgOpticsEffect >> {cls.name}: unknown type \"{typ[0]}\"" + (f" - did you mean \"{hint}\"?" if hint else ""))
            return
        if params[0] is not None and isinstance(params[0], list):
            # strings inside config arrays are expressions evaluated by the engine
            # (CBA: params[] = {0.005, 0.005, "0.35/(getResolution select 4)", 0.35};) - not type errors
            pvals = _unknown_strings(params[0])
            inst.adjusts.append(Op(cls.file, params[1], -1, pvals, "handle"))
            for rule, sev, msg, prov in validate_params(self.rules, eff, pvals, "handle"):
                self.add("CF004" if rule == "PP002" else rule, cls.file, params[1], f"CfgOpticsEffect >> {cls.name}: {msg}", sev=sev, prov=prov)

    def _check_optics(self) -> None:
        known = set(self.res.optic_effects) | self.vanilla
        valid_vm = {v.lower() for v in self.rules.tc["vision_modes"]}
        for o in self.res.optics:
            for e in o.effects:
                if e.lower() not in known and not _VANILLA_OPTICS_RE.match(e):
                    self.add("CF001", o.file, o.line, f"{o.name}: opticsPPEffects references \"{e}\" which is not defined in this mod or the known vanilla list")
            seen: dict[float, str] = {}
            for e in o.effects:
                inst = self.res.optic_effects.get(e.lower())
                if inst is not None and _isnum(inst.priority):
                    if inst.priority in seen and seen[inst.priority] != e:
                        self.add("PP004", o.file, o.line, f"{o.name}: effects \"{seen[inst.priority]}\" and \"{e}\" share priority {inst.priority:g}; only one of them will be created")
                    seen[inst.priority] = e
            if o.vision is not None:
                for v in o.vision:
                    if v.lower() not in valid_vm:
                        self.add("CF002", o.file, o.line, f"{o.name}: unknown visionMode \"{v}\" (known: {', '.join(self.rules.tc['vision_modes'])})")
                if o.thermal and "ti" not in [v.lower() for v in o.vision]:
                    self.add("CF003", o.file, o.line, f"{o.name}: thermalMode is set but visionMode has no \"Ti\"")


# ---------------------------------------------------------------------------
def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _unknown_strings(v):
    if isinstance(v, list):
        return [_unknown_strings(x) for x in v]
    return UNKNOWN if isinstance(v, str) else v


PP_USE_CMDS = {"ppeffectadjust", "ppeffectcommit", "ppeffectenable", "ppeffectforceinnvg",
               "ppeffectcommitted", "ppeffectenabled"}
PP_PREFIX_CMDS = {"ppeffectdestroy", "ppeffectenabled", "ppeffectcommitted", "private"}


def _handle_escapes(lx: sqf.Lexed, var: str, start: int) -> bool:
    """True when `var` (a ppEffectCreate handle) is used in a way we cannot follow: returned
    from a function, stored in a collection, passed to another call, copied to another variable.
    Lifecycle rules (never enabled / never destroyed / never committed) stay quiet for such handles
    because the missing step may well happen where the handle ends up."""
    toks = lx.toks
    for k in range(start + 1, len(toks)):
        t = toks[k]
        if not (t.kind == "id" and t.val == var):
            continue
        prv = toks[k - 1] if k > 0 else None
        nxt = toks[k + 1] if k + 1 < len(toks) else None
        if nxt is not None and nxt.kind == "id" and nxt.val.lower() in PP_USE_CMDS:
            continue
        if prv is not None and prv.kind == "id" and prv.val.lower() in PP_PREFIX_CMDS:
            continue
        if nxt is not None and nxt.kind == "op" and nxt.val == "=":
            continue  # reassigned
        if nxt is not None and ((nxt.kind == "op" and nxt.val in COMPARE_OPS) or (nxt.kind == "id" and nxt.val.lower() in CMP_IDS)):
            continue
        if prv is not None and prv.kind == "op" and prv.val in COMPARE_OPS:
            continue
        # inside an array that is itself the operand of a pp command: [_h1,_h2] ppEffectEnable true
        if _in_pp_array(lx, k):
            continue
        return True
    return False


def _in_pp_array(lx: sqf.Lexed, k: int) -> bool:
    toks = lx.toks
    depth = 0
    j = k - 1
    while j >= 0:
        t = toks[j]
        if t.kind == "punct":
            if t.val in ("]", ")", "}"):
                depth += 1
            elif t.val in ("[", "(", "{"):
                if depth == 0:
                    if t.val != "[":
                        return False
                    close = lx.match.get(j)
                    after = toks[close + 1] if close is not None and close + 1 < len(toks) else None
                    before = toks[j - 1] if j > 0 else None
                    if after is not None and after.kind == "id" and after.val.lower() in PP_USE_CMDS:
                        return True
                    if before is not None and before.kind == "id" and before.val.lower() == "ppeffectdestroy":
                        return True
                    return False
                depth -= 1
            elif t.val == ";" and depth == 0:
                return False
        j -= 1
    return False


def _handle_checked(lx: sqf.Lexed, var: str) -> bool:
    toks = lx.toks
    for k, t in enumerate(toks):
        if t.kind == "id" and t.val == var:
            nx = toks[k + 1] if k + 1 < len(toks) else None
            pv = toks[k - 1] if k > 0 else None
            if nx is not None and ((nx.kind == "op" and nx.val in COMPARE_OPS) or (nx.kind == "id" and nx.val.lower() in CMP_IDS)):
                return True
            if pv is not None and pv.kind == "op" and pv.val in COMPARE_OPS:
                return True
    return False
