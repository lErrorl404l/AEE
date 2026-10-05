// initSettings.inc.sqf - CBA Settings registration for aee_mobility
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// mobility stringtable.

// ── Flight Turbulence ──────────────────────────────────────────────────────
// Applies atmospheric turbulence, gusts and wind shear to aircraft.  The
// advanced and rotor-lib models take a PhysX force; the simple model takes a
// local velocity delta.  Every application is gated to the owning machine.
[
    QGVAR(flightTurbulence),
    "CHECKBOX",
    [LLSTRING(flightTurbulence_Name), LLSTRING(flightTurbulence_Description)],
    ["AEE Mobility", "Turbulence"],
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

AEE_SETTING_SLIDER(turbulenceScale,"AEE Mobility","Turbulence",0,3,1,1);

AEE_SETTING_SLIDER(turbulenceRadius,"AEE Mobility","Turbulence",500,5000,2000,0);

// ── Airframe density and icing load ────────────────────────────────────────
// Applies the published lift ratio and the FAR 25 App C icing state to a
// locally-owned airframe as bounded lift/drag forces and an ice-mass delta.
AEE_SETTING_CHECKBOX(flightAeroPenalty,"AEE Mobility","Flight",true);

AEE_SETTING_SLIDER(airframeRadius,"AEE Mobility","Flight",500,5000,2000,0);

// ── Traction ────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(mudAccretionRate,"AEE Mobility","Hydrology",0,0.02,0.002,3);

AEE_SETTING_SLIDER(mudDecayRate,"AEE Mobility","Hydrology",0.9,1,0.99,2);

AEE_SETTING_SLIDER(tractionScale,"AEE Mobility","Traction",0.5,1.5,1.0,1);

// ── Vehicle Performance ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(minEnginePower,"AEE Mobility","Traction",0.1,0.8,0.3,1);

// ── Environment ─────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(routeRecoveryRate,"AEE Mobility","Route",1,1.01,1.001,3);

AEE_SETTING_SLIDER(routeDamageRate,"AEE Mobility","Route",0,0.0001,0.00002,5);

AEE_SETTING_SLIDER(riverResponseRate,"AEE Mobility","Hydrology",0.01,0.5,0.1,2);

AEE_SETTING_SLIDER(rainAccumDecay,"AEE Mobility","Hydrology",0.9,1,0.97,2);

// ── Brake fade (issue #133) ────────────────────────────────────────────────
AEE_SETTING_SLIDER(brakeCoolingTau,"AEE Mobility","Traction",100,900,450,0);

AEE_SETTING_SLIDER(brakeRotorMassKg,"AEE Mobility","Traction",4,40,16,1);

AEE_SETTING_SLIDER(brakeHeatFraction,"AEE Mobility","Traction",0.1,1,0.6,2);

// ── Hydrology (issue #24) ─────────────────────────────────────────────────
// These drive the rainfall-runoff chain in fnc_calculateRiverWaterLevel.
// The defaults are the operational values the models were calibrated on,
// so the settings change the model rather than decorating it.
AEE_SETTING_SLIDER(riverSectionWidth_m,"AEE Mobility","Hydrology",0.5,50,4,1);

AEE_SETTING_SLIDER(tidalReach_m,"AEE Mobility","Hydrology",500,20000,5000,0);

AEE_SETTING_SLIDER(baseflowRate_perDay,"AEE Mobility","Hydrology",0.01,1,0.2,2);

AEE_SETTING_SLIDER(catchmentArea_m2,"AEE Mobility","Hydrology",10000,5000000,250000,0);

AEE_SETTING_SLIDER(bedSlope,"AEE Mobility","Hydrology",0.0001,0.05,0.001,5);

AEE_SETTING_SLIDER(manningN,"AEE Mobility","Hydrology",0.01,0.1,0.035,3);

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

// ── Off-road terrain drag ──────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(terrainDragEnabled,"AEE Mobility","Terrain",true);

AEE_SETTING_SLIDER(terrainDragScale,"AEE Mobility","Terrain",0.05,1.0,0.3,2);

AEE_SETTING_SLIDER(terrainRadius,"AEE Mobility","Terrain",10,200,50,0);

// ── Runtime vehicle coupling (W2) ─────────────────────────────────────────
// Applies the surface accretion load with setMass and the wet/ice grip loss
// with a force. Both run on the machine that owns the vehicle.
AEE_SETTING_CHECKBOX(vehicleCouplingEnabled,"AEE Mobility","Vehicle",true);

// ── Vehicle Mass Estimate ──────────────────────────────────────────────────
// The estimate is modelled, not documented. A sourced catalogue weight always
// takes precedence. The switch stays off until the model passes calibration
// and a human approves mass_model.json.
[
    QGVAR(estimateVehicleMassEnabled),
    "CHECKBOX",
    [LLSTRING(estimateVehicleMassEnabled_Name), LLSTRING(estimateVehicleMassEnabled_Description)],
    ["AEE Mobility", "Vehicle"],
    false,  // default: disabled until calibration and approval pass
    true,   // global, so the estimate is the same on every machine
    {}
] call CBA_fnc_addSetting;

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_mobility_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Mobility",false);
