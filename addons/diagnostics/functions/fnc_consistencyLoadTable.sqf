#include "..\script_component.hpp"

/*
Cross-module invariant table (compiled-in constant).

SQF cannot read a JSON file at run time, so the table is compiled in here as
a constant.  It is the SQF twin of data/consistency/invariants.json and the
two MUST stay in lockstep; tools/tests/test_consistency_evaluator.py parses
both and fails when a row, a field, or a value drifts.

Row layout (fixed index order, mirrored by fnc_evaluateConsistency):

    0 id          STRING  invariant id, for example "INV-1"
    1 name        STRING  invariant name, for example "illuminance_chain"
    2 producers   ARRAY   list of [module, variable] pairs
    3 predicate   STRING  agree_within | night_scene_agreement |
                          daynight_consistent
    4 tolerance   NUMBER  predicate band, units stated in the note
    5 severity    STRING  warn | error
    6 grade       STRING  provenance of the values compared
    7 note        STRING  one line of context

The evaluator never reads the world: it takes this table and a value map and
returns per-row verdicts.  The runtime monitor (task 15) builds the value map
and the prior-sample references this table's predicates consume.

Returns: Array - the invariant table.
*/

private _table = [
    [
        "INV-1",
        "illuminance_chain",
        [
            ["core", "aee_core_illuminanceLux"],
            ["optics", "aee_optics_eyeSceneLux"],
            ["core", "aee_core_lightIsNight"]
        ],
        "night_scene_agreement",
        0.5,
        "warn",
        "derived",
        "Night scope: the row runs only when aee_core_lightIsNight is true (sun at or below the horizon). At night both sides are the physical-sky model, so the eye scene illuminance (aee_optics_eyeSceneLux) tracks the core illuminance (aee_core_illuminanceLux) within the tolerance, a relative fraction. The eye fix 98d1f17 gates the engine local term by sun elevation, so the two agree at night. In daylight the two draw on different light sources and the row is out of scope."
    ],
    [
        "INV-2",
        "thermal_ground_chain",
        [
            ["core", "aee_core_currentTemperature"],
            ["core", "aee_core_groundSurfaceTemp"],
            ["core", "aee_core_avgGroundTemp"]
        ],
        "agree_within",
        15.0,
        "warn",
        "derived",
        "Air, ground-surface and average-ground temperatures agree within 15 C. aee_thermal_groundNodeStack is a per-cell HashMap store documented in Annex C, not a scalar, so it is excluded from the numeric comparison."
    ],
    [
        "INV-5",
        "solar_sky_eye",
        [
            ["core", "aee_core_currentSunElevation"],
            ["thermal", "aee_thermal_skyBandTempC"],
            ["core", "aee_core_lightIsNight"],
            ["environmental", "aee_environmental_nightClassification"]
        ],
        "daynight_consistent",
        1.0,
        "warn",
        "derived",
        "The night flag and the DEF Stan 61-027 night classification agree with the sun elevation. Tolerance is the twilight margin in degrees."
    ]
];

_table
