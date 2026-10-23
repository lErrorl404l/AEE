#!/usr/bin/env python3
"""Merge the drag function tables into one held set.

data/ballistics/sources/drag_functions.json holds the small arms
standard curves. drag_functions_extra.json holds the others that research
found. The simulation loads one set, so the two are merged here with the
source of every model recorded.

Run:  python3 tools/validation/merge_drag_functions.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
MAIN = SRC / "drag_functions.json"
EXTRA = SRC / "drag_functions_extra.json"

# A cannon label that reuses a held curve because no measured curve of its
# own is held. It is never presented as a sourced model.
PLACEHOLDERS = {
    "APFSDS": {
        "reuses": "SCHAPIRO",
        "note": "The APFSDS label reuses the SCHAPIRO curve. No measured APFSDS drag curve is held, so the model carries no source of its own.",
    },
}


def main():
    main_file = json.loads(MAIN.read_text(encoding="utf-8"))
    models = dict(main_file["models"])
    placeholders = dict(main_file.get("placeholder_models") or {})
    placeholders.update(PLACEHOLDERS)
    sources = {
        name: main_file["url"] for name in models if name not in placeholders
    }
    added = []
    if EXTRA.exists():
        extra = json.loads(EXTRA.read_text(encoding="utf-8"))
        for name, points in extra["models"].items():
            if name in models:
                continue
            models[name] = points
            sources[name] = extra["url"]
            added.append(name)
    merged = {
        "url": main_file["url"],
        "retrieved": main_file["retrieved"],
        "sha256": main_file["sha256"],
        "note": main_file.get("note", ""),
        "sources": sources,
        "placeholder_models": placeholders,
        "models": dict(sorted(models.items())),
    }
    MAIN.write_text(json.dumps(merged, indent=1) + "\n", encoding="utf-8")
    print(f"drag models held: {len(models)} ({', '.join(sorted(models))})")
    print(f"added from the extra set: {', '.join(added) if added else 'none'}")


if __name__ == "__main__":
    main()
