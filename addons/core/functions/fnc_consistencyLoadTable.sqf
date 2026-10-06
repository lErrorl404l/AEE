#include "..\script_component.hpp"

/*
Cross-module invariant table (compiled-in constant).

SQF cannot read a JSON file at run time, so the table is compiled in here as
a constant.  It is the SQF twin of data/consistency/invariants.json and the
two MUST stay in lockstep; tools/tests/test_consistency_evaluator.py parses
both and fails when a row, a field, or a value drifts.

Row layout (fixed index order, mirrored by fnc_evaluateConsistency):

    0 id          STRING  invariant id, for example "INV-4"
    1 name        STRING  invariant name, for example "body_temperature"
    2 producers   ARRAY   list of [module, variable] pairs
    3 predicate   STRING  agree_within | aperture_matches_lux |
                          monotone_with_wind | daynight_consistent
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
            ["optics", "aee_optics_eyeAdaptedLux"],
            ["optics", "aee_optics_eyeAperture"]
        ],
        "aperture_matches_lux",
        0.5,
        "warn",
        "derived",
        "The adapted luminance tracks the scene illuminance and the eye aperture lies on the supplied lux-to-aperture line. Tolerance is a relative fraction."
    ],
    [
        "INV-2",
        "thermal_ground_chain",
        [
            ["core", "aee_core_currentTemperature"],
            ["thermal", "aee_thermal_groundNodeStack"],
            ["core", "aee_core_groundSurfaceTemp"],
            ["core", "aee_core_avgGroundTemp"]
        ],
        "agree_within",
        15.0,
        "warn",
        "derived",
        "Air, ground-surface and average-ground temperatures agree within 15 C. aee_thermal_groundNodeStack is a HashMap; the harness supplies its surface layer."
    ],
    [
        "INV-3",
        "wind_scent_turbulence",
        [
            ["core", "aee_core_currentWindStr"],
            ["environmental", "aee_environmental_scentDispersionIntensity"],
            ["core", "aee_core_currentTurbulence"]
        ],
        "monotone_with_wind",
        0.05,
        "warn",
        "derived",
        "A stronger wind raises or holds the scent dispersion and the turbulence. The harness supplies the prior sample as the reference."
    ],
    [
        "INV-4",
        "body_temperature",
        [
            ["thermal", "aee_thermal_humanCoreTempC"],
            ["core", "aee_core_coreBodyTemp"]
        ],
        "agree_within",
        2.0,
        "warn",
        "derived",
        "The thermal two-node human core temperature and the core physiology heat balance agree within 2 C. The physiology coefficients are UNSOURCED."
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
