// initSettings.inc.sqf - CBA Settings registration for aee_flight
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the flight
// stringtable.

// ── Flight Turbulence ──────────────────────────────────────────────────────
// Applies atmospheric turbulence, gusts and wind shear to aircraft.  The
// advanced and rotor-lib models take a PhysX force; the simple model takes a
// local velocity delta.  Every application is gated to the owning machine.
[
    QGVAR(flightTurbulence),
    "CHECKBOX",
    [LLSTRING(flightTurbulence_Name), LLSTRING(flightTurbulence_Description)],
    ["AEE Flight", "Turbulence"],
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

AEE_SETTING_SLIDER(turbulenceScale,"AEE Flight","Turbulence",0,3,1,1);

AEE_SETTING_SLIDER(turbulenceRadius,"AEE Flight","Turbulence",500,5000,2000,0);

// ── Airframe density and icing load ────────────────────────────────────────
// Applies the published lift ratio and the FAR 25 App C icing state to a
// locally-owned airframe as bounded lift/drag forces and an ice-mass delta.
AEE_SETTING_CHECKBOX(flightAeroPenalty,"AEE Flight","Flight",true);

AEE_SETTING_SLIDER(airframeRadius,"AEE Flight","Flight",500,5000,2000,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name built
// from the component: aee_flight_logDebug.  Declaring it here, in its own
// addon, is what makes that name correct.  QGVAR(logDebug) resolves to
// aee_flight_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Flight",false);
