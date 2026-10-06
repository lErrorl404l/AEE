#!/usr/bin/env python3
"""Derive per-run isolation for the headless Docker test.

Two runs of the Arma 3 dedicated server test share one host.  A run that
reuses the compose project name captures the other run's container, and a
run that reuses the game port fights for the same socket.  This module
derives, for one run, a unique compose project name, a unique profile name,
a unique run directory, and a free game-port block.  The derivation is pure,
so the shell harness and its unit test share one source of truth.

Command line:
    docker_run_isolation.py resolve --docker DIR --root-name NAME [--pid N]
        [--run-id ID] [--run-dir DIR] [--port N] [--profile NAME] [--slot N]
    docker_run_isolation.py port --run-id ID [--slot N] [--reserve A,B]

`resolve` prints shell assignments for the harness to evaluate.  The port
block is `slot` consecutive ports, because the server binds the game port
and the ports above it (Steam query and friends).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import socket
import sys
import zlib

# Compose project names match [a-z0-9][a-z0-9_-]*.  Arma profile names are
# used as a directory name, so keep them alphanumeric.
PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
PROFILE_RE = re.compile(r"^[A-Za-z0-9_]+$")

PORT_LOW = 2312
PORT_SPAN = 600
PORT_SLOT = 10


def sanitize_id(text: str, limit: int = 24) -> str:
    """Lowercase a name and reduce every other run of characters to '-'.

    The result is a valid compose project fragment: it starts with an
    alphanumeric and holds only [a-z0-9_-].
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:limit].strip("-")
    return slug or "run"


def derive_run_id(root_name: str, pid: int, salt: str = "") -> str:
    """A run id from the worktree name and the process id.

    Two concurrent shells have different process ids, so the id is unique on
    one host without a lock.
    """
    rid = f"{sanitize_id(root_name)}-{pid}"
    if salt:
        rid = f"{rid}-{sanitize_id(salt, 12)}"
    return rid[:48].strip("-") or "run"


def project_name(run_id: str) -> str:
    name = f"aee-{sanitize_id(run_id, 40)}"
    if not PROJECT_RE.match(name):
        raise ValueError(f"invalid compose project name: {name!r}")
    return name[:63]


def profile_name(run_id: str) -> str:
    """A stable, collision-free Arma profile name for one run id."""
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:10]
    return f"aee{digest}"


def run_dir(docker_dir: str, run_id: str) -> str:
    return os.path.join(docker_dir, "runs", sanitize_id(run_id, 48))


def _slot_candidates(run_id: str, slot: int = PORT_SLOT):
    start = zlib.crc32(run_id.encode("utf-8")) % PORT_SPAN
    for step in range(PORT_SPAN):
        yield PORT_LOW + ((start + step) % PORT_SPAN) * slot


def is_free_port(port: int, slot: int = PORT_SLOT) -> bool:
    """True when every UDP port in [port, port+slot) can be bound."""
    socks = []
    try:
        for offset in range(slot):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", port + offset))
            socks.append(sock)
        return True
    except OSError:
        return False
    finally:
        for sock in socks:
            sock.close()


def allocate_port(
    run_id: str,
    is_free=is_free_port,
    slot: int = PORT_SLOT,
    reserved=(),
) -> int:
    """The first free port block for a run, skipping reserved blocks."""
    taken = set(reserved)
    for base in _slot_candidates(run_id, slot):
        if base in taken:
            continue
        if is_free(base, slot):
            return base
    raise RuntimeError(f"no free port block for run id {run_id!r}")


def resolve(
    *,
    docker_dir: str,
    root_name: str,
    pid: int,
    run_id: str | None = None,
    run_dir_: str | None = None,
    port: int | None = None,
    profile: str | None = None,
    slot: int = PORT_SLOT,
    is_free=is_free_port,
) -> dict[str, str]:
    rid = sanitize_id(run_id, 48) if run_id else derive_run_id(root_name, pid)
    if not rid:
        rid = derive_run_id(root_name, pid)
    if port is None:
        port = allocate_port(rid, is_free=is_free, slot=slot)
    return {
        "AEE_RUN_ID": rid,
        "COMPOSE_PROJECT_NAME": project_name(rid),
        "AEE_PROFILE": profile or profile_name(rid),
        "AEE_RUN_DIR": run_dir_ or run_dir(docker_dir, rid),
        "AEE_GAME_PORT": str(port),
        "AEE_PORT_SLOT": str(slot),
    }


def _cmd_resolve(args: argparse.Namespace) -> int:
    values = resolve(
        docker_dir=args.docker,
        root_name=args.root_name,
        pid=args.pid,
        run_id=args.run_id,
        run_dir_=args.run_dir,
        port=args.port,
        profile=args.profile,
        slot=args.slot,
    )
    for key, value in values.items():
        print(f"{key}={shlex.quote(value)}")
    return 0


def _cmd_port(args: argparse.Namespace) -> int:
    reserved = [int(p) for p in args.reserve.split(",") if p.strip()]
    print(allocate_port(args.run_id, slot=args.slot, reserved=reserved))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    res = sub.add_parser("resolve", help="print shell assignments for one run")
    res.add_argument("--docker", required=True, help="the tests/docker directory")
    res.add_argument("--root-name", required=True, help="worktree directory name")
    res.add_argument("--pid", type=int, default=os.getpid())
    res.add_argument("--run-id")
    res.add_argument("--run-dir", dest="run_dir")
    res.add_argument("--port", type=int)
    res.add_argument("--profile")
    res.add_argument("--slot", type=int, default=PORT_SLOT)
    res.set_defaults(func=_cmd_resolve)

    port = sub.add_parser("port", help="print one free port block base")
    port.add_argument("--run-id", required=True)
    port.add_argument("--slot", type=int, default=PORT_SLOT)
    port.add_argument("--reserve", default="", help="comma separated bases to skip")
    port.set_defaults(func=_cmd_port)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
