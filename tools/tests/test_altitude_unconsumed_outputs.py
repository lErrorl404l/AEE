#!/usr/bin/env python3
"""The altitude outputs that are published and deliberately unread (issue #293).

The altitude module publishes three values to the mission state surface:

  aee_altitude_gLocStage      HAS a consumer: fnc_applyGLOCEffects turns the
                              stage into a RadialBlur.
  aee_altitude_gLocTolerance  NO consumer.
  aee_altitude_amsRisk        NO consumer.

gLocTolerance is the G tolerance fnc_calculateGLOC already applies INTERNALLY
to derive the stage.  The published copy is a diagnostic threshold that no
HUD, effect or model reads.  The consumer that is missing is a G-tolerance
readout, and the module has none.

amsRisk is the acute-mountain-sickness risk.  No AMS symptom or performance
model exists: the survival-pressure kernel aggregates five literature-anchored
hazards (dehydration, hypoxia, cold, heat, fatigue) and AMS is not one of them.
The consumer that is missing is an AMS symptom or performance model.

This suite pins that honest state.  It fails when a reader appears in addons/,
because a reader means the value is wired and the claim must be proven by the
code that reads it.  It fails when the ICD claims a crossing that has no
consumer.  It fails when the producer stops declaring the value deliberately
unread, so "published" is never mistaken for "wired".

Run: python3 -m unittest tools.tests.test_altitude_unconsumed_outputs
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"

# Published symbol -> the one file that writes it.
PRODUCERS = {
    "gLocTolerance": ADDONS / "altitude" / "XEH_postInit.sqf",
    "amsRisk": ADDONS
    / "altitude"
    / "functions"
    / "altitude"
    / "fnc_calculateAltitudeAcclimatization.sqf",
}

# The missing consumer for each value, stated once so the reason travels with
# the test and not only with the report.
MISSING_CONSUMER = {
    "gLocTolerance": (
        "a G-tolerance readout (HUD or telemetry consumer). The published "
        "value is the threshold fnc_calculateGLOC already applies internally; "
        "nothing outside the producer reads it."
    ),
    "amsRisk": (
        "an AMS symptom or performance model. The survival-pressure kernel "
        "aggregates dehydration, hypoxia, cold, heat and fatigue, and AMS is "
        "not one of the five; nothing else reads the published risk."
    ),
}

# A producer must say in the source that the published value is deliberately
# unread, beside the publish line.
UNREAD_MARKER = "deliberately unread"


def _sqf_sources():
    for path in ADDONS.rglob("*.sqf"):
        yield path, path.read_text(encoding="utf-8", errors="replace")


class TestTheValueIsPublished(unittest.TestCase):
    def test_each_symbol_is_written_by_its_producer(self):
        for symbol, producer in PRODUCERS.items():
            src = producer.read_text(encoding="utf-8")
            self.assertIn(
                f"QGVAR({symbol})",
                src,
                f"{producer} no longer publishes {symbol}",
            )


class TestNoCodeReadsThePublishedValue(unittest.TestCase):
    """A reader anywhere in addons/ means the value is wired, not unread."""

    def test_only_the_producer_names_the_symbol(self):
        for symbol, producer in PRODUCERS.items():
            readers = sorted(
                str(path.relative_to(ROOT))
                for path, src in _sqf_sources()
                if symbol in src and path != producer
            )
            self.assertEqual(
                readers,
                [],
                f"{symbol} now has a reader ({readers}); wire it the way "
                f"fnc_applyGLOCEffects consumes gLocStage and replace this pin "
                f"with a test that proves the read. The consumer that was "
                f"missing: {MISSING_CONSUMER[symbol]}",
            )


class TestTheProducerDeclaresTheValueUnread(unittest.TestCase):
    """The source states the value is deliberately unread, so the next reader
    cannot mistake 'published' for 'wired'."""

    def test_each_producer_declares_it(self):
        for symbol, producer in PRODUCERS.items():
            src = producer.read_text(encoding="utf-8")
            publish = src.index(f"QGVAR({symbol})")
            # The declaration sits with the publish, so it travels with the
            # line rather than somewhere else in the file.
            window = src[max(0, publish - 400) : publish + 200]
            self.assertIn(
                UNREAD_MARKER,
                window,
                f"{producer} publishes {symbol} without declaring it "
                f"deliberately unread. Missing consumer: "
                f"{MISSING_CONSUMER[symbol]}",
            )


class TestTheIcdClaimsNoConsumer(unittest.TestCase):
    """docs/icd/altitude-physiology.md records a crossing only for a variable
    the consumer addon reads.  These two do not cross; a row would be a claim
    of a consumer that does not exist."""

    def test_the_crossing_table_omits_them(self):
        icd = (ROOT / "docs" / "icd" / "altitude-physiology.md").read_text(
            encoding="utf-8"
        )
        for symbol in PRODUCERS:
            self.assertNotIn(
                f"aee_altitude_{symbol}",
                icd,
                f"the ICD now claims {symbol} crosses to the consumer addon; "
                f"wire the consumer or correct the ICD. Missing consumer: "
                f"{MISSING_CONSUMER[symbol]}",
            )


if __name__ == "__main__":
    unittest.main()
