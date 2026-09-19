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
