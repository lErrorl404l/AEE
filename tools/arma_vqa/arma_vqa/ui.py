"""UI layer checks: cutRsc / cutText / cutObj / cutFadeOut, titleRsc / titleText / titleObj / titleFadeOut,
and BIS_fnc_rscLayer.

What is known (BI wiki: cutRsc, cutText, cutObj, cutFadeOut, allCutLayers, titleRsc, titleText,
Title Effect Type, BIS_fnc_rscLayer):

* Layer 0 is the back-most. Numeric layers are rounded and cannot be negative. Layer names (strings) are
  case-sensitive and are allocated a layer number the first time they are used, in order of first use.
* Layer 0 is reserved for cut commands used without a layer or with an empty layer name.
* Showing a resource on a layer that already has one replaces it.
* Effect types: PLAIN, PLAIN NOFADE, PLAIN DOWN, BLACK, BLACK OUT, BLACK FADED, BLACK IN, WHITE OUT, WHITE IN.
  BLACK/BLACK OUT/WHITE OUT drop a full-screen "curtain" that hides the other GUI until BLACK IN / WHITE IN
  (or another effect) lifts it; BLACK FADED without a speed disappears by itself after ~5-10 s but with a
  speed it stays; WHITE OUT can blind the player, so a fade-in time should always be given.
* showInMap=false hides the resource when the map is open; the default is true, so it is drawn over the map.
* cutFadeOut: when the fade-in was shorter than 1 s the fade-out time is scaled by it (wiki user note).
* titleRsc / titleText have no layer argument.

What is NOT known and therefore never asserted: whether `"x" cutRsc` and `("x" call BIS_fnc_rscLayer) cutRsc`
share a layer, how titles and cuts stack against each other, and the properties of an RscTitles class
(the wiki page could not be read). Checks never fire on values the static evaluator could not resolve.
"""
from __future__ import annotations

import difflib
import math
import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .sqf import UNKNOWN, Call, RscLayer

if TYPE_CHECKING:  # pragma: no cover
    from .analyze import Analyzer

# Effect type names: rules/ui_map.json >> title_effect_types (wiki: Title_Effect_Type). These module constants are the
# defaults, replaced by the JSON when an Analyzer is created (see configure()).
EFFECT_TYPES = ["PLAIN", "PLAIN NOFADE", "PLAIN DOWN", "BLACK", "BLACK OUT", "BLACK FADED", "BLACK IN", "WHITE OUT", "WHITE IN"]
CURTAIN_ON = {"BLACK", "BLACK OUT", "BLACK FADED", "WHITE OUT"}
CURTAIN_OFF = {"BLACK IN", "WHITE IN"}
PLAINS = {"PLAIN", "PLAIN NOFADE", "PLAIN DOWN"}


def configure(spec: dict) -> None:
    global EFFECT_TYPES, CURTAIN_ON, CURTAIN_OFF, PLAINS
    if spec and spec.get("types"):
        EFFECT_TYPES = [t.upper() for t in spec["types"]]
        CURTAIN_ON = {t.upper() for t in spec.get("curtain_on", [])}
        CURTAIN_OFF = {t.upper() for t in spec.get("curtain_off", [])}
        PLAINS = {t for t in EFFECT_TYPES if t.startswith("PLAIN")}

CUT_CMDS = {"cutrsc", "cuttext", "cutobj", "cutfadeout"}
TITLE_CMDS = {"titlersc", "titletext", "titleobj", "titlefadeout"}
UI_CMDS = CUT_CMDS | TITLE_CMDS | {"bis_fnc_rsclayer"}

# argument layout of the array operand: (name, kind)   kind: s=string n=number b=boolean
SIGNATURES = {
    "cutrsc": [("class", "s"), ("effect", "s"), ("speed", "n"), ("showInMap", "b"), ("drawOverHUD", "b")],
    "cuttext": [("text", "s"), ("effect", "s"), ("speed", "n"), ("showInMap", "b"), ("isStructuredText", "b"), ("drawOverHUD", "b")],
    "cutobj": [("class", "s"), ("effect", "s"), ("speed", "n"), ("showInMap", "b"), ("drawOverHUD", "b")],
    "titlersc": [("class", "s"), ("effect", "s"), ("speed", "n"), ("showInMap", "b")],
    "titletext": [("text", "s"), ("effect", "s"), ("speed", "n"), ("showInMap", "b"), ("isStructuredText", "b")],
    # titleObj was not documented on a page we could read: no argument-count/type checks
}
_MARKUP_RE = re.compile(r"<\s*(?:t|br|img|a)\b[^>]*>|<\s*br\s*/?\s*>", re.I)


def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def norm_effect(v) -> str | None:
    if not isinstance(v, str):
        return None
    return " ".join(v.upper().split())


def layer_key(c: Call):
    """Which layer a call addresses, or None if it cannot be resolved statically."""
    if c.cmd in TITLE_CMDS:
        return ("title", 0)
    if not c.has_left:
        return ("n", 0)
    L = c.left
    if L is UNKNOWN or L is None or isinstance(L, bool):
        return None
    if isinstance(L, RscLayer):
        return ("r", str(L).lower())
    if _isnum(L):
        return ("n", int(math.floor(L + 0.5))) if L >= 0 else ("bad", L)   # negative: reported as UI002, still a known (invalid) layer
    if isinstance(L, str):
        return ("n", 0) if L == "" else ("s", L)
    return None


def key_label(key) -> str:
    kind, v = key
    if kind == "n":
        return f"layer {v}" + (" (the reserved default layer)" if v == 0 else "")
    if kind == "s":
        return f'layer "{v}"'
    if kind == "r":
        return f'rscLayer "{v}"'
    if kind == "bad":
        return f"invalid layer {v:g}"
    return "the title slot"


@dataclass
class Use:
    key: tuple | None
    cmd: str
    kind: str                 # show | clear | fade
    res: str | None
    effect: str | None
    speed: Any
    show_in_map: Any
    over_hud: Any
    file: str
    line: int
    tok: int
    owners: tuple
    addon: str
    mod: str
    raw: str = ""

    @property
    def identity(self) -> tuple:
        """What is being shown. Two scripts of the same addon showing text are treated as one feature;
        text from different addons is different content."""
        if self.cmd.endswith("rsc"):
            return ("rsc", (self.res or "").lower())
        if self.cmd.endswith("obj"):
            return ("obj", (self.res or "").lower())
        return ("text", self.addon)


@dataclass
class UiModel:
    uses: list[Use] = field(default_factory=list)
    rsc_layer_calls: list[Call] = field(default_factory=list)
    unknown_layer_addons: set = field(default_factory=set)   # addons with a fade/clear on a layer we could not resolve
    layers: list[dict] = field(default_factory=list)         # filled by finish(): the report table

    # ------------------------------------------------------------------ per call
    def check_call(self, an: "Analyzer", c: Call) -> None:
        cmd = c.cmd
        if cmd == "bis_fnc_rsclayer":
            self._check_rsc_layer(an, c)
            return
        key = layer_key(c)
        items = c.items
        addon = an._addon_root(c.file)
        mod = an._mod_of(c.file)

        # --- layer argument ---------------------------------------------------------------------
        if cmd in TITLE_CMDS and c.has_left and cmd != "titlefadeout":
            an.add("UI004", c.file, c.line, f"{c.cmd_raw} has no layer argument on the wiki (only `{c.cmd_raw} [...]`); the left operand will not select a layer")
        if cmd in CUT_CMDS and c.has_left and _isnum(c.left):
            if c.left < 0:
                an.add("UI002", c.file, c.line, f"layer {c.left:g} is negative; the wiki says layer numbers cannot be negative")
            elif abs(c.left - round(c.left)) > 1e-9:
                an.add("UI002", c.file, c.line, f"layer {c.left:g} is rounded to {int(math.floor(c.left + 0.5))} by the engine (e.g. 99.5 becomes layer 100)", sev="info")

        # --- fades -----------------------------------------------------------------------------
        if cmd in ("cutfadeout", "titlefadeout"):
            self.uses.append(Use(key, cmd, "fade", None, None, c.right if _isnum(c.right) else None, None, None,
                                 c.file, c.line, c.tok, c.owners, addon, mod, c.cmd_raw))
            if key is None and cmd == "cutfadeout":
                self.unknown_layer_addons.add(addon)
            self._check_fade_scaling(an, c, key)
            return

        # --- array operand ---------------------------------------------------------------------
        if items is None:
            if c.right is not UNKNOWN and not isinstance(c.right, list):
                an.add("UI004", c.file, c.line, f"{c.cmd_raw} expects an array operand, got {c.right!r}")
            if key is None and cmd in CUT_CMDS:
                self.unknown_layer_addons.add(addon)
            return
        sig = SIGNATURES.get(cmd)
        if sig is not None:
            if len(items) > len(sig):
                an.add("UI004", c.file, c.line, f"{c.cmd_raw} takes at most {len(sig)} array elements ({', '.join(n for n, _ in sig)}), got {len(items)}")
            if len(items) < 1:
                an.add("UI004", c.file, c.line, f"{c.cmd_raw} needs at least the {sig[0][0]} element")
            for k, ((name, kind), v) in enumerate(zip(sig, items)):
                if v is UNKNOWN:
                    continue
                ok = (kind == "s" and isinstance(v, str)) or (kind == "n" and _isnum(v)) or (kind == "b" and isinstance(v, bool))
                if not ok:
                    want = {"s": "a string", "n": "a number", "b": "true/false"}[kind]
                    an.add("UI004", c.file, c.line, f"{c.cmd_raw}: element {k} ({name}) should be {want}, got {v!r}")
        first = items[0] if items else UNKNOWN
        eff_raw = items[1] if len(items) > 1 else UNKNOWN
        speed = items[2] if len(items) > 2 else None   # None = argument omitted
        sim_ = items[3] if len(items) > 3 else None
        is_text = cmd.endswith("text")
        is_obj_or_rsc = not is_text

        effect = norm_effect(eff_raw)
        if effect is not None and effect not in EFFECT_TYPES:
            near = difflib.get_close_matches(effect, EFFECT_TYPES, n=1, cutoff=0.6)
            an.add("UI003", c.file, c.line, f"{c.cmd_raw}: unknown effect type \"{eff_raw}\"" + (f" - did you mean \"{near[0]}\"?" if near else "")
                   + f" (known: {', '.join(EFFECT_TYPES)})")

        # --- speed ---------------------------------------------------------------------------------
        if effect == "WHITE OUT" and (speed is None or (_isnum(speed) and speed <= 0)):
            an.add("UI014", c.file, c.line, f"{c.cmd_raw}: WHITE OUT with {'no fade-in time' if speed is None else f'speed {speed:g}'}; the wiki warns it can blind the player and says to always set a fade-in time")
        if effect == "BLACK FADED" and speed is None:
            an.add("UI015", c.file, c.line, f"{c.cmd_raw}: BLACK FADED without a speed disappears by itself after roughly 5-10 seconds (with a speed the screen stays black until cleared)", sev="info")

        # --- text markup -----------------------------------------------------------------------------
        if is_text and c.item_toks:
            has_markup = any(t.kind == "str" and _MARKUP_RE.search(t.val) for t in c.item_toks[0])
            structured = items[4] if len(items) > 4 else None
            if has_markup and structured is not True and structured is not UNKNOWN:
                an.add("UI005", c.file, c.line, f"{c.cmd_raw}: the text contains Structured Text markup (<t>, <br/>, ...) but isStructuredText is "
                       + ("not set" if structured is None else "false") + ", so the tags are printed literally; pass true as the isStructuredText element")

        # --- bookkeeping --------------------------------------------------------------------------------
        res = first if (is_obj_or_rsc and isinstance(first, str)) else None
        kind = "show"
        if is_text and first == "" and effect in PLAINS:
            kind = "clear"
        if cmd.endswith("rsc") and isinstance(first, str) and first.lower() == "default":
            kind = "clear"
            an.add("UI010", c.file, c.line, f"{c.cmd_raw} [\"Default\", ...] relies on an RscTitles class named Default; the wiki says it no longer exists in current Arma 3. Clear with cutText [\"\", \"PLAIN\"] or cutFadeOut instead")
        show_in_map = sim_ if isinstance(sim_, bool) else (True if sim_ is None else None)
        over_hud = items[4] if (cmd in ("cutrsc", "cutobj") and len(items) > 4 and isinstance(items[4], bool)) else (
            items[5] if (cmd == "cuttext" and len(items) > 5 and isinstance(items[5], bool)) else None)
        u = Use(key, cmd, kind, res, effect, speed if _isnum(speed) else (None if speed is None else UNKNOWN), show_in_map, over_hud,
                c.file, c.line, c.tok, c.owners, addon, mod, c.cmd_raw)
        self.uses.append(u)
        if key is None and cmd in CUT_CMDS:
            self.unknown_layer_addons.add(addon)

        if key == ("n", 0) and cmd in CUT_CMDS and an.once(("UI008", c.file, kind)):
            if kind == "clear":
                an.add("UI008", c.file, c.line, f"{c.cmd_raw} clears layer 0, the reserved default layer that every cut command without a layer argument shares - it removes other scripts' resources too; give it its own named layer", sev="info")
            else:
                an.add("UI008", c.file, c.line, f"{c.cmd_raw} without a layer uses layer 0, which the wiki reserves for cut commands without a layer or with an empty name; any other mod doing the same replaces this resource. Use a named layer, e.g. \"tag_name\" {c.cmd_raw} [...]", sev="info")
        if kind == "show" and effect in CURTAIN_ON and show_in_map is True and an.once(("UI012", c.file, c.line)):
            an.add("UI012", c.file, c.line, f"{c.cmd_raw} {effect}: a full-screen curtain with showInMap true (the default) is not hidden when the map opens; pass false as the showInMap element if it must not cover the map")

    # ------------------------------------------------------------------ helpers
    def _check_rsc_layer(self, an: "Analyzer", c: Call) -> None:
        v = c.left
        if v is UNKNOWN or v is None:
            return
        name = v[0] if isinstance(v, list) and len(v) == 1 else v
        if isinstance(v, list) and len(v) > 1:
            an.add("UI011", c.file, c.line, "BIS_fnc_rscLayer takes a single layer name: [\"name\"] call BIS_fnc_rscLayer")
        elif isinstance(name, list) and not name:
            return  # [] -> the calling function's name is used
        elif name is UNKNOWN:
            return
        elif not isinstance(name, str):
            an.add("UI011", c.file, c.line, f"BIS_fnc_rscLayer expects the layer name as a String, got {name!r}")
        elif name == "":
            an.add("UI011", c.file, c.line, "BIS_fnc_rscLayer called with an empty name; the layer name should be a unique, tagged string")

    def _check_fade_scaling(self, an: "Analyzer", c: Call, key) -> None:
        """Wiki user note (Arma 3 1.60): with a fade-in shorter than 1 s, cutFadeOut's time is multiplied by the fade-in."""
        dur = c.right
        if key is None or not _isnum(dur):
            return
        prev = None
        for u in reversed(self.uses[:-1]):
            if u.file == c.file and u.key == key and u.kind == "show" and u.owners == c.owners:
                prev = u
                break
        if prev is None or not _isnum(prev.speed) or not (0 < prev.speed < 1):
            return
        an.add("UI007", c.file, c.line, f"cutFadeOut {dur:g} follows a fade-in of {prev.speed:g}s (line {prev.line}); per a wiki user note (Arma 3 1.60) the fade-out is then scaled by the fade-in, i.e. about {dur * prev.speed:.2g}s rather than {dur:g}s")

    # ------------------------------------------------------------------ whole scan
    def finish(self, an: "Analyzer") -> None:
        shows = [u for u in self.uses if u.kind == "show" and u.key is not None]
        by_key: dict[tuple, list[Use]] = {}
        for u in self.uses:
            if u.key is not None:
                by_key.setdefault(u.key, []).append(u)

        self._collisions(an, shows)
        self._case_variants(an)
        self._orphans(an, by_key)
        self._curtains(an, by_key)
        self._classes(an)
        self._build_table(an, by_key)

    def _collisions(self, an: "Analyzer", shows: list[Use]) -> None:
        groups: dict[tuple, list[Use]] = {}
        for u in shows:
            groups.setdefault(u.key, []).append(u)
        for key, us in groups.items():
            first = us[0]
            for u in us[1:]:
                if u.identity == first.identity or u.file == first.file:
                    continue
                cross_mod = len(an._roots) > 1 and u.mod and first.mod and u.mod != first.mod
                if key[0] == "title":
                    if u.addon == first.addon and not cross_mod:
                        continue
                    sev, prov = "info", "inferred"
                    what = "titleRsc / titleText have a single slot (no layer argument), so a second title replaces the first"
                elif cross_mod:
                    sev, prov = "warning", None
                    what = "showing a resource on a layer replaces what is already there"
                elif u.addon != first.addon:
                    sev, prov = "warning", None
                    what = "showing a resource on a layer replaces what is already there"
                else:
                    sev, prov = "info", None
                    what = "fine if these two are never on screen together; otherwise the later one replaces the earlier"
                tag = f"[cross-mod: {first.mod} vs {u.mod}] " if cross_mod else ""
                adv = "; use a named layer (\"tag_name\" cutRsc [...])" if key[0] == "n" else ""
                other = f"{first.raw} \"{first.res}\"" if first.res else first.raw
                mine = f" for \"{u.res}\"" if u.res else ""
                an.add("UI001", u.file, u.line,
                       f"{tag}{key_label(key)}{mine} is also used by {other} at {an._rel(first.file)}:{first.line}; {what}{adv}",
                       sev=sev, prov=prov)

    def _case_variants(self, an: "Analyzer") -> None:
        names: dict[str, dict[str, Use]] = {}
        for u in self.uses:
            if u.key is not None and u.key[0] == "s":
                names.setdefault(u.key[1].lower(), {}).setdefault(u.key[1], u)
        for low, spell in names.items():
            if len(spell) > 1:
                items = list(spell.items())
                base_name, base_use = items[0]
                for nm, u in items[1:]:
                    an.add("UI009", u.file, u.line, f"layer name \"{nm}\" differs from \"{base_name}\" ({an._rel(base_use.file)}:{base_use.line}) only by case; the wiki says layer names are case-sensitive, so these are two different layers")

    def _orphans(self, an: "Analyzer", by_key: dict) -> None:
        shown_names = {u.key[1].lower() for u in self.uses if u.kind == "show" and u.key and u.key[0] in ("s", "r")}
        shown_nums = {u.key[1] for u in self.uses if u.kind == "show" and u.key and u.key[0] == "n"}
        any_show = any(u.kind == "show" for u in self.uses)
        if not any_show:
            return
        for u in self.uses:
            if u.kind == "show" or u.key is None or u.cmd.startswith("title"):
                continue
            k, v = u.key
            if k in ("s", "r") and v.lower() not in shown_names:
                near = difflib.get_close_matches(v.lower(), sorted(shown_names), n=1, cutoff=0.75)
                an.add("UI013", u.file, u.line, f"{u.raw}: {key_label(u.key)} is cleared/faded here but nothing in the scanned files shows anything on it" + (f" - did you mean \"{near[0]}\"?" if near else ""), sev="info")
            elif k == "n" and v != 0 and v not in shown_nums:
                an.add("UI013", u.file, u.line, f"{u.raw}: {key_label(u.key)} is cleared/faded here but nothing in the scanned files shows anything on it", sev="info")

    def _curtains(self, an: "Analyzer", by_key: dict) -> None:
        for key, us in by_key.items():
            for u in us:
                if u.kind != "show" or u.effect not in CURTAIN_ON:
                    continue
                if u.effect == "BLACK FADED" and u.speed is None:
                    continue   # disappears on its own
                if u.addon in self.unknown_layer_addons:
                    continue   # something in this addon fades/clears a layer we cannot resolve
                lifted = False
                for v in us:
                    if v is u:
                        continue
                    if v.kind in ("fade", "clear") or v.effect in CURTAIN_OFF or (v.kind == "show" and v.effect not in CURTAIN_ON):
                        lifted = True
                        break
                if not lifted:
                    an.add("UI016", u.file, u.line, f"{u.raw} {u.effect} puts a full-screen curtain on {key_label(key)} but nothing in the scanned files lifts it (no BLACK IN / WHITE IN, PLAIN, cutText \"\" or cutFadeOut on that layer); the wiki says the curtain hides the other GUI until it is withdrawn")

    def _classes(self, an: "Analyzer") -> None:
        for u in self.uses:
            if u.kind != "show" or not u.res:
                continue
            table = an.rsc_titles if u.cmd.endswith("rsc") else (an.cfg_titles if u.cmd.endswith("obj") else None)
            if not table:
                continue
            where = "RscTitles" if u.cmd.endswith("rsc") else "CfgTitles"
            low = u.res.lower()
            if low in table or low in an.vanilla or _suffix_match(low, table):
                continue
            near = difflib.get_close_matches(low, list(table), n=1, cutoff=0.8)
            tag = low.split("_")[0]
            same_tag = any(n.split("_")[0] == tag and "_" in n for n in table) and "_" in low
            hint = f" - did you mean \"{table[near[0]][2]}\"?" if near else ""
            if near or same_tag:
                an.add("UI006", u.file, u.line, f"{u.raw} class \"{u.res}\" is not defined in any {where} in the scanned files{hint}", sev="warning")
            else:
                an.add("UI006", u.file, u.line, f"{u.raw} class \"{u.res}\" is not defined in any {where} in the scanned files (fine if it comes from the game or another addon; list such names with --vanilla-classes)", sev="info")

    def _build_table(self, an: "Analyzer", by_key: dict) -> None:
        rows = []
        for key, us in sorted(by_key.items(), key=lambda kv: (kv[0][0] != "n", kv[0][1] if kv[0][0] == "n" else 0, str(kv[0]))):
            rows.append({
                "layer": key_label(key),
                "kind": {"n": "numeric", "s": "named", "r": "rscLayer", "title": "title", "bad": "invalid"}[key[0]],
                "number": key[1] if key[0] == "n" else None,
                "uses": [{
                    "cmd": u.raw or u.cmd, "what": u.kind, "resource": u.res, "effect": u.effect, "speed": u.speed if _isnum(u.speed) else None,
                    "showInMap": u.show_in_map, "drawOverHUD": u.over_hud,
                    "at": f"{an._rel(u.file)}:{u.line}",
                } for u in us],
            })
        self.layers = rows


def _suffix_match(low: str, table: dict) -> bool:
    """CBA/ACE macros are collapsed without the mod prefix (GVAR(x) -> comp_x), so tolerate `prefix_` differences."""
    for n in table:
        if len(n) >= 6 and len(low) >= 6 and (low.endswith("_" + n) or n.endswith("_" + low)):
            return True
    return False
