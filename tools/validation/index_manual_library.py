#!/usr/bin/env python3
"""Index the archive.org manual library.

The item manuals.content.like.stevespages holds thousands of scanned
firearm manuals and maker catalogues. The value is a held document when a
model needs a value that no current maker page carries: the mass, the
chambering, and sometimes the twist of a discontinued or historical arm.

The OCR text is usable for most documents but not all, and the tables in
an old catalogue read badly, so the library is mined on demand for a
named model and the extracted line is verified before it enters the
database. This tool writes the index that makes that lookup possible: the
base URLs once, and the document stems.

Run:  python3 tools/validation/index_manual_library.py
"""

import json
import subprocess
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = DATA / "sources" / "manual_library.json"
ITEM = "manuals.content.like.stevespages"


def main():
    url = f"https://archive.org/metadata/{ITEM}"
    raw = subprocess.run(
        ["curl", "-sL", "--max-time", "90", "-A", "Mozilla/5.0", url],
        capture_output=True,
        text=True,
    ).stdout
    meta = json.loads(raw)
    files = meta.get("files", [])
    pdfs = sorted({f["name"][:-4] for f in files if f["name"].lower().endswith(".pdf")})
    ocr = {f["name"][:-9] for f in files if f["name"].endswith("_djvu.txt")}
    documents = [
        {
            "stem": stem,
            "pdf": f"{stem}.pdf",
            "ocr_text": stem in ocr,
        }
        for stem in pdfs
    ]
    OUT.write_text(
        json.dumps(
            {
                "item": ITEM,
                "metadata_url": url,
                "download_base": f"https://archive.org/download/{ITEM}/",
                "note": (
                    "A held document when a history check is needed. The OCR "
                    "text is usable for most documents and rubbish for a few, "
                    "and a table in an old catalogue reads badly, so a value "
                    "is mined for a named model and then verified."
                ),
                "documents": documents,
                "counts": {
                    "documents": len(documents),
                    "with_ocr_text": sum(1 for d in documents if d["ocr_text"]),
                },
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"manual library: {len(documents)} documents "
        f"({sum(1 for d in documents if d['ocr_text'])} with OCR text), "
        f"wrote {OUT.name} ({OUT.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    main()
