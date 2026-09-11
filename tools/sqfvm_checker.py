r"""
Parallel SQFVM checker for AEE — validates all .sqf and config.cpp files
using SQFVM's parse-only mode, with proper AEE virtual path mappings.

Resolves relative includes (e.g. #include "..\script_component.hpp")
before passing to SQFVM, since the native Linux binary doesn't handle
backslash-based relative paths.

Usage:
    python -m tools.sqfvm_checker                      # full check
    python -m tools.sqfvm_checker --verbose             # show all warnings
    python -m tools.sqfvm_checker --skip-configs        # SQF files only
    python -m tools.sqfvm_checker --workers 8           # 8 parallel workers
    python -m tools.sqfvm_checker --file path/to/file   # single file

Returns exit code 0 if no errors, 1 otherwise.
"""

from __future__ import annotations

import concurrent.futures
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict
from pathlib import Path
from tools.proton import find_sqfvm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQFVM_EXE = find_sqfvm()
FILES_TO_IGNORE_LOWER: set[str] = set()

# Virtual path map: {virtual_prefix: real_path}
# Built from VIRTUAL_PATHS format "real_path|virtual_prefix"
VIRTUAL_MAP: dict[str, str] = {}
for vp_entry in [
    f"{PROJECT_ROOT}|/z/aee",
    f"{PROJECT_ROOT / 'include' / 'x' / 'cba'}|/x/cba",
]:
    real, virt = vp_entry.rsplit("|", 1)
    VIRTUAL_MAP[virt.rstrip("/")] = real


def _resolve_virtual(include_path: str) -> str | None:
    """Resolve a virtual path include like \\z\\aee\\addons\\main\\script_mod.hpp
    to an absolute filesystem path using VIRTUAL_MAP."""
    # Convert backslashes to forward slashes
    normalized = include_path.replace("\\", "/")
    # Try each virtual prefix
    for virt_prefix, real_prefix in VIRTUAL_MAP.items():
        if normalized.startswith(virt_prefix + "/") or normalized == virt_prefix:
            rel = normalized[len(virt_prefix) :]
            resolved = Path(real_prefix + rel).resolve()
            if resolved.is_file():
                return str(resolved)
    return None


RE_INCLUDE = re.compile(r'#include\s+"([^"]+)"')


def _find_files(path: Path) -> list[Path]:
    files: list[Path] = []
    addons_root = path / "addons"
    if not addons_root.is_dir():
        print(f"Error: addons/ not found at {addons_root}")
        return files
    for root, _dirs, entries in os.walk(addons_root):
        for entry in entries:
            if not entry.endswith(".sqf") and entry != "config.cpp":
                continue
            if entry.endswith(".inc.sqf"):
                continue
            if entry.lower() in FILES_TO_IGNORE_LOWER:
                continue
            files.append(Path(root) / entry)
    files.sort()
    return files


RE_GUARD_IFNDEF = re.compile(r"^\s*#ifndef\s+(\w+)\s*$")
RE_GUARD_DEFINE = re.compile(r"^\s*#define\s+(\w+)\s*$")
RE_GUARD_ENDIF = re.compile(r"^\s*#endif\s*$")


def _strip_guard(content: str) -> str:
    """Strip a classic include guard (ifndef/define/endif) from content.

    Detects the pattern:
        #ifndef X
        #define X
        ...
        #endif
    where the #ifndef is at or near the top (allowing comment/blank lines)
    and the matching #endif is at or near the bottom.

    Returns content with the three guard lines removed, or the original
    content unchanged if no guard pattern is detected.
    """
    lines = content.split("\n")
    n = len(lines)
    if n < 3:
        return content

    # Find first non-blank, non-comment line
    first_pp = -1
    guard_name: str | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        m = RE_GUARD_IFNDEF.match(line)
        if m:
            first_pp = i
            guard_name = m.group(1)
        break

    if first_pp < 0 or guard_name is None:
        return content

    # Next line must be #define with the same name
    define_pp = -1
    for j in range(first_pp + 1, n):
        stripped = lines[j].strip()
        if not stripped or stripped.startswith("//"):
            continue
        m = RE_GUARD_DEFINE.match(lines[j])
        if m and m.group(1) == guard_name:
            define_pp = j
        break

    if define_pp < 0:
        return content

    # Find last #endif (tracking nesting depth)
    endif_pp = -1
    depth = 1
    for j in range(define_pp + 1, n):
        line = lines[j]
        if (
            re.match(r"^\s*#if\b", line)
            or re.match(r"^\s*#ifdef\b", line)
            or re.match(r"^\s*#ifndef\b", line)
        ):
            depth += 1
        elif re.match(r"^\s*#endif\b", line):
            depth -= 1
            if depth == 0:
                endif_pp = j
                break

    if endif_pp < 0:
        return content
    # Allow trailing blank lines after the guard endif
    non_blank_after = any(l.strip() for l in lines[endif_pp + 1 :])
    if non_blank_after:
        return content  # content after the endif — not a clean guard

    # Remove the three lines
    new_lines = (
        lines[:first_pp]
        + lines[first_pp + 1 : define_pp]
        + lines[define_pp + 1 : endif_pp]
        + lines[endif_pp + 1 :]
    )
    return "\n".join(new_lines)


def _flatten_includes(
    file_path: Path, seen: set[str] | None = None, depth: int = 0
) -> str:
    """Recursively resolve all #include directives into a self-contained file.

    Reads the file, resolves every #include to an absolute path, then
    replaces the directive with the flattened content of the included file.
    This avoids SQFVM's inability to resolve backslash virtual paths.
    Classic include guards (#ifndef X / #define X / ... / #endif) are
    stripped from inlined content since SQF's preprocessor doesn't
    support nested ifndef blocks.
    """
    if depth > 20:
        return f"// RECURSION LIMIT at {file_path}\n"
    if seen is None:
        seen = set()

    abs_path = str(file_path.resolve())
    if abs_path in seen:
        return f"// ALREADY INCLUDED: {file_path.name}\n"
    seen.add(abs_path)

    content = file_path.read_text(encoding="utf-8", errors="ignore")

    # If depth > 0, we're being inlined — strip the include guard
    if depth > 0:
        content = _strip_guard(content)

    lines = content.split("\n")
    out: list[str] = []

    for line in lines:
        m = RE_INCLUDE.match(line)
        if not m:
            out.append(line)
            continue

        inc = m.group(1)
        if inc.startswith("\\"):
            # Virtual path — resolve using VIRTUAL_MAP
            resolved_str = _resolve_virtual(inc)
            if resolved_str:
                included = _flatten_includes(Path(resolved_str), seen, depth + 1)
                out.append(included.rstrip("\n"))
                continue
        else:
            # Relative path — resolve relative to current file
            normalized = inc.replace("\\", "/")
            candidate = (file_path.parent / normalized).resolve()
            if not candidate.is_file() and not candidate.suffix:
                for ext in [".sqf", ".hpp", ".cpp"]:
                    c2 = candidate.with_suffix(ext)
                    if c2.is_file():
                        candidate = c2
                        break
            if candidate.is_file():
                included = _flatten_includes(candidate, seen, depth + 1)
                out.append(included.rstrip("\n"))
                continue

        # Couldn't resolve — keep the original include (SQFVM will error)
        out.append(line)

    return "\n".join(out)


def _skip_compile(content: str) -> bool:
    return "SKIP_COMPILE" in content[:256]


def _run_sqfvm(path: str, verbose: bool = False) -> bool:
    cmd = [str(SQFVM_EXE), "--input", path, "--parse-only", "--automated"]
    # Still pass virtual paths for any remaining non-resolved includes.
    for vp in [
        f"{PROJECT_ROOT}|/z/aee",
        f"{PROJECT_ROOT / 'include' / 'x' / 'cba'}|/x/cba",
        "P:/a3|/a3",
        "P:/a3|/A3",
    ]:
        cmd += ["-v", vp]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        proc.wait(30)
    except subprocess.TimeoutExpired:
        proc.kill()  # type: ignore[union-attr]
        return True
    except Exception as e:
        print(f"  SQFVM error: {e}")
        return True
    has_err = False
    for line in proc.stdout or []:  # type: ignore[union-attr]
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("[ERR]"):
            has_err = True
            print(f"  {line}")
        elif line.startswith("[WRN]"):
            if "a3/" in line and (
                "Unexpected IFDEF" in line or "defined twice" in line
            ):
                continue
            if "Unknown pragma instruction 'hemtt'" in line:
                continue
            if verbose:
                print(f"  {line}")
        elif verbose:
            print(f"  {line}")
    return has_err


def _check_file(file_path: Path, verbose: bool = False) -> bool:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if _skip_compile(content):
        return False
    preprocessed = _flatten_includes(file_path)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=file_path.suffix, delete=False, encoding="utf-8"
    ) as f:
        f.write(preprocessed)
        tmp = f.name
    try:
        return _run_sqfvm(tmp, verbose=verbose)
    finally:
        os.unlink(tmp)


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p)


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="AEE SQFVM checker")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--skip-configs", action="store_true")
    p.add_argument("--workers", "-w", type=int, default=12)
    p.add_argument("--file", "-f", type=str)
    p.add_argument(
        "--allow-missing",
        action="store_true",
        help="Return 0 (pass) if SQFVM binary is not installed",
    )
    a = p.parse_args()
    if not SQFVM_EXE or not os.path.isfile(SQFVM_EXE):
        if a.allow_missing:
            print("SQFVM not found — skipping (--allow-missing).")
            return 0
        print("Error: SQFVM not found.")
        return 1
    files = [Path(a.file).resolve()] if a.file else _find_files(PROJECT_ROOT)
    if a.skip_configs:
        files = [f for f in files if f.suffix == ".sqf"]
    if not files:
        print("No files.")
        return 0
    print(f"SQFVM: {SQFVM_EXE}\nFiles: {len(files)}")
    start = time.time()
    errs = 0
    ok = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        fm = {ex.submit(_check_file, f, verbose=a.verbose): f for f in files}
        for fut in concurrent.futures.as_completed(fm):
            f = fm[fut]
            try:
                if fut.result():
                    errs += 1
                    print(f"  ERR {rel(f)}")
                else:
                    ok += 1
            except Exception as e:
                print(f"  EXC {rel(f)}: {e}")
                errs += 1
    t = time.time() - start
    print(f"\nResults: {ok} OK, {errs} ERRORS  ({t:.1f}s)")
    return 1 if errs > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
