#!/usr/bin/env python3
"""Validate the engine override programme.

Checks the verdict register, the generated headers and the emitted values:

  * every surface in the register carries a verdict and a reason;
  * every REJECT names a ceiling;
  * every implemented surface owns a key that is present in its header;
  * no emitted class is a bare reopen (every class restates its parent);
  * the generated register document matches data/engine/verdicts.json.

Run: python3 tools/validation/validate_engine_overrides.py
Exit 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import gen_engine_overrides as gen  # noqa: E402

_BARE_CLASS = re.compile(r"^\s+class\s+[A-Za-z0-9_]+\s*\{\s*$")
_BODY_CLASS = re.compile(r"^\s+class\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)\s*\{\s*$")


def _validate_register(verdicts: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for record in verdicts:
        surface_id = record["id"]
        verdict = record["verdict"]
        reason = record.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"{surface_id}: no reason recorded")
        if verdict in ("RECONCILE", "REJECT"):
            source = record.get("source")
            if not isinstance(source, str) or not source.strip():
                errors.append(f"{surface_id}: {verdict} with no source note")
        if verdict == "REJECT":
            ceiling = record.get("ceiling")
            if not isinstance(ceiling, str) or not ceiling.strip():
                errors.append(f"{surface_id}: REJECT with no ceiling")
    return errors


def _headers() -> dict[str, str]:
    return {
        "CfgMagazines": gen.MAG_OUT.read_text(encoding="utf-8"),
        "CfgAmmo": gen.AMMO_OUT.read_text(encoding="utf-8"),
    }


def _validate_implemented(
    verdicts: list[dict[str, object]], headers: dict[str, str]
) -> list[str]:
    errors: list[str] = []
    implemented = gen.implemented_keys(verdicts)
    if not implemented:
        errors.append("no implemented surface in the register")
    for surface_id, (config_class, key) in implemented.items():
        header = headers.get(config_class)
        if header is None:
            errors.append(f"{surface_id}: unknown config class {config_class}")
            continue
        if f"class {config_class} {{" not in header:
            errors.append(f"{surface_id}: {config_class} block missing")
        if f"{key} = " not in header:
            errors.append(f"{surface_id}: key {key} not emitted in {config_class}")
    return errors


def _validate_no_bare_reopen(headers: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for config_class, header in headers.items():
        bodies = 0
        for line in header.splitlines():
            if _BARE_CLASS.match(line):
                errors.append(f"{config_class}: bare reopen {line.strip()}")
            elif _BODY_CLASS.match(line):
                bodies += 1
        if bodies == 0:
            errors.append(f"{config_class}: no class body emitted")
    return errors


def _validate_register_document(verdicts: list[dict[str, object]]) -> list[str]:
    if not gen.REGISTER_OUT.is_file():
        return [f"{gen.REGISTER_OUT}: the register document is missing"]
    expected = gen.render_register(verdicts)
    if gen.REGISTER_OUT.read_text(encoding="utf-8") != expected:
        return [f"{gen.REGISTER_OUT}: stale; run the generator"]
    return []


def main() -> int:
    errors: list[str] = []
    try:
        verdicts = gen.load_verdicts()
    except (OSError, ValueError) as exc:
        print(f"engine overrides: cannot load the register: {exc}")
        return 1
    headers = _headers()
    errors += _validate_register(verdicts)
    errors += _validate_implemented(verdicts, headers)
    errors += _validate_no_bare_reopen(headers)
    errors += _validate_register_document(verdicts)
    if errors:
        print("engine overrides: FAILED")
        for item in errors:
            print(f"  - {item}")
        return 1
    print(f"engine overrides: {len(verdicts)} surfaces, register and headers OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
