#!/usr/bin/env python3
"""Fail loudly when the open-file limit cannot hold the HEMTT build.

HEMTT holds approximately one file descriptor per file it packs and keeps
the handle open until the addon is written.  Measured on this tree: a peak
of 5,660 descriptors for the 5,516 marker .paa files, identical with
`hemtt build --threads 1`, so the requirement follows the file count and not
thread concurrency.  The optics addon alone holds the marker set, and the
markers are the product, so the build needs a soft `nofile` limit well above
the usual default (Docker ships 2048).

The requirement is computed from the current tree, so it scales with the
marker set.  `tools/hemtt.sh` raises the soft limit first and calls this to
assert the result.  A low hard limit fails loudly here instead of dying with
`os error 24` part-way through the pack.

Run:  python3 tools/check_fd_limit.py
Exit 0 when the limit is adequate, 1 when it is not.
"""

import resource
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADDONS = REPO / "addons"

# Headroom above the packed file count for HEMTT's own descriptors, the
# build output, wine and any concurrent addon packing.
HEADROOM = 4096


def packed_file_count(root: Path = ADDONS) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def required_limit(files: int) -> int:
    return files + HEADROOM


def is_adequate(soft: int, required: int) -> bool:
    return soft >= required


def soft_limit() -> int:
    soft, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft == resource.RLIM_INFINITY:
        return sys.maxsize
    return soft


def main() -> int:
    files = packed_file_count()
    required = required_limit(files)
    current = soft_limit()
    if not is_adequate(current, required):
        print(
            f"fd limit: FAIL: soft nofile limit {current} is below the "
            f"{required} needed to pack {files} files.  HEMTT holds about one "
            "descriptor per packed file, and the markers are the product."
        )
        print(
            "Fix: run the build through tools/hemtt.sh, or raise the limit in "
            f"the build shell (`ulimit -n {required}`).  A container needs "
            "`ulimits: nofile:` (see tests/docker/docker-compose.yml)."
        )
        return 1
    print(f"fd limit: PASS ({current} >= {required} for {files} packed files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
