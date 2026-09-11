#!/usr/bin/env python3
"""Assemble a CycloneDX SBOM for the AEE repository.

Run: python3 tools/make_sbom.py [output.json]

The only third-party code in the repository is the vendored CBA header
copies under include/x/cba, pinned to a recorded CBA_A3 commit. The build
toolchain is HEMTT. AEE's own tooling uses the Python standard library
only, so no further dependency entries exist.
"""

import json
import sys
from datetime import datetime, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "sbom.cdx.json"

CBA_SHA = "6b37925af487eda786ca360300b8fe48ae9c7e33"

doc = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": {"type": "application", "name": "AEE", "version": "1.0.0"},
    },
    "components": [
        {
            "type": "library",
            "name": "CBA_A3",
            "version": CBA_SHA,
            "purl": f"pkg:github/CBATeam/CBA_A3@{CBA_SHA}",
            "licenses": [{"license": {"id": "GPL-2.0-or-later"}}],
            "description": "Vendored macro headers under include/x/cba, copied unmodified for HEMTT preprocessing.",
            "scope": "required",
        },
        {
            "type": "application",
            "name": "HEMTT",
            "version": "1.21.0",
            "purl": "pkg:github/BrettMayson/HEMTT",
            "licenses": [{"license": {"id": "GPL-2.0-or-later"}}],
            "description": "Build and release toolchain.",
            "scope": "required",
        },
    ],
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print(f"SBOM written to {OUT}")
