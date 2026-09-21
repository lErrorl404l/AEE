// ── Armour overhaul settings (issue #126) ─────────────────────────────────
[
    QGVAR(armourEnabled),
    "CHECKBOX",
    [LLSTRING(armourEnabled_Name), LLSTRING(armourEnabled_Description)],
    ["AEE Armour", "Armour"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(penetrationGate),
    "CHECKBOX",
    [LLSTRING(penetrationGate_Name), LLSTRING(penetrationGate_Description)],
    ["AEE Armour", "Penetration"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(penetrationDebug),
    "CHECKBOX",
    [LLSTRING(penetrationDebug_Name), LLSTRING(penetrationDebug_Description)],
    ["AEE Armour", "Penetration"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;
