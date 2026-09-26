#include "..\script_component.hpp"
/*
Vehicle mass model parameter table.

Function: aee_mobility_fnc_getVehicleMassModel.

This file is GENERATED. The generator tools/validation/gen_vehicle_mass_model.py
writes it from the model artefact data/vehicle/mass_model.json. Do not edit it
by hand. Edit the model and regenerate it.

The table holds modelled parameters only. It reads no engine state, it
defines no extra function, and it holds no real-world vehicle value. The
estimate is unavailable while the approved flag is false.

Return Value: ARRAY, five blocks in this order:
  0 approved       BOOL. True only after calibration and approval pass.
  1 densityTable   ARRAY of [className, lowKgM3, highKgM3], one row per
                   classifier class.
  2 massClasses    ARRAY of [key, matchKind, vehicleType, densityClass,
                   fillLow, fillHigh], in match order, default last.
  3 geometryBands  ARRAY [minExtentM, maxExtentM, maxWidthRatio].
  4 powerBlock     ARRAY [enabled, unit, hardFactor, bands].

Public: No
*/

[
    true,
    [
        [
            "metal",
            7100.0,
            7850.0
        ],
        [
            "rock",
            2500.0,
            2800.0
        ],
        [
            "wood",
            350.0,
            1100.0
        ],
        [
            "concrete",
            2200.0,
            2600.0
        ],
        [
            "glass",
            2200.0,
            2500.0
        ],
        [
            "water",
            998.0,
            1000.0
        ],
        [
            "vegetation",
            250.0,
            350.0
        ],
        [
            "ground",
            860.0,
            1450.0
        ]
    ],
    [
        [
            "Motorcycle",
            "token",
            "wheeled",
            "metal",
            0.0,
            0.0
        ],
        [
            "Car",
            "token",
            "wheeled",
            "metal",
            0.0046,
            0.0068
        ],
        [
            "Truck",
            "token",
            "wheeled",
            "metal",
            0.0036,
            0.0078
        ],
        [
            "MRAP",
            "token",
            "wheeled",
            "metal",
            0.0081,
            0.0172
        ],
        [
            "Wheeled_APC",
            "token",
            "wheeled",
            "metal",
            0.0047,
            0.0106
        ],
        [
            "Wheeled_APC_F",
            "token",
            "wheeled",
            "metal",
            0.0,
            0.0
        ],
        [
            "Tank",
            "token",
            "tracked",
            "metal",
            0.0149,
            0.0287
        ],
        [
            "Tracked_APC",
            "token",
            "tracked",
            "metal",
            0.0041,
            0.009
        ],
        [
            "wheeled",
            "vehicle_type",
            "wheeled",
            "metal",
            0.0036,
            0.0172
        ],
        [
            "tracked",
            "vehicle_type",
            "tracked",
            "metal",
            0.0041,
            0.0287
        ],
        [
            "default",
            "default",
            "",
            "metal",
            0.0,
            0.0
        ]
    ],
    [
        0.5,
        20.0,
        6.0
    ],
    [
        false,
        "enginePower/tonne",
        2.0,
        []
    ]
]
