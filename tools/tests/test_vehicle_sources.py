#!/usr/bin/env python3
"""Source holding tests for the vehicle corpus (wave 1, task 1).

The holding tool writes the fetched bytes and marks a source held only when
the on-disk digest equals the recorded digest. A missing file, a digest
mismatch and a failed fetch are errors. A failed or mismatched download
never leaves a held file. A source with no pinned digest is never held, so
the tool never trusts the first fetched digest.

The tests use a temporary directory and an injected fetch. They do not use
the network.

Run: python3 -m unittest tools.tests.test_vehicle_sources -v
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.validation import fetch_vehicle_sources as f

REPO = Path(__file__).parents[2]

GOOD = b"held document bytes"
GOOD_SHA = hashlib.sha256(GOOD).hexdigest()
BAD_SHA = hashlib.sha256(b"other bytes").hexdigest()


def _entry(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source_id": "tm_test",
        "tier": 2,
        "type": "manual",
        "title": "Test manual, not a real document",
        "identifier": "TM-TEST",
        "retrieved": "2026-09-24",
        "url": "https://example.invalid/tm_test.pdf",
        "sha256": GOOD_SHA,
        "primary_held": False,
    }
    base.update(over)
    return base


class HeldFilename(unittest.TestCase):
    def test_pdf_url_keeps_extension(self) -> None:
        self.assertEqual(f.held_filename(_entry()), "tm_test.pdf")

    def test_url_with_query_keeps_extension(self) -> None:
        entry = _entry(url="https://example.invalid/a/b.pdf?token=1")
        self.assertEqual(f.held_filename(entry), "tm_test.pdf")

    def test_no_url_uses_bin(self) -> None:
        self.assertEqual(f.held_filename(_entry(url="")), "tm_test.bin")


class AtomicWrite(unittest.TestCase):
    def test_write_leaves_no_partial_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            target = dest / "tm_test.pdf"
            f.atomic_write_bytes(target, GOOD)
            self.assertEqual(target.read_bytes(), GOOD)
            leftovers = [p.name for p in dest.iterdir() if p != target]
            self.assertEqual(leftovers, [])

    def test_write_replaces_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "tm_test.pdf"
            target.write_bytes(b"stale")
            f.atomic_write_bytes(target, GOOD)
            self.assertEqual(target.read_bytes(), GOOD)


class HoldSource(unittest.TestCase):
    def test_valid_fetch_writes_and_marks_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            entry, err = f.hold_source(_entry(), dest, fetch=lambda url: GOOD)
            self.assertIsNone(err)
            self.assertTrue(entry["primary_held"])
            self.assertEqual(entry["sha256"], GOOD_SHA)
            self.assertEqual((dest / "tm_test.pdf").read_bytes(), GOOD)

    def test_digest_mismatch_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            entry, err = f.hold_source(_entry(), dest, fetch=lambda url: b"bad")
            self.assertIsNotNone(err)
            self.assertIn("mismatch", str(err))
            self.assertFalse(entry["primary_held"])
            self.assertEqual(entry["sha256"], GOOD_SHA)
            self.assertFalse((dest / "tm_test.pdf").exists())

    def test_failed_fetch_writes_nothing(self) -> None:
        def boom(url: str) -> bytes:
            raise RuntimeError("connection refused")

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            entry, err = f.hold_source(_entry(), dest, fetch=boom)
            self.assertIsNotNone(err)
            self.assertIn("connection refused", str(err))
            self.assertFalse(entry["primary_held"])
            self.assertFalse((dest / "tm_test.pdf").exists())

    def test_empty_response_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            entry, err = f.hold_source(_entry(), dest, fetch=lambda url: b"")
            self.assertIsNotNone(err)
            self.assertFalse(entry["primary_held"])
            self.assertFalse((dest / "tm_test.pdf").exists())

    def test_missing_url_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entry, err = f.hold_source(_entry(url=""), Path(tmp), fetch=lambda u: GOOD)
            self.assertIsNotNone(err)
            self.assertFalse(entry["primary_held"])

    def test_missing_expected_digest_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            entry, err = f.hold_source(_entry(sha256=""), dest, fetch=lambda url: GOOD)
            self.assertIsNotNone(err)
            self.assertIn("pinned sha256", str(err))
            self.assertFalse(entry["primary_held"])
            self.assertEqual(entry["sha256"], "")
            self.assertFalse((dest / "tm_test.pdf").exists())

    def test_absent_sha256_key_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            source = _entry()
            del source["sha256"]
            entry, err = f.hold_source(source, dest, fetch=lambda url: GOOD)
            self.assertIsNotNone(err)
            self.assertIn("pinned sha256", str(err))
            self.assertFalse(entry["primary_held"])
            self.assertFalse((dest / "tm_test.pdf").exists())


class VerifySources(unittest.TestCase):
    def test_valid_held_file_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "tm_test.pdf").write_bytes(GOOD)
            errors = f.verify_sources([_entry(primary_held=True)], dest)
            self.assertEqual(errors, [])

    def test_missing_held_file_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = f.verify_sources([_entry(primary_held=True)], Path(tmp))
            self.assertEqual(len(errors), 1)
            self.assertIn("tm_test", errors[0])
            self.assertIn("missing", errors[0])

    def test_digest_mismatch_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "tm_test.pdf").write_bytes(b"truncated")
            errors = f.verify_sources([_entry(primary_held=True)], dest)
            self.assertEqual(len(errors), 1)
            self.assertIn("tm_test", errors[0])
            self.assertIn("mismatch", errors[0])

    def test_blank_digest_on_held_file_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "tm_test.pdf").write_bytes(GOOD)
            errors = f.verify_sources([_entry(primary_held=True, sha256="")], dest)
            self.assertEqual(len(errors), 1)
            self.assertIn("tm_test", errors[0])

    def test_missing_file_of_non_held_source_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = f.verify_sources([_entry(primary_held=False)], Path(tmp))
            self.assertEqual(errors, [])

    def test_expected_digest_in_bad_sha_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "tm_test.pdf").write_bytes(GOOD)
            errors = f.verify_sources([_entry(primary_held=True, sha256=BAD_SHA)], dest)
            self.assertEqual(len(errors), 1)
            self.assertIn("mismatch", errors[0])


class RegistryRoundTrip(unittest.TestCase):
    def test_load_and_save_keeps_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            f.save_registry(path, [_entry()])
            loaded = f.load_registry(path)
            self.assertEqual(loaded, [_entry()])


def _write_registry(dest: Path, entries: list[dict[str, object]]) -> Path:
    path = dest / "sources.json"
    f.save_registry(path, entries)
    return path


class CliVerify(unittest.TestCase):
    def test_verify_passes_on_a_held_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "sources").mkdir()
            (dest / "sources" / "tm_test.pdf").write_bytes(GOOD)
            _write_registry(dest, [_entry(primary_held=True)])
            self.assertEqual(f.main(["--verify", "--data-dir", str(dest)]), 0)

    def test_verify_fails_and_names_the_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "sources").mkdir()
            _write_registry(dest, [_entry(primary_held=True)])
            self.assertEqual(f.main(["--verify", "--data-dir", str(dest)]), 1)

    def test_named_fetch_holds_and_updates_the_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _write_registry(dest, [_entry()])
            with mock.patch.object(f, "fetch_url", return_value=GOOD):
                rc = f.main(["tm_test", "--data-dir", str(dest)])
            self.assertEqual(rc, 0)
            saved = f.load_registry(dest / "sources.json")
            self.assertTrue(saved[0]["primary_held"])
            self.assertEqual((dest / "sources" / "tm_test.pdf").read_bytes(), GOOD)

    def test_unknown_source_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _write_registry(dest, [_entry()])
            self.assertEqual(f.main(["ghost", "--data-dir", str(dest)]), 1)


if __name__ == "__main__":
    unittest.main()
