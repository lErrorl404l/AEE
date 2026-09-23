#include "..\script_component.hpp"

/*
NRMM soil strength: the go/no-go test for a vehicle on soft ground (#117).

The ground has a Rating Cone Index (RCI); the vehicle needs a Vehicle Cone
Index (VCI).  The vehicle passes if RCI >= VCI.

  RCI = CI * RI
    CI is the cone index of the soil, RI the remolding index (the ratio of
    remolded to undisturbed strength, capped at 1).  RI applies to
    fine-grained soils and remoldable sands, not to clean sand or gravel.
    Source: ERDC/GSL SR-13-2 Eq. 1; FM 5-430-00-1 Ch. 7.

  Wheeled Mobility Index (MI), all terms in lbf and inches:
    MI = [(CPF * WF) / (TEF * GF) + WLF - CF] * EF * TF
      CPF = w / (0.5 * n * d * b)     contact pressure factor
      TEF = (10 + b) / 100            tyre factor
      WLF = w / 2000                  weight-load factor
      CF  = hc / 10                   clearance factor
      WF  = CWF1 * (w / 1000) + CWF2  weight factor, piecewise in the load
      GF  = 1 + 0.05 * chains         grouser factor
      EF  = 1 + 0.05 (PWR < 10 hp/t)  engine factor
      TF  = 1 + 0.05 (manual gearbox) transmission factor
    Source: Priddy 1999, ERDC TR GL-99-8 (DTIC ADA368656), p. 42.

  Vehicle Cone Index, wheeled:
    MI < 115:  VCI1  = (11.48 + 0.2 MI - 39.2 / (MI + 2.14)) * DCF
               VCI50 = 28.23 + 0.43 MI - 92.67 / (MI + 3.67)
    MI > 115:  VCI1  = 4.1 * MI^0.446 * DCF
               VCI50 = 9 * MI^0.446 * DCF
    DCF = (0.15 / delta)^0.25, the deflection correction factor.  delta is
    the hard-surface deflection ratio, nominally 0.15, which makes the
    factor 1 and leaves the coefficient forms exact.
    Source: Priddy 1999 p. 43; WEVJ 2025 16(1):47 Eq. 6.

NOT IMPLEMENTED, because no primary source was reached (recorded on the
issue rather than guessed):
  - VCI50 = 25.2 + 0.454 MI    (the issue's form; NOT FOUND)
  - VCI = 1.4 MI for non-AWD    (NOT FOUND)
  - the Def Stan 23-6 stress bands (paywalled)
  - the tracked MI and VCI.  The tracked form needs the track contact
    length and the Nr*As product; the engine exposes neither and no
    reached source gives them, so a tracked vehicle reports no MI and no
    VCI rather than a fabricated one.  Its mobility falls back to the
    wheeled traction model.

Arguments:
  0: vehicle (OBJECT)
  1: rci (NUMBER) - the Rating Cone Index at the vehicle's position

Return Value: ARRAY [vci1, vci50, mi, passes50, passes1]
Example: [cursorObject, 72] call aee_mobility_fnc_calculateSoilStrength
Public: No
*/

params [
    ["_vehicle", objNull, [objNull]],
    ["_rci", 0, [0]]
];

if (isNull _vehicle) exitWith { [0, 0, 0, false, false] };

// ─── Vehicle geometry ────────────────────────────────────────────────────
// The engine exposes no tyre width, tyre diameter, wheel count or track
// contact length, so a class table carries the published values of the
// vehicle each class represents.  Most specific first, because isKindOf
// matches the whole inheritance chain.
if (_vehicle isKindOf "Tank" || {_vehicle isKindOf "Tracked_APC"}) exitWith {
    missionNamespace setVariable [QGVAR(currentMobilityIndex), 0];
    [0, 0, 0, false, false]
};

private _spec = [8000, 12, 40, 10, 4];   // default: a light 4x4
{
    if (_vehicle isKindOf (_x select 0)) exitWith {
        _spec = _x select 1;
    };
} forEach [
    ["MRAP",        [30000, 14, 44, 14, 4]],
    ["Wheeled_APC", [26000, 14, 42, 16, 8]],
    ["Car",         [ 7000, 10, 28,  8, 4]],
    ["Truck",       [20000, 14, 40, 12, 6]]
];

_spec params ["_w", "_b", "_d", "_hc", "_n"];

// ─── Mobility Index ──────────────────────────────────────────────────────
private _cpf = _w / (0.5 * _n * _d * _b);
private _tef = (10 + _b) / 100;
private _wlf = _w / 2000;
private _cf  = _hc / 10;

// Weight factor, piecewise in the load (lbf).  Source: Priddy 1999 p. 42.
private _wfC1 = 0; private _wfC2 = 0;
if (_w < 2000) then { _wfC1 = 0.553; _wfC2 = 0; }
else { if (_w < 13500) then { _wfC1 = 0.033; _wfC2 = 1.050; }
else { if (_w < 20000) then { _wfC1 = 0.142; _wfC2 = -0.420; }
else { _wfC1 = 0.278; _wfC2 = -3.115; }; }; };
private _wf = _wfC1 * (_w / 1000) + _wfC2;

// GF, EF and TF are 1 for the vanilla fleet: no grousers, every vehicle
// over 10 hp/ton, and the engine reporting an automatic for these classes.
private _gf = 1;
private _ef = 1;
private _tf = 1;

private _mi = ((_cpf * _wf) / (_tef * _gf) + _wlf - _cf) * _ef * _tf;

// ─── Vehicle Cone Index ──────────────────────────────────────────────────
// A zero or negative MI makes the coefficient forms blow up (a division by
// a near-zero MI).  The floor keeps the arithmetic real; a vehicle cannot
// have an MI below about 4 on any published geometry.
_mi = _mi max 4;

private _dcf = 1;   // delta = 0.15 nominal, so DCF is 1
private _vci1 = 0;
private _vci50 = 0;

if (_mi < 115) then {
    _vci1  = (11.48 + 0.2 * _mi - 39.2 / (_mi + 2.14)) * _dcf;
    _vci50 = 28.23 + 0.43 * _mi - 92.67 / (_mi + 3.67);
} else {
    _vci1  = 4.1 * (_mi ^ 0.446) * _dcf;
    _vci50 = 9 * (_mi ^ 0.446) * _dcf;
};

_vci1 = _vci1 max 1;
_vci50 = _vci50 max _vci1;

// ─── Go / no-go ──────────────────────────────────────────────────────────
private _passes50 = _rci >= _vci50;
private _passes1  = _rci >= _vci1;

missionNamespace setVariable [QGVAR(currentVCI1), _vci1];
missionNamespace setVariable [QGVAR(currentVCI50), _vci50];
missionNamespace setVariable [QGVAR(currentMobilityIndex), _mi];

[_vci1, _vci50, _mi, _passes50, _passes1]
