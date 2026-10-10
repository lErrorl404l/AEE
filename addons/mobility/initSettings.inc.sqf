// initSettings.inc.sqf - CBA Settings registration for aee_mobility
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// mobility stringtable.

// ── Traction ────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(mudAccretionRate,"AEE Mobility","Hydrology",0,0.02,0.002,3);

AEE_SETTING_SLIDER(mudDecayRate,"AEE Mobility","Hydrology",0.9,1,0.99,2);

AEE_SETTING_SLIDER(tractionScale,"AEE Mobility","Traction",0.5,1.5,1.0,1);

// ── Environment ─────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(routeRecoveryRate,"AEE Mobility","Route",1,1.01,1.001,3);

AEE_SETTING_SLIDER(routeDamageRate,"AEE Mobility","Route",0,0.0001,0.00002,5);

AEE_SETTING_SLIDER(rainAccumDecay,"AEE Mobility","Hydrology",0.9,1,0.97,2);

// ── Brake fade (issue #133) ────────────────────────────────────────────────
AEE_SETTING_SLIDER(brakeCoolingTau,"AEE Mobility","Traction",100,900,450,0);

AEE_SETTING_SLIDER(brakeRotorMassKg,"AEE Mobility","Traction",4,40,16,1);

AEE_SETTING_SLIDER(brakeHeatFraction,"AEE Mobility","Traction",0.1,1,0.6,2);

// ── Vehicle Rollover ───────────────────────────────────────────────────────
// The threshold physics is the Static Stability Factor (NHTSA) with the
// Gillespie slope correction. Each control is a real input to that model,
// so none of them is inert.
[
    QGVAR(rolloverEnabled),
    "CHECKBOX",
    [LLSTRING(rolloverEnabled_Name), LLSTRING(rolloverEnabled_Description)],
    ["AEE Mobility", "Rollover"],
    true,   // default: enabled
    true,   // global — the threshold must match on every machine
    {}
] call CBA_fnc_addSetting;

AEE_SETTING_SLIDER(rolloverDynamicFactor,"AEE Mobility","Rollover",0.7,0.9,0.8,2);

AEE_SETTING_SLIDER(rolloverHoldFrames,"AEE Mobility","Rollover",1,60,10,0);

AEE_SETTING_SLIDER(rolloverTorqueScale,"AEE Mobility","Rollover",0.05,1.0,0.25,2);

AEE_SETTING_SLIDER(rolloverRadius,"AEE Mobility","Rollover",10,200,50,0);

// ── Frost heave (issue #20) ────────────────────────────────────────────────
// The magnitude is the two-term value of fnc_calculateFrostHeave (in-situ
// expansion plus ice-lens segregation).  Each control is a real input to that
// model, so none of them is inert.
AEE_SETTING_CHECKBOX(frostHeaveEnabled,"AEE Mobility","Frost Heave",true);

AEE_SETTING_SLIDER(frostHeaveMultiplier,"AEE Mobility","Frost Heave",0,2,1.0,2);

AEE_SETTING_SLIDER(frostHeaveMaxM,"AEE Mobility","Frost Heave",0,0.5,0.3,2);

// ── Off-road terrain drag ──────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(terrainDragEnabled,"AEE Mobility","Terrain",true);

AEE_SETTING_SLIDER(terrainDragScale,"AEE Mobility","Terrain",0.05,1.0,0.3,2);

AEE_SETTING_SLIDER(terrainRadius,"AEE Mobility","Terrain",10,200,50,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_mobility_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Mobility",false);
