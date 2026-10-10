// initSettings.inc.sqf - CBA Settings registration for aee_symbology
//
// Included from XEH_preInit.sqf after the ADR-032 settings migration.  Each
// setting registers with CBA_fnc_addSetting; the NATO/OPFOR symbology knobs
// moved here from aee_optics and took the aee_symbology_* names.  No default
// changed.

// ── NATO/OPFOR map symbology (ADR-023) ────────────────────────────────────
// The map and world symbols follow NATO APP-6(C).  The layer draws the frame
// grammar, the affiliation colours and a curated set of inner glyphs.  The
// master switch ships OFF; each toggle gates one surface.
AEE_SETTING_CHECKBOX(symbologyEnabled,"AEE HUD","Symbology",false);

// The affiliation palette.  A LIST, because only these three choices are
// valid.  NATO fixes WEST as the friendly side, OPFOR fixes EAST, and Auto
// follows the local side.  The index 2 is "Auto", the default.
[
    QGVAR(symbologyPalette),
    "LIST",
    [LLSTRING(symbologyPalette_Name), LLSTRING(symbologyPalette_Description)],
    ["AEE HUD", "Symbology"],
    [["NATO", "OPFOR", "Auto"], ["NATO", "OPFOR", "Auto"], 2],
    true,
    {}
] call CBA_fnc_addSetting;

// Draw the symbols for the in-range units and the player.
AEE_SETTING_CHECKBOX(symbologyUnits,"AEE HUD","Symbology",true);

// Draw the symbols for the engine map markers.
AEE_SETTING_CHECKBOX(symbologyMarkers,"AEE HUD","Symbology",true);

// Gate the unit pass on a carried tracker.  When on, the unit symbols draw
// only while the local player carries a GPS or a tracker device, as a
// blue-force tracker does.  Default off, so nothing regresses.
AEE_SETTING_CHECKBOX(bftRequired,"AEE HUD","Symbology",false);

// Suppress the engine indicators where the engine allows it and hide the
// engine mission markers locally while the map is open.
AEE_SETTING_CHECKBOX(symbologySuppress,"AEE HUD","Symbology",true);

// Use the AEE font for the symbology labels when the assets are present.
AEE_SETTING_CHECKBOX(symbologyFont,"AEE HUD","Symbology",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_symbology_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Symbology",false);
