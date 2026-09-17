#include "..\script_component.hpp"

/*
Wet/ice traction continuum (issue #133): hydroplaning (Horne & Dreher,
NASA TN D-2056), black ice (freezing-rain gate), and brake fade (Limpert).

Three independent effects that reduce effective friction:

  1. HYDROPLANING — dynamic, speed-dependent.  V_cr = 10.35*sqrt(P) mph
     (tyre pressure psi).  Below ~80% of V_cr the wet friction holds;
     between 80-100% it ramps linearly to the hydroplaning floor.
     Mass-independent (NASA): the tyre floats on the water film.

  2. BLACK ICE — a state, not a ramp.  Triggers when the road surface is
     below freezing AND liquid precipitation is falling AND there is
     standing water.  Ice friction is ~0.1 (dry is ~0.8).  Slipperiest
     near 0 C (a thin melt film acts as a lubricant), slightly better
     below -10 C.

  3. BRAKE FADE — cumulative thermal.  Each stop adds rotor heat
     dT = (0.5 m v^2 k)/(m_rotor c_p); the brake friction coefficient
     drops linearly from mu_cold (200 C) to mu_hot (300 C+).  Rotors
     cool exponentially toward ambient (tau 300-600 s).

The friction state publishes per-vehicle (the game exposes one contact
patch per vehicle; per-wheel would need ACE-style wheel access):

  mu_effective = min(mu_surface, mu_brake)   // braking
  mu_lateral   = mu_surface                   // cornering (no brake fade)

Input:  [_veh] - vehicle object (reads its own state)
        [_veh, _massKg, _speedMps, _braking] - update with motion (per-frame)
Output: mu_surface (0..1 combined hydroplaning/ice) when called with a veh;
        the internal _muBrake is applied by fnc_getEffectiveBrakingMu.

State: vehicle getVariable [QGVAR(brakeState)] = [tempC, lastTickSec].
*/

params [["_veh", objNull, [objNull]], ["_massKg", 0, [0]], ["_speedMps", 0, [0]], ["_braking", false, [false]]];

if (isNull _veh) exitWith { 1.0 };

// ─── Environmental inputs ────────────────────────────────────────────────
private _surfaceWet = missionNamespace getVariable [QEGVAR(core,surfaceWetness), 0];
if !(_surfaceWet isEqualType 0) then { _surfaceWet = 0; };
_surfaceWet = _surfaceWet max 0 min 1;

private _precipPhase = missionNamespace getVariable [QEGVAR(core,precipitationPhase), "none"];
private _roadTemp = missionNamespace getVariable [QEGVAR(core,avgGroundTemp), 15];
if !(_roadTemp isEqualType 0) then { _roadTemp = 15; };

// ─── 1. Hydroplaning (Horne & Dreher) ────────────────────────────────────
// V_cr (mph) = 10.35 * sqrt(P).  Tyre pressure: default 32 psi; if the
// config exposes tyre pressure use it.  Convert mph -> m/s (x0.44704).
private _tyrePsi = 32;
if (getNumber (configOf _veh >> "tyrePressurePsi") > 0) then {
    _tyrePsi = getNumber (configOf _veh >> "tyrePressurePsi");
};
private _vCrMps = 10.35 * sqrt (_tyrePsi max 20) * 0.44704;

// Water film depth scales with surface wetness.  Below the wet threshold
// friction is the dry/damp value; above it hydroplaning can engage.
private _dryMu = 0.8;
private _wetMu = 0.55;
private _muSurface = _dryMu - (_dryMu - _wetMu) * _surfaceWet;  // dry..wet by wetness

if (_speedMps > 0 && _surfaceWet > 0.3) then {
    private _frac = _speedMps / _vCrMps;
    if (_frac >= 0.8) then {
        // Linear ramp 80-100% V_cr down to the hydroplaning floor 0.05.
        private _t = ((_frac - 0.8) / 0.2) min 1 max 0;
        _muSurface = _muSurface - (_muSurface - 0.05) * _t;
    };
};

// ─── 2. Black ice ────────────────────────────────────────────────────────
// Road below 0 C + liquid precipitation + standing water.
if (_roadTemp < 0 && (_precipPhase == "rain" || _precipPhase == "freezing_rain") && _surfaceWet > 0.1) then {
    // Slipperiest near 0 C (thin melt film), improving below -10 C.
    private _coldFactor = 1.0 - (0.5 * ((_roadTemp + 10) / 10) max 0 min 1);
    _muSurface = (0.1 + 0.05 * _coldFactor) min _muSurface;
};

// ─── 3. Brake fade (Limpert) ─────────────────────────────────────────────
if (_massKg > 0) then {
    private _state = _veh getVariable [QGVAR(brakeState), [_roadTemp max 0, diag_tickTime]];
    _state params ["_brakeTemp", "_lastTick"];
    private _dt = (diag_tickTime - _lastTick) max 0;

    // Cool toward ambient exponentially (tau 450 s).
    private _tau = missionNamespace getVariable [QGVAR(brakeCoolingTau), 450];
    if !(_tau isEqualType 0) then { _tau = 450; };
    _brakeTemp = _roadTemp + (_brakeTemp - _roadTemp) * exp (-_dt / _tau);

    // Rotor heat per braking event: dT = (0.5 m v^2 k)/(m_rotor c_p).
    if (_braking && _speedMps > 1) then {
        private _rotorMass = missionNamespace getVariable [QGVAR(brakeRotorMassKg), 16];
        private _k = missionNamespace getVariable [QGVAR(brakeHeatFraction), 0.6];
        private _dT = (0.5 * _massKg * (_speedMps ^ 2) * _k) / (_rotorMass * 460);
        _brakeTemp = _brakeTemp + _dT;
    };

    // Friction coefficient: cold (200 C) -> hot (300 C+), linear between.
    private _muBrake = 0.4;
    if (_brakeTemp > 200) then {
        private _t = ((_brakeTemp - 200) / 100) min 1 max 0;
        _muBrake = 0.4 - (0.4 - 0.2) * _t;
    };

    _veh setVariable [QGVAR(brakeState), [_brakeTemp, diag_tickTime]];

    // Publish for diagnostics and consumers.
    missionNamespace setVariable [QGVAR(brakeTempC), _brakeTemp];
    missionNamespace setVariable [QGVAR(brakeMu), _muBrake];

    // Braking uses the min of surface and brake friction.
    if (_braking) then {
        _muSurface = _muSurface min _muBrake;
    };
};

missionNamespace setVariable [QGVAR(muSurface), _muSurface];

_muSurface
