// initSettings.inc.sqf - CBA Settings registration for aee_optics
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// optics stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Optics / Visibility ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(seeingFXIntensity,"AEE Optics","Intensity",0,0.1,0.02,2);




AEE_SETTING_SLIDER(mirageIntensity,"AEE Optics","Intensity",0,2,1.0,0);

AEE_SETTING_SLIDER(mirageDensity,"AEE Optics","Intensity",0.01,0.5,0.08,2);

AEE_SETTING_SLIDER(solarGlareIntensity,"AEE Optics","Intensity",0,2,1.0,0);

AEE_SETTING_SLIDER(glareBlurMax,"AEE Optics","Intensity",0,1,0.2,1);

AEE_SETTING_SLIDER(heatShimmerIntensity,"AEE Optics","Intensity",0,0.2,0.04,2);

AEE_SETTING_SLIDER(dewBlurMax,"AEE Optics","Intensity",0,1,0.4,1);

AEE_SETTING_SLIDER(snowBlindnessIntensity,"AEE Optics","Intensity",0,2,1.0,0);

AEE_SETTING_SLIDER(rainBlurScale,"AEE Optics","Intensity",0,1,0.3,1);

AEE_SETTING_SLIDER(mirageOnsetTemp,"AEE Optics","Thresholds",20,50,35,0);

AEE_SETTING_SLIDER(mirageMinSunElev,"AEE Optics","Thresholds",0,30,15,0);

AEE_SETTING_SLIDER(smokePersistenceScale,"AEE Optics","Atmosphere",0.2,3,1.0,1);

AEE_SETTING_SLIDER(snowVisibilityPenalty,"AEE Optics","Atmosphere",0.3,1,0.7,1);

AEE_SETTING_SLIDER(vehicleShimmerBase,"AEE Optics","Thresholds",0,1,0.3,1);

AEE_SETTING_SLIDER(snowBlindnessBase,"AEE Optics","Thresholds",0,0.5,0.1,1);

AEE_SETTING_SLIDER(dewAccumRate,"AEE Optics","Particles",0,0.2,0.05,2);

AEE_SETTING_SLIDER(dewDecayRate,"AEE Optics","Particles",0,0.1,0.02,2);

AEE_SETTING_SLIDER(rainAccumRate,"AEE Optics","Particles",0,0.05,0.01,2);

AEE_SETTING_SLIDER(rainDecayRate,"AEE Optics","Particles",0,0.1,0.02,2);

AEE_SETTING_SLIDER(chromaCap,"AEE Optics","Intensity",0,0.2,0.06,2);

// ── ECOTI environment HUD ──────────────────────────────────────────────────
// A night-vision operator aid: heading, grid, altitude, time and the aee
// environment state over the NVG view.  Default OFF (a HUD is an operator
// choice); the HUD workers gate on this setting each tick, so it toggles
// live.
AEE_SETTING_CHECKBOX(hudEnabled,"AEE HUD","Displays",false);

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

// ── Signal-dependent tracker (task 13) ────────────────────────────────────
// Replaces the arcade exact friendly position with a modelled one: the three
// aee GNSS kernels (error ellipse, fix state, datalink) applied to the exact
// group positions.  Default OFF; the driver and the draw gate on it each tick.
AEE_SETTING_CHECKBOX(trackerEnabled,"AEE HUD","Tracker",false);

// Suppress the engine friendly map indicators where the engine allows it.
// The suppression is a LOCAL disableMapIndicators call (Arma 3 1.82+) that
// acts only when the difficulty exposes "extended map content".  The tracker
// draws its own fuzzy markers regardless.
AEE_SETTING_CHECKBOX(trackerSuppressIcons,"AEE HUD","Tracker",false);

// Seconds between tracker model updates for the local group.  A longer
// interval is cheaper and ages the tracks more.
AEE_SETTING_SLIDER(trackerInterval,"AEE HUD","Tracker",0.2,5,1.0,1);

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

// Suppress the engine indicators where the engine allows it and hide the
// engine mission markers locally while the map is open.
AEE_SETTING_CHECKBOX(symbologySuppress,"AEE HUD","Symbology",true);

// Use the AEE font for the symbology labels when the assets are present.
AEE_SETTING_CHECKBOX(symbologyFont,"AEE HUD","Symbology",true);

// ── Thermal polarity (issue #196) ─────────────────────────────────────────
// Moved to aee_thermal/initSettings.inc.sqf with the rest of the thermal
// pipeline (white-hot default, black-hot user-selectable per FM 3-22.9).

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_optics_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Optics",false);
