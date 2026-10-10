// initSettings.inc.sqf - CBA Settings registration for aee_persistence
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// persistence stringtable.

// ── Frost ──────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(FrostAccumRate,"AEE Environmental","Hydrology",0,0.01,0.001,3);

AEE_SETTING_SLIDER(FrostDecayRate,"AEE Environmental","Hydrology",0,0.05,0.01,2);

[
    QGVAR(groundFrostEnabled),
    "CHECKBOX",
    [LLSTRING(GroundFrostEnabled_Name), LLSTRING(GroundFrostEnabled_Description)],
    ["AEE Environmental", "Hydrology"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Hydrology ──────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(FlashFloodThreshold,"AEE Environmental","Weather",20,100,50,0);

AEE_SETTING_SLIDER(WettingRate,"AEE Environmental","Hydrology",0,0.2,0.05,2);

AEE_SETTING_SLIDER(DewRate,"AEE Environmental","Hydrology",0,0.1,0.02,2);

// ── Avalanche slab model (#134) ────────────────────────────────────────────
// McClung & Schaerer shear-stress parameters.  Slab density and depth
// define tau = rho·g·h·sin(psi); the weak-layer strength is scaled from
// the snowpack quality.
AEE_SETTING_SLIDER(slabDensity,"AEE Environmental","Snow",100,400,300,0);

AEE_SETTING_SLIDER(slabDepth,"AEE Environmental","Snow",0.1,2,1.0,1);

// ── Seismic activity (#27) ─────────────────────────────────────────────────
// The seismic event is placed with the AEE Seismic Source EDEN module or
// raised by the scripting entry point.  These switches gate the secondary
// effects: the camera shake is local and cosmetic, the terrain deformation
// is server-side and destructive.
AEE_SETTING_CHECKBOX(seismicShakeEnabled,"AEE Environmental","Seismic",true);

AEE_SETTING_CHECKBOX(seismicTerrainDeformationEnabled,"AEE Environmental","Seismic",false);

// Diagnostics: the ground-state trace line logs at DEBUG after the first
// INFO line when this switch is on.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Persistence",false);
