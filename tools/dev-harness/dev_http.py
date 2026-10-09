#!/usr/bin/env python3
"""Tiny loopback client for the dev console, used by docker_test.sh --console.

Commands:
    dev_http.py health PORT               GET /health, print the body.
    dev_http.py post PORT TOKEN OP ARG... POST /command, print the reply body.
Each ARG is one string element of the JSON args array.
"""

from __future__ import annotations

import json
import sys
import urllib.request


def health(port: int) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
            sys.stdout.write(r.read().decode("utf-8", "replace"))
        return 0
    except Exception:  # noqa: BLE001 - any failure means the listener is not up
        return 1


def post(port: int, token: str, op: str, args: list[str]) -> int:
    body = json.dumps({"op": op, "id": 1, "args": args, "token": token}).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/command",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            sys.stdout.write(r.read().decode("utf-8", "replace"))
        return 0
    except Exception:  # noqa: BLE001 - a refused or timed-out call is a failure
        return 1


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "health":
        return health(int(argv[2]))
    if len(argv) >= 5 and argv[1] == "post":
        return post(int(argv[2]), argv[3], argv[4], argv[5:])
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
