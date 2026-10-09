// initSettings.inc.sqf - CBA Settings registration for aee_cartography
//
// Included from XEH_preInit.sqf after the ADR-032 settings migration.  Each
// setting registers with CBA_fnc_addSetting; the MGRS map and GPS knobs moved
// here from aee_optics and took the aee_cartography_* names.  No default
// changed.

// MGRS grid readout in the HUD (task 7).  On: the grid line carries the
// aee worldToMgrs reference.  Off: the legacy numeric grid from
// FUNC(hudFormatGrid).  Default on; the formatter falls back to the legacy
// grid on its own when MGRS is unavailable.
AEE_SETTING_CHECKBOX(mgrsEnabled,"AEE HUD","Displays",true);

// MGRS precision: the total digit count.  A LIST, because only these counts
// are valid MGRS references (an arbitrary even count is not one).  Four
// digits is 1 km, six is 100 m, eight is 10 m and ten is 1 m.  Default 10.
[
    QGVAR(mgrsPrecision),
    "LIST",
    [LLSTRING(mgrsPrecision_Name), LLSTRING(mgrsPrecision_Description)],
    ["AEE HUD", "Displays"],
    [[4, 6, 8, 10], ["4 (1 km)", "6 (100 m)", "8 (10 m)", "10 (1 m)"], 3],
    true,
    {}
] call CBA_fnc_addSetting;

// Scale the MGRS digit count with the world map size.  On: a small world gets
// a six-figure reference (100 m) and a large world an eight-figure one
// (10 m).  Off: the mgrsPrecision list applies.  Default on.
AEE_SETTING_CHECKBOX(mgrsPrecisionAuto,"AEE HUD","Displays",true);

// Draw the aee MGRS grid over the engine map.  The engine grid stays
// numeric: the CfgWorlds Grid class formats numbers only and no script
// command writes it, so the aee overlay draws its own MGRS lines and their
// labels.  The interval follows the zoom.  Default on.
AEE_SETTING_CHECKBOX(mgrsMapGrid,"AEE HUD","Displays",true);

// Show the aee MGRS reference and the terrain elevation at the map cursor.
// The vanilla cursor tooltip is engine-side and cannot be replaced, so the
// aee readout is drawn adjacent to it.  Default on.
AEE_SETTING_CHECKBOX(mgrsCursorReadout,"AEE HUD","Displays",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_cartography_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Cartography",false);
