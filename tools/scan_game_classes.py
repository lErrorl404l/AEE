#!/usr/bin/env python3
"""Read class identities straight out of game PBOs, in memory.

This is the ground truth for the matchers: it reads what the game and the
installed mods ACTUALLY declare, so matcher coverage can be measured
against real content instead of a hand-written list of class names.

A PBO is an index of entries followed by their bytes, so nothing is
written to disk: the index says where each file sits and only the configs
and stringtables are read. A binarised config is rapified, which this
decodes directly rather than shelling out to an unpacking tool. A whole
install scans in seconds.

Each row is {source, kind, class, display, parent, fmt, feeds, magazines,
ammo, damage, item_parent, item_type, optics_modes, thermal_mode}:
  kind    CfgVehicles, CfgWeapons, CfgMagazines or CfgAmmo
  display the resolved display name; a $STR_ key is resolved from the
          stringtable.xml files inside the scanned PBOs themselves
  parent  the class it inherits, so a consumer can walk the chain and tell
          a vehicle from a prop
  feeds   true when the class declares magazines or muzzles, which is what
          separates a firearm from the uniforms and helmets that also live
          in CfgWeapons
  magazines the magazines the class feeds from, its own and its muzzles',
          so a consumer can follow a weapon to the round it fires
  ammo    the CfgAmmo class a magazine holds
  damage  what a round does on arrival, the largest of hit, indirectHit
          and explosive. A fire-control entry - a master arm switch, a
          burst limit, a pod inhibit - lives in CfgWeapons and declares
          magazines like any weapon, but nothing it can reach does any
          damage, which is how it is told apart from a weapon
  item_parent the ItemInfo slot item class (`UniformItem`, `VestItem`,
          the optics item). This is the config's own statement of which
          slot the class belongs to.
  item_type the numeric ItemInfo `type` id when the config declares one,
          else null. The NVG root declares 616; most clothing declares
          none and is identified by its slot item class instead.
  optics_modes the OpticsModes a sight offers, empty for a class that is
          not an optic.
  thermal_mode true when any optics mode declares a thermal palette
          (`thermalMode[]`) or the thermal vision mode (`visionMode` holds
          `Ti`), which is what makes an optic a thermal sight.
  fmt     "bin" for a binarised config, "cpp" for raw source. Raw source
          is NOT preprocessed here, so a config built from macros can
          mis-associate a display name: trust "bin" for measurement.

Scan the game and the mods together so a mod display name that reuses
a base-game key still resolves:

    OUT=all.jsonl python3 tools/scan_game_classes.py \
        ".../steamapps/common/Arma 3/Addons" \
        ".../steamapps/workshop/content/107410"
"""

from __future__ import annotations

import json
import os
import re
import struct
import sys
from pathlib import Path

WANT = re.compile(r"(config\.(cpp|bin)|stringtable\.xml)$", re.I)
STR_RE = re.compile(r'<Key ID="([^"]+)"[^>]*>(.*?)</Key>', re.S | re.I)
ENG_RE = re.compile(r"<(?:English|Original)>(.*?)</(?:English|Original)>", re.S | re.I)
ROOTS = ("CfgVehicles", "CfgWeapons", "CfgMagazines", "CfgAmmo")


# ─── PBO container ─────────────────────────────────────────────────────────
def pbo_entries(path: Path):
    """Yield (name, bytes) for the files worth reading, reading only those."""
    with open(path, "rb") as fh:
        index = []
        while True:
            name = b""
            while True:
                ch = fh.read(1)
                if not ch or ch == b"\0":
                    break
                name += ch
            head = fh.read(20)
            if len(head) < 20:
                return
            method, _orig, _res, _time, size = struct.unpack("<5I", head)
            if not name:
                # The first entry may be a PROPERTIES header: its packing
                # method is "Vers" and it is followed by null-terminated
                # key/value pairs, ending with an empty key. The real index
                # starts after those, so they must be consumed, not read as
                # another entry.
                if method == 0x56657273:
                    while True:
                        key = b""
                        while True:
                            ch = fh.read(1)
                            if not ch or ch == b"\0":
                                break
                            key += ch
                        if not key:
                            break
                        val = b""
                        while True:
                            ch = fh.read(1)
                            if not ch or ch == b"\0":
                                break
                            val += ch
                    continue
                break
            index.append((name.decode("utf-8", "replace"), size))
        base = fh.tell()
        offset = 0
        for name, size in index:
            if WANT.search(name.replace("\\", "/")):
                fh.seek(base + offset)
                yield name, fh.read(size)
            offset += size


# ─── rapified config ───────────────────────────────────────────────────────
class Rap:
    def __init__(self, buf: bytes):
        self.b = buf
        self.i = 0

    def u8(self):
        v = self.b[self.i]
        self.i += 1
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.i)[0]
        self.i += 4
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.i)[0]
        self.i += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.b, self.i)[0]
        self.i += 4
        return v

    def comp(self):
        out, shift = 0, 0
        while True:
            c = self.u8()
            out |= (c & 0x7F) << shift
            if not c & 0x80:
                return out
            shift += 7

    def asciiz(self):
        j = self.b.index(b"\0", self.i)
        s = self.b[self.i : j].decode("utf-8", "replace")
        self.i = j + 1
        return s

    def array(self):
        out = []
        for _ in range(self.comp()):
            t = self.u8()
            if t == 0:
                out.append(self.asciiz())
            elif t == 1:
                out.append(self.f32())
            elif t == 2:
                out.append(self.i32())
            elif t == 3:
                out.append(self.array())
        return out

    def body(self, at: int) -> dict:
        """Return {"__children__": {name: offset}, prop: value}."""
        self.i = at
        parent = self.asciiz()  # inherited class
        node: dict = {"__children__": {}, "__parent__": parent}
        for _ in range(self.comp()):
            t = self.u8()
            if t == 0:
                name = self.asciiz()
                node["__children__"][name] = self.u32()
            elif t == 1:
                st = self.u8()
                name = self.asciiz()
                if st == 0:
                    node[name] = self.asciiz()
                elif st == 1:
                    node[name] = self.f32()
                elif st == 2:
                    node[name] = self.i32()
                else:
                    node[name] = None
            elif t == 2:
                name = self.asciiz()
                node[name] = self.array()
            elif t in (3, 4, 5):
                if t == 5:
                    self.u32()
                self.asciiz()
        return node


def parse_rap(buf: bytes):
    r = Rap(buf)
    r.i = 4  # magic
    r.u32()
    r.u32()
    r.u32()  # version, always-8, enum offset
    return r, r.body(r.i)


# ─── plain config.cpp ──────────────────────────────────────────────────────
DN_RE = re.compile(r'displayName\s*=\s*"([^"]*)"')


def cpp_classes(txt: str):
    low = txt.lower()
    for root in ROOTS:
        start = low.find("class " + root.lower())
        while start != -1:
            i = txt.find("{", start)
            if i == -1:
                break
            d, j = 0, i
            while j < len(txt):
                if txt[j] == "{":
                    d += 1
                elif txt[j] == "}":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            body = txt[i:j]
            d, k = 0, 0
            while k < len(body):
                c = body[k]
                if c == "{":
                    d += 1
                elif c == "}":
                    d -= 1
                elif d == 1 and body.startswith("class ", k):
                    m = re.match(
                        r"class\s+([A-Za-z0-9_]+)\s*(?::\s*([A-Za-z0-9_]+))?", body[k:]
                    )
                    if m:
                        e = body.find("{", k)
                        dn = ""
                        if e != -1:
                            dd, p = 0, e
                            while p < len(body):
                                if body[p] == "{":
                                    dd += 1
                                elif body[p] == "}":
                                    dd -= 1
                                    if dd == 0:
                                        break
                                p += 1
                            inner = body[e:p]
                            dd2, q = 0, 0
                            while q < len(inner):
                                if inner[q] == "{":
                                    dd2 += 1
                                elif inner[q] == "}":
                                    dd2 -= 1
                                elif dd2 == 1 and inner.startswith("displayName", q):
                                    mm = DN_RE.match(inner[q:])
                                    if mm:
                                        dn = mm.group(1)
                                        break
                                q += 1
                        yield root, m.group(1), dn, (m.group(2) or ""), "cpp", False
                k += 1
            start = low.find("class " + root.lower(), j)


def scan(path: Path, table: dict):
    rows, strings = [], {}
    for name, data in pbo_entries(path):
        n = name.lower()
        if n.endswith("stringtable.xml"):
            txt = data.decode("utf-8", "replace")
            for key, body in STR_RE.findall(txt):
                m = ENG_RE.search(body)
                if m:
                    strings[key.strip().upper()] = re.sub(
                        r"\s+", " ", m.group(1)
                    ).strip()
        elif n.endswith("config.bin") or (
            n.endswith("config.cpp") and data[:4] == b"\0raP"
        ):
            if data[:4] != b"\0raP":
                continue
            try:
                r, root = parse_rap(data)
                for rootname in ROOTS:
                    off = root["__children__"].get(rootname)
                    if off is None:
                        for k, v in root["__children__"].items():
                            if k.lower() == rootname.lower():
                                off = v
                                break
                    if off is None:
                        continue
                    node = r.body(off)
                    for cls, coff in node["__children__"].items():
                        try:
                            cb = r.body(coff)
                        except Exception:
                            continue
                        # What this class FIRES, read from the config so a
                        # consumer can tell a weapon that launches something
                        # from a fire-control entry that launches nothing.
                        # A weapon hangs its magazines on itself or on its
                        # muzzle subclasses, so both are read.
                        mags = list(cb.get("magazines") or [])
                        for muzzle in cb.get("muzzles") or []:
                            moff = cb["__children__"].get(str(muzzle))
                            if moff is None:
                                continue
                            try:
                                mags.extend(r.body(moff).get("magazines") or [])
                            except Exception:
                                continue
                        rows.append(
                            (
                                rootname,
                                cls,
                                str(cb.get("displayName") or ""),
                                str(cb.get("__parent__") or ""),
                                "bin",
                                # A firearm declares what it feeds from.
                                # CfgWeapons also holds uniforms, vests and
                                # helmets, which never do, so this is what
                                # separates a weapon from a wearable.
                                bool(cb.get("magazines") or cb.get("muzzles")),
                                [str(m) for m in mags],
                                str(cb.get("ammo") or ""),
                                _damage(cb),
                                *_item_info(r, cb),
                            )
                        )
            except Exception:
                continue
        elif n.endswith("config.cpp"):
            try:
                rows.extend(cpp_classes(data.decode("utf-8", "replace")))
            except Exception:
                continue
    local = dict(table)
    local.update(strings)
    out = []
    for row in rows:
        kind, cls, dn, parent, fmt, feeds = row[:6]
        if dn.startswith("$"):
            dn = local.get(dn[1:].upper(), dn)
        rest = tuple(row[6:]) or ([], "", 0.0)
        out.append((kind, cls, dn, parent, fmt, feeds) + tuple(rest))
    return out, strings


def _damage(cb) -> float:
    """What this round does on arrival, as the config states it."""
    out = 0.0
    for field in ("hit", "indirectHit", "explosive"):
        value = cb.get(field)
        if isinstance(value, (int, float)):
            out = max(out, float(value))
    return out


def _item_info(r, cb) -> tuple:
    """The ItemInfo slot declaration of one CfgWeapons class.

    This is the config's own statement of what the class IS as an item:
    the slot item class it inherits (`UniformItem`, `VestItem`, the optics
    item), the numeric `type` id when the config declares one, the optics
    modes it offers, and whether any mode declares a thermal palette.

    The measured tables key on this: without it an optic and a compass are
    both `ItemCore` descendants, and a uniform and a vest are both
    `CfgWeapons` entries with no magazines. Returns
    `(item_parent, item_type, optics_modes, thermal_mode)`; an absent
    ItemInfo is four empty values, never a guess.
    """
    parent, type_id, modes, thermal = "", None, [], False
    off = cb.get("__children__", {}).get("ItemInfo")
    if off is None:
        return parent, type_id, modes, thermal
    try:
        info = r.body(off)
    except Exception:
        return parent, type_id, modes, thermal
    parent = str(info.get("__parent__") or "")
    value = info.get("type")
    if isinstance(value, (int, float)):
        type_id = int(value)
    modes_off = info.get("__children__", {}).get("OpticsModes")
    if modes_off is None:
        return parent, type_id, modes, thermal
    try:
        node = r.body(modes_off)
    except Exception:
        return parent, type_id, modes, thermal
    for name, mode_off in node.get("__children__", {}).items():
        modes.append(str(name))
        try:
            mode = r.body(mode_off)
        except Exception:
            continue
        # Two config statements make a sight thermal: the palette pair
        # (`thermalMode[]`), and the thermal vision mode. Either is the
        # config's own evidence, and no figure is read.
        vision = mode.get("visionMode") or []
        if mode.get("thermalMode") or "Ti" in [str(v) for v in vision]:
            thermal = True
    return parent, type_id, modes, thermal


def collect_strings(pbos) -> dict:
    """Every stringtable in the scanned set, read before any config.

    A mod ships its own stringtable.xml inside its PBOs, and the config
    that uses a key often sits in a DIFFERENT PBO of the same mod, so the
    tables have to be gathered across the whole set first. No separate
    language package is required, and none is assumed.
    """
    table: dict = {}
    for pbo in pbos:
        try:
            for name, data in pbo_entries(pbo):
                if not name.lower().endswith("stringtable.xml"):
                    continue
                txt = data.decode("utf-8", "replace")
                for key, body in STR_RE.findall(txt):
                    m = ENG_RE.search(body)
                    if m:
                        table[key.strip().upper()] = re.sub(
                            r"\s+", " ", m.group(1)
                        ).strip()
        except Exception:
            continue
    return table


def main() -> int:
    # No language package is needed or looked for. Every PBO carries its
    # own stringtable.xml, and pass one below reads them all.
    table: dict = {}
    # Pass one: every stringtable in the whole set, so a key defined in one
    # PBO resolves a display name used in another.
    all_pbos: list[Path] = []
    for target in sys.argv[1:]:
        p = Path(target)
        all_pbos.extend([p] if p.suffix.lower() == ".pbo" else sorted(p.rglob("*.pbo")))
    table.update(collect_strings(all_pbos))

    out = open(os.environ.get("OUT", "classes.jsonl"), "a", encoding="utf-8")
    n = 0
    if True:
        pbos = all_pbos
        for pbo in pbos:
            try:
                rows, _ = scan(pbo, table)
            except Exception:
                continue
            for row in rows:
                kind, cls, dn, parent, fmt, feeds = row[:6]
                rest = (list(row[6:]) + [[], "", 0.0, "", None, [], False])[:7]
                mags, ammo, damage, item_parent, item_type, modes, thermal = rest
                out.write(
                    json.dumps(
                        {
                            "source": pbo.name,
                            "kind": kind,
                            "class": cls,
                            "display": dn,
                            "parent": parent,
                            "fmt": fmt,
                            "feeds": feeds,
                            "magazines": mags,
                            "ammo": ammo,
                            "damage": damage,
                            "item_parent": item_parent,
                            "item_type": item_type,
                            "optics_modes": modes,
                            "thermal_mode": thermal,
                        }
                    )
                    + "\n"
                )
                n += 1
    out.close()
    print(f"rows {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
