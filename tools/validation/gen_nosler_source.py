#!/usr/bin/env python3
"""Build data/ballistics/sources/nosler_velocity.json from Nosler load data.

Nosler publishes one load data sheet per cartridge and bullet-weight group at
nosler.com/load-data. Each sheet prints a test barrel length and a powder
table with a muzzle velocity per charge. The sheet header lists the bullets
the sheet covers, so a velocity is cited for a bullet that the sheet names.

The captured PDFs are not distributed. They are joined in a fixed order into
one bundle, held in the machine-local source cache, and identified by its
sha256. A sidecar manifest in the cache records each sheet's own sha256.

  python3 tools/validation/gen_nosler_source.py --fetch [--papers DIR]
  python3 tools/validation/gen_nosler_source.py

--fetch downloads the cartridge pages and their load data sheets into the
papers directory: the caliber index names each cartridge page, and each
cartridge page links its sheets. A later run needs no network.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation.source_cache import capture_path  # noqa: E402
from tools.validation.verify_ballistics import mass_gr  # noqa: E402

DATA = REPO / "data" / "ballistics"
OUT = DATA / "sources" / "nosler_velocity.json"
BUNDLE = "nosler/load_data_sheets_v9.tar"
INDEX_URL = "https://www.nosler.com/load-data/caliber-and-cartridge-data.html"
SHEET_URL = "https://www.nosler.com/media/load_data_assets/pdfs/"

# Sheet bullet abbreviation -> (product words required in the record name,
# words that disqualify it). Profile words are added on top of these.
MODELS = {
    "AB": (("accubond",), ("long", "range")),
    "ABLR": (("accubond", "long", "range"), ()),
    "BT": (("ballistic", "tip"), ("varmint", "lead", "free", "silvertip")),
    "BTV": (("ballistic", "tip", "varmint"), ()),
    "BTLF": (("ballistic", "tip", "lead"), ()),
    "BST": (("silvertip",), ()),
    "CC": (("custom", "competition"), ()),
    "ET": (("e", "tip"), ("ballistic",)),
    "RDF": (("rdf",), ()),
    "PT": (("partition",), ()),
    "BSB": (("solid", "base"), ()),
    "SD": (("solid",), ()),
    "SHG": (("sporting", "handgun"), ()),
}

PROFILES = {
    "spitzer": ("spitzer",),
    "semi-spitzer": ("semi", "spitzer"),
    "hpbt": ("hpbt",),
    "ppt": ("protected", "point"),
    "jhp": ("jhp",),
    "jsp": ("jsp",),
    "solid": ("solid",),
    "rn": ("round", "nose"),
    "rnbt": ("round", "nose"),
    "fbhp": ("fbhp",),
    "fb tipped": ("fb", "tipped"),
    "fmj": ("fmj",),
}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t}


def value(rec: dict, key: str):
    """Return one record value's number, or None."""
    entry = rec.get("values", {}).get(key)
    return entry.get("value") if isinstance(entry, dict) else None


def barrel_inches(text: str) -> float:
    """Return a barrel length in inches from "24", "8-1/4" or "20.5"."""
    if "-" in text:
        whole, fraction = text.split("-", 1)
        top, bottom = fraction.split("/")
        return float(whole) + float(top) / float(bottom)
    return float(text)


def resolve_cartridge(title: str, index: dict) -> tuple[str, str] | None:
    """Return the cartridge record that a sheet title names, or None.

    Only exact matches after a mechanical clean-up are accepted: a trailing
    qualification in brackets, a trailing action word, or the multiplication
    sign in place of an x.
    """
    candidates = [
        title,
        re.sub(r"\s*\([^)]*\)\s*$", "", title),
        re.sub(r"\s+(?:Handgun|Mauser)$", "", title),
        title.replace("\u00d7", "x"),
    ]
    for candidate in candidates:
        hit = index.get(norm(candidate))
        if hit:
            return hit
    return None


def curl(url: str, target: Path) -> None:
    """Write one URL to a file unless the file already holds bytes."""
    if target.exists() and target.stat().st_size > 1024:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "curl",
            "-sS",
            "-A",
            "Mozilla/5.0",
            "--compressed",
            "-L",
            "--max-time",
            "120",
            url,
            "-o",
            str(target),
        ],
        check=True,
    )


def fetch(papers: Path) -> None:
    """Download every cartridge page and load data sheet."""
    index = papers / "index.html"
    curl(INDEX_URL, index)
    links = sorted(
        set(
            re.findall(
                r'href="https://www\.nosler\.com/([a-z0-9-]+)"',
                index.read_text(encoding="utf-8", errors="replace"),
            )
        )
    )
    for slug in links:
        curl(f"https://www.nosler.com/{slug}", papers / "pages" / f"{slug}.html")
    for page in sorted((papers / "pages").glob("*.html")):
        markup = page.read_text(encoding="utf-8", errors="replace")
        for sheet in set(re.findall(r"load_data_assets/pdfs/([^\"]*\.pdf)", markup)):
            pdf = papers / "pdfs" / sheet
            curl(SHEET_URL + sheet, pdf)
            text = papers / "txt" / (pdf.stem + ".txt")
            if not text.exists():
                text.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["pdftotext", "-layout", str(pdf), str(text)], check=True
                )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sheet(text: str) -> dict | None:
    barrel = re.search(
        r'BARREL Length/Make\s+(\d+(?:-\d+/\d+)?(?:\.\d+)?)"\s*(\S+)', text
    )
    header = re.search(r"^(.+?)\s+-\s+([\d/]+)\s*grain\b", text, re.M)
    calibre = re.search(r"([\d.]+\s*(?:mm|Cal\.))\s*\(([\d.]+)\"\)", text)
    if not barrel or not header:
        return None
    velocities = []
    for line in text.splitlines():
        hit = re.search(r"\d+\.\d+\s+\*?\s*(MAX\.)?\s*(\d{3,4})\s", line)
        if hit:
            velocities.append((int(hit.group(2)), bool(hit.group(1))))
    max_rows = [v for v, is_max in velocities if is_max]
    if not max_rows:
        return None
    bullets = []
    head = text.split("CASE TYPE")[0]
    for hit in re.finditer(
        r"([A-Z]{2,5})\s+(\d+(?:\.\d+)?)\s*gr\.\s+([A-Za-z][A-Za-z/ -]*?)\s+(?=[\d.]+\")",
        head,
    ):
        profile = hit.group(3).strip().lower()
        if profile not in PROFILES:
            continue
        bullets.append((hit.group(1), float(hit.group(2)), profile))
    if not bullets:
        return None
    return {
        "cartridge": header.group(1).strip(),
        "barrel_mm": round(barrel_inches(barrel.group(1)) * 25.4, 1),
        "barrel_make": barrel.group(2),
        "velocity_ms": round(max(max_rows) * 0.3048, 1),
        "velocity_fps": max(max_rows),
        "diameter_mm": round(float(calibre.group(2)) * 25.4, 4) if calibre else None,
        "bullets": bullets,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--papers",
        default=str(capture_path("ballistics", "nosler/papers")),
        help="directory holding the fetched cartridge pages and sheets",
    )
    ap.add_argument("--skip-capture", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()
    papers = Path(args.papers)
    if args.fetch:
        fetch(papers)

    cart_by_name: dict[str, tuple[str, str]] = {}
    for rec in json.loads((DATA / "cartridges.json").read_text(encoding="utf-8")):
        for name in rec.get("names", []):
            cart_by_name[norm(name)] = (rec["cartridge_id"], name)

    projectiles = [
        rec
        for rec in json.loads((DATA / "projectiles.json").read_text(encoding="utf-8"))
        if (rec.get("manufacturer") or "").lower() == "nosler"
    ]

    # Sheet -> cartridge, taken from the page that linked the sheet.
    page_of_sheet: dict[str, str] = {}
    for page in sorted((papers / "pages").glob("*.html")):
        markup = page.read_text(encoding="utf-8", errors="replace")
        title = re.search(r"<title>([^<]*)</title>", markup)
        if not title:
            continue
        name = html.unescape(re.sub(r"\s*Load Data.*$", "", title.group(1)).strip())
        for pdf in re.findall(r"load_data_assets/pdfs/([^\"]*\.pdf)", markup):
            page_of_sheet[pdf] = name

    sheets = []
    for pdf in sorted((papers / "pdfs").glob("*.pdf")):
        if "archived" in pdf.name.lower():
            continue
        text = (papers / "txt" / (pdf.stem + ".txt")).read_text(
            encoding="utf-8", errors="replace"
        )
        parsed = parse_sheet(text)
        if parsed is None:
            continue
        name = page_of_sheet.get(pdf.name, "")
        resolved = resolve_cartridge(name, cart_by_name)
        if resolved is None:
            continue
        cartridge_id, canonical = resolved
        parsed.update(pdf=pdf, cartridge_name=canonical, cartridge_id=cartridge_id)
        sheets.append(parsed)

    loads = []
    used: set[tuple[str, str]] = set()
    for sheet in sheets:
        sheet["sha256"] = sha256(sheet["pdf"])
        for abbr, mass, profile in sheet["bullets"]:
            if abbr not in MODELS:
                continue
            want, refuse = MODELS[abbr]
            want = want + PROFILES[profile]
            for rec in projectiles:
                if abs((mass_gr(rec) or 0) - mass) > 0.6:
                    continue
                diameter = value(rec, "diameter_mm")
                if sheet["diameter_mm"] is None or diameter is None:
                    continue
                if abs(diameter - sheet["diameter_mm"]) > 0.06:
                    continue
                words = tokens(" ".join(rec.get("names", [])))
                if not set(want) <= words or set(refuse) & words:
                    continue
                name = rec["names"][0]
                model = re.search(r"\bGr\.\s*(.+)$", name)
                if not model:
                    continue
                design = f"{mass:g} gr {model.group(1).strip()}"
                key = (sheet["cartridge_id"], design.lower())
                if key in used:
                    continue
                used.add(key)
                loads.append(
                    {
                        "cartridge": sheet["cartridge_name"],
                        "projectile": design,
                        "barrel_mm": sheet["barrel_mm"],
                        "velocity_ms": sheet["velocity_ms"],
                        "source_locator": (
                            f"{SHEET_URL}{sheet['pdf'].name} p.1, "
                            f"{sheet['cartridge_name']} {mass:g} grain group, "
                            f"row of the fastest MAX charge"
                        ),
                        "source_note": (
                            f"Nosler load data sheet {sheet['pdf'].name} "
                            f"(version 9.0), test barrel "
                            f"{sheet['barrel_mm'] / 25.4:g} in {sheet['barrel_make']}; "
                            f"velocity is the sheet's fastest MAX charge figure for the "
                            f"{mass:g} grain group, which lists this bullet; "
                            f"sheet sha256={sheet['sha256']}"
                        ),
                    }
                )

    loads.sort(key=lambda r: (r["cartridge"], r["projectile"]))

    if not args.skip_capture:
        bundle = capture_path("ballistics", BUNDLE)
        bundle.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "tar",
                "--sort=name",
                "--mtime=@0",
                "--owner=0",
                "--group=0",
                "--numeric-owner",
                "-cf",
                str(bundle),
                "-C",
                str(papers / "pdfs"),
                *[s["pdf"].name for s in sheets],
            ],
            check=True,
        )
        manifest = {
            "bundle_sha256": sha256(bundle),
            "sheets": {s["pdf"].name: sha256(s["pdf"]) for s in sheets},
        }
        bundle.with_suffix(".manifest.json").write_text(
            json.dumps(manifest, indent=1) + "\n", encoding="utf-8"
        )
        digest = manifest["bundle_sha256"]
    else:
        digest = ""

    record = {
        "url": INDEX_URL,
        "retrieved": "2026-10-23",
        "sha256": digest,
        "capture": "local-cache-only",
        "capture_path": BUNDLE,
        "note": (
            f"Nosler load data, {len(sheets)} single-page sheets from "
            f"nosler.com/load-data (version 9.0), one sheet per cartridge and "
            f"bullet-weight group; each sheet prints its own test barrel "
            f"({round(min(s['barrel_mm'] for s in sheets) / 25.4, 1):g} in to "
            f"{round(max(s['barrel_mm'] for s in sheets) / 25.4, 1):g} in) and a muzzle "
            f"velocity per powder charge; sha256 is of a tar of the sheet PDFs in "
            f"filename order, per-sheet hashes are in each load's source_note"
        ),
        "loads": loads,
    }
    OUT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(f"sheets={len(sheets)} loads={len(loads)} sha256={digest[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
