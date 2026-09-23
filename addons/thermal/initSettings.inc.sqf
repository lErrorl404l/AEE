// ── Thermal polarity (issue #196) ─────────────────────────────────────────
// White-hot (0) is the system default - the AN/PAS-13 initialises white
// hot.  Black-hot (1) is a user-selectable alternative; FM 3-22.9
// Appendix H states polarity choice is user preference, not doctrine.
// Lives here (aee_thermal) with the rest of the thermal pipeline - the
// optics module owns NVG/normal vision only.
[
    QGVAR(thermalPolarity),
    "LIST",
    [LLSTRING(thermalPolarity_Name), LLSTRING(thermalPolarity_Description)],
    ["AEE Thermal", "Display"],
    [[0, 1], ["White hot", "Black hot"], 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Fusion (issue #204, Track B ENVG-B) ───────────────────────────────────
// Off: fusion only on TI-capable headsets (visionMode includes "TI").
// On:  fusion renders over ANY NVG, thermal source or not (the A3TI
// approach - its fusion modes are offered whenever an optic has thermal
// and the current vanilla mode is NVG).
[
    QGVAR(fusionAlwaysOn),
    "CHECKBOX",
    [LLSTRING(fusionAlwaysOn_Name), LLSTRING(fusionAlwaysOn_Description)],
    ["AEE Thermal", "Fusion"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Fixed-pattern noise (issue #204, FPN) ────────────────────────────────
// Real LWIR sensors show a static spatial mottle (fixed-pattern noise)
// over the thermal image, independent of the temporal FilmGrain.  On:
// painted thermal objects get the ti_fpn.rvmat material (perlinNoise
// Stage2 multiplying the painted heat colour).  The material swap is
// client-local and restored on thermal EXIT.
[
    QGVAR(thermalFPN),
    "CHECKBOX",
    [LLSTRING(thermalFPN_Name), LLSTRING(thermalFPN_Description)],
    ["AEE Thermal", "Display"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Thermal diagnostics (issue #203, standalone decoupling) ─────────────
// Thermal's own debug flag - previously borrowed nightvision's nvgDebug,
// a cross-module coupling that blocked thermal as a standalone addon.
[
    QGVAR(thermalDebug),
    "CHECKBOX",
    [LLSTRING(thermalDebug_Name), LLSTRING(thermalDebug_Description)],
    ["AEE Thermal", "Diagnostics"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Solver cadence ────────────────────────────────────────────────────────
// The object-temperature scan is the most expensive call in the environment
// tick. Surface temperatures run on time constants of 600 s and up, so the
// scan does not need the tick rate. 0 restores a scan every tick.
[
    QGVAR(objectScanInterval),
    "SLIDER",
    [LLSTRING(objectScanInterval_Name), LLSTRING(objectScanInterval_Description)],
    ["AEE Thermal", "Solver"],
    [0, 120, 30, 0],
    true,
    {}
] call CBA_fnc_addSetting;
