#!/usr/bin/env python3
"""Unit tests for the Docker test run isolation helper.

The helper derives a unique compose project, profile, run directory and
game-port block per run.  These tests assert the derivation is unique and
non-overlapping, so two concurrent Docker runs cannot capture each other's
container, port or logs.

Run: python3 -m unittest tools.tests.test_docker_isolation -v
"""

import re
import unittest
from pathlib import Path

import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

import docker_run_isolation as iso  # noqa: E402


class TestRunId(unittest.TestCase):
    def test_distinct_pids_give_distinct_ids(self):
        ids = {iso.derive_run_id("AEE", pid) for pid in range(1000, 1100)}
        self.assertEqual(len(ids), 100)

    def test_id_is_a_valid_compose_fragment(self):
        rid = iso.derive_run_id("Weird Worktree Name!", 42)
        self.assertRegex(rid, r"^[a-z0-9][a-z0-9-]*$")

    def test_same_inputs_give_same_id(self):
        self.assertEqual(iso.derive_run_id("aee", 7), iso.derive_run_id("aee", 7))


class TestNames(unittest.TestCase):
    def test_project_name_matches_compose_rules(self):
        for rid in ("aee-1", "AEE/odd name", "x" * 80, "run_9"):
            self.assertRegex(iso.project_name(rid), iso.PROJECT_RE)

    def test_profile_name_matches_profile_rules(self):
        for rid in ("aee-1", "AEE/odd name", "x" * 80, "run_9"):
            self.assertRegex(iso.profile_name(rid), iso.PROFILE_RE)

    def test_distinct_ids_give_distinct_projects_and_profiles(self):
        rids = [f"run-{i}" for i in range(200)]
        projects = {iso.project_name(r) for r in rids}
        profiles = {iso.profile_name(r) for r in rids}
        self.assertEqual(len(projects), len(rids))
        self.assertEqual(len(profiles), len(rids))


class TestRunDir(unittest.TestCase):
    def test_distinct_ids_give_distinct_dirs(self):
        docker = "/repo/tests/docker"
        dirs = {iso.run_dir(docker, f"run-{i}") for i in range(50)}
        self.assertEqual(len(dirs), 50)
        for d in dirs:
            self.assertTrue(d.startswith(docker + "/runs/"))


class TestPorts(unittest.TestCase):
    def test_allocator_skips_reserved_blocks(self):
        first = iso.allocate_port("id", is_free=lambda p, s: True)
        second = iso.allocate_port("id", is_free=lambda p, s: True, reserved=[first])
        self.assertNotEqual(first, second)

    def test_allocated_block_is_inside_the_range_and_aligned(self):
        port = iso.allocate_port("some-run", is_free=lambda p, s: True)
        self.assertGreaterEqual(port, iso.PORT_LOW)
        self.assertLess(port, iso.PORT_LOW + iso.PORT_SPAN * iso.PORT_SLOT)
        self.assertEqual((port - iso.PORT_LOW) % iso.PORT_SLOT, 0)

    def test_allocator_honours_a_busy_block(self):
        base = iso.allocate_port("busy-run", is_free=lambda p, s: True)
        # Mark the first candidate busy; the allocator must move on.
        calls = []

        def free(p, s):
            calls.append(p)
            return p != base

        chosen = iso.allocate_port("busy-run", is_free=free)
        self.assertNotEqual(chosen, base)
        self.assertEqual(calls[0], base)

    def test_concurrent_blocks_do_not_overlap(self):
        # The parent reserves each block before the next allocation, so the
        # blocks handed to concurrent runs are disjoint.
        reserved = []
        blocks = []
        for i in range(20):
            port = iso.allocate_port(
                f"job-{i}", is_free=lambda p, s: True, reserved=reserved
            )
            reserved.append(port)
            blocks.append(set(range(port, port + iso.PORT_SLOT)))
        for i, a in enumerate(blocks):
            for b in blocks[i + 1 :]:
                self.assertFalse(a & b)


class TestResolve(unittest.TestCase):
    def test_resolve_is_self_consistent(self):
        plan = iso.resolve(
            docker_dir="/repo/tests/docker",
            root_name="aee-docker-par",
            pid=1234,
            is_free=lambda p, s: True,
        )
        self.assertRegex(plan["COMPOSE_PROJECT_NAME"], iso.PROJECT_RE)
        self.assertRegex(plan["AEE_PROFILE"], iso.PROFILE_RE)
        self.assertTrue(plan["AEE_RUN_DIR"].endswith(plan["AEE_RUN_ID"]))
        self.assertEqual((int(plan["AEE_GAME_PORT"]) - iso.PORT_LOW) % iso.PORT_SLOT, 0)

    def test_two_resolves_do_not_collide(self):
        kw = dict(docker_dir="/repo/tests/docker", is_free=lambda p, s: True)
        a = iso.resolve(root_name="aee", pid=1, **kw)
        b = iso.resolve(root_name="aee", pid=2, **kw)
        self.assertNotEqual(a["AEE_RUN_ID"], b["AEE_RUN_ID"])
        self.assertNotEqual(a["COMPOSE_PROJECT_NAME"], b["COMPOSE_PROJECT_NAME"])
        self.assertNotEqual(a["AEE_RUN_DIR"], b["AEE_RUN_DIR"])

    def test_run_id_is_sanitised(self):
        plan = iso.resolve(
            docker_dir="/d",
            root_name="x",
            pid=1,
            run_id="Weird/Name:1",
            is_free=lambda p, s: True,
        )
        self.assertRegex(plan["AEE_RUN_ID"], r"^[a-z0-9][a-z0-9-]*$")

    def test_long_ids_sharing_a_prefix_do_not_collide(self):
        # A long run id must not be truncated to a shared prefix: two sibling
        # jobs differ only in their final index and must keep distinct ids.
        kw = dict(docker_dir="/d", root_name="x", pid=1, is_free=lambda p, s: True)
        a = iso.resolve(run_id="aee-docker-par-154884-default-0", **kw)
        b = iso.resolve(run_id="aee-docker-par-154884-default-1", **kw)
        self.assertNotEqual(a["AEE_RUN_ID"], b["AEE_RUN_ID"])
        self.assertNotEqual(a["COMPOSE_PROJECT_NAME"], b["COMPOSE_PROJECT_NAME"])


if __name__ == "__main__":
    unittest.main()
