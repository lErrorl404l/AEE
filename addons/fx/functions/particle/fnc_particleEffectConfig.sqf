#include "..\..\script_component.hpp"

/*
Particle effect schema (issue #149) — every effect is one row of DATA the
pipeline reads.

DECISION: the schema is SQF data, not an Arma config class.  A
CfgParticleEffects config cannot carry executable expressions safely: the
engine config parser does not evaluate SQF, so an expression such as
`intensity = "aee_core_dustSuppression * speed"` would be a string the
engine never runs, and the config is read-only at run time so it cannot be
driven by AEE state.  The emission physics therefore lives in SQF
(fnc_particleEmission) and this table carries only the static per-effect
data.  A new effect is a new row, not a new pipeline branch.

Row keys:
  priority  - allocation order.  A higher priority preempts a lower one at
              the budget ceiling (fnc_particleAllocate).  The ladder top
              (100) is reserved for fire, lightning and visible CBRN
              particles; the weather and dust effects sit below it.
  material  - the fnc_particleMaterial key (surface effects override it
              with the sampled surface material).
  baseRate  - particles per second at intensity 1.
  lifetime  - seconds.
  size      - [min, max] particle size in metres.
  circle    - emitter circle radius in metres.
  particles - budget estimate per live source (rate x lifetime).
  attach    - true: the source follows the emitter object.
  surface   - true: use the surface-lift coupling (fnc_kickupParams).
  slant     - 0..1 how much of the local wind enters moveVelocity.
  fall      - vertical moveVelocity in m/s (negative = settles).
  ttl       - seconds a source lives after its gate last passed.

Returns: HashMap effect name -> HashMap row.
*/

createHashMapFromArray [
    [
        "vehicleDust",
        createHashMapFromArray [
            ["priority", 40], ["material", "dust"], ["baseRate", 20],
            ["lifetime", 0.9], ["size", [0.2, 0.5]], ["circle", 3],
            ["particles", 18], ["attach", true], ["surface", true],
            ["slant", 0.5], ["fall", -0.2], ["ttl", 2]
        ]
    ],
    [
        "footfallDust",
        createHashMapFromArray [
            ["priority", 30], ["material", "dust"], ["baseRate", 8],
            ["lifetime", 1.4], ["size", [0.15, 0.4]], ["circle", 0.25],
            ["particles", 11], ["attach", true], ["surface", true],
            ["slant", 0.3], ["fall", 0.15], ["ttl", 1]
        ]
    ],
    [
        "atmosphericDust",
        createHashMapFromArray [
            ["priority", 10], ["material", "dust"], ["baseRate", 5],
            ["lifetime", 10], ["size", [30, 45]], ["circle", 50],
            ["particles", 50], ["attach", true], ["surface", false],
            ["slant", 0.05], ["fall", 0], ["ttl", 12]
        ]
    ],
    [
        "rotorWash",
        createHashMapFromArray [
            ["priority", 50], ["material", "dust"], ["baseRate", 15],
            ["lifetime", 2.4], ["size", [1.5, 3.5]], ["circle", 6],
            ["particles", 36], ["attach", true], ["surface", true],
            ["slant", 0.4], ["fall", 0.6], ["ttl", 2]
        ]
    ],
    [
        "snowfall",
        createHashMapFromArray [
            ["priority", 60], ["material", "snow"], ["baseRate", 25],
            ["lifetime", 3.5], ["size", [0.05, 0.12]], ["circle", 40],
            ["particles", 88], ["attach", true], ["surface", false],
            ["slant", 0.5], ["fall", -2.0], ["ttl", 3]
        ]
    ],
    [
        "blowingSnow",
        createHashMapFromArray [
            ["priority", 70], ["material", "snow"], ["baseRate", 45],
            ["lifetime", 2.0], ["size", [0.1, 0.3]], ["circle", 50],
            ["particles", 90], ["attach", true], ["surface", false],
            ["slant", 0.85], ["fall", -0.5], ["ttl", 3]
        ]
    ],
    [
        "hail",
        createHashMapFromArray [
            ["priority", 80], ["material", "hail"], ["baseRate", 30],
            ["lifetime", 2.5], ["size", [0.04, 0.09]], ["circle", 40],
            ["particles", 75], ["attach", true], ["surface", false],
            ["slant", 0.2], ["fall", -6.0], ["ttl", 3]
        ]
    ],
    [
        "haboob",
        createHashMapFromArray [
            ["priority", 55], ["material", "sand"], ["baseRate", 18],
            ["lifetime", 6], ["size", [15, 25]], ["circle", 60],
            ["particles", 108], ["attach", true], ["surface", false],
            ["slant", 0.9], ["fall", -0.3], ["ttl", 8]
        ]
    ],
    [
        "hurricane",
        createHashMapFromArray [
            ["priority", 90], ["material", "rain"], ["baseRate", 70],
            ["lifetime", 3], ["size", [0.3, 3.0]], ["circle", 60],
            ["particles", 210], ["attach", true], ["surface", false],
            ["slant", 0.95], ["fall", -8.0], ["ttl", 4]
        ]
    ],
    [
        "hurricaneSpray",
        createHashMapFromArray [
            ["priority", 88], ["material", "spray"], ["baseRate", 25],
            ["lifetime", 2.5], ["size", [0.5, 2.0]], ["circle", 50],
            ["particles", 63], ["attach", true], ["surface", false],
            ["slant", 0.9], ["fall", -1.0], ["ttl", 4]
        ]
    ],
    [
        "hurricaneDebris",
        createHashMapFromArray [
            ["priority", 86], ["material", "debris"], ["baseRate", 10],
            ["lifetime", 3.5], ["size", [0.1, 0.4]], ["circle", 50],
            ["particles", 35], ["attach", true], ["surface", false],
            ["slant", 0.8], ["fall", -3.0], ["ttl", 4]
        ]
    ]
]
