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
