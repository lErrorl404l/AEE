#include "..\..\script_component.hpp"
/*
Rifle optic properties (issue #215).

Classifies the weapon's optic slot by its classname family keywords and
returns the researched sight physics from sensor-device-library.md:

  [magnification, objectiveMm, fovDeg, weightKg, exitPupilMm, active]

Groups (sortable by country -> company -> type):
  USA  | Trijicon ACOG (TA31/TA11, 4x32 prism) + M150 RCO -> Aimpoint
    M68/CompM4/T-2 (red dot) -> EOTech EXPS3 (holographic) -> ELCAN
    SpecterDR 1-4x / M145 MGO -> Leupold Mark 4 (10x) + Mark 5 ->
    Nightforce ATACR (5-25x) -> Schmidt & Bender PM II
  UK   | SUSAT L9A1 (4x) -> ELCAN SpecterDR
  Europe | Hensoldt ZF (4x), Schmidt & Bender
  Russia | PSO-1 (4x24), 1P78 Kashtan (4x), 1P87 (red dot), 1P69
    Hyperon (3-10x), POSP (4-8x), NVG sights (1PN51/93/120, ~2 kg)
  China | Type 89, QMK152

Optic physics (the FOV/magnification the view model consumes):
  exit pupil = objective / magnification (PSO-1 24/4 = 6 mm)
  FOV falls as magnification rises (~24/mag deg for the 4x class)
  eye relief 70-90 mm fixed scopes, unlimited red dots
  active (NVG/thermal) adds ~1.5-2 kg

Arguments:
  0: unit (OBJECT, default player)
  1: weapon (OBJECT, default the primary)

Returns [magnification, objectiveMm, fovDeg, weightKg, exitPupilMm, active]
*/
params [["_unit", player, [objNull]], ["_weapon", objNull, [objNull]]];
if (isNull _unit) exitWith { [4, 32, 7, 0.42, 8, 0] };

private _optic = "";
if (!isNull _weapon) then { _optic = primaryWeaponItems _weapon param [2, ""]; };
if (_optic == "") exitWith { [4, 32, 7, 0.42, 8, 0] };

private _o = toLower _optic;
private _fallback = switch (true) do {
    // ── Active NVG/thermal weapon sights (the fusion/night optics) ──
    case (_o find "1pn" >= 0 ||
          _o find "nvs" >= 0 ||
          _o find "nvg" >= 0 ||
          _o find "thermal" >= 0 ||
          _o find "pas-13" >= 0):          { [3.5, 50, 5, 2.0, 14, 1] };
    // ── Variable sniper optics (5-25x, the precision class) ──
    case (_o find "atacr" >= 0 ||
          _o find "5-25" >= 0 ||
          _o find "5x25" >= 0 ||
          _o find "pmii" >= 0 ||
          _o find "pm2" >= 0 ||
          _o find "mark5" >= 0 ||
          _o find "mark_5" >= 0):          { [10, 56, 3, 1.05, 5.6, 0] };
    // ── Fixed 10x sniper (Leupold Mark 4 M3) ──
    case (_o find "mark4" >= 0 ||
          _o find "mark_4" >= 0 ||
          _o find "10x" >= 0):             { [10, 40, 3.5, 0.68, 4, 0] };
    // ── Variable 1-4x / 1-6x (SpecterDR, LDS, the combat variable) ──
    case (_o find "specterdr" >= 0 ||
          _o find "specter_dr" >= 0 ||
          _o find "1-4" >= 0 ||
          _o find "1-6" >= 0 ||
          _o find "1x4" >= 0 ||
          _o find "1x6" >= 0 ||
          _o find "l_d_s" >= 0 ||
          _o find "lds" >= 0):             { [4, 30, 8, 0.60, 7.5, 0] };
    // ── Russian PSO-1 (4x24, SVD) + POSP (4-8x) + 1P78 ──
    case (_o find "pso" >= 0 ||
          _o find "posp" >= 0 ||
          _o find "1p78" >= 0 ||
          _o find "kashtan" >= 0 ||
          _o find "1p69" >= 0 ||
          _o find "hyperon" >= 0):         { [4, 24, 6, 0.60, 6, 0] };
    // ── Fixed 4x prism (ACOG TA31/TA11, M150 RCO, SUSAT, Hensoldt) ──
    case (_o find "acog" >= 0 ||
          _o find "ta31" >= 0 ||
          _o find "ta11" >= 0 ||
          _o find "rco" >= 0 ||
          _o find "susat" >= 0 ||
          _o find "zf" >= 0 ||
          _o find "4x" >= 0):              { [4, 32, 7, 0.42, 8, 0] };
    // ── Red dots (Aimpoint M68/CompM4/T-2, the reflex class) ──
    case (_o find "compm" >= 0 ||
          _o find "comp_m" >= 0 ||
          _o find "t-2" >= 0 ||
          _o find "t2" >= 0 ||
          _o find "m68" >= 0 ||
          _o find "cc0" >= 0 ||
          _o find "1p87" >= 0 ||
          _o find "reddot" >= 0 ||
          _o find "reflex" >= 0):          { [1, 23, 0, 0.27, 0, 0] };
    // ── Holographic (EOTech EXPS3) ──
    case (_o find "eotech" >= 0 ||
          _o find "exps" >= 0 ||
          _o find "553" >= 0):             { [1, 0, 0, 0.32, 0, 0] };
    // ── M145 MGO / C79 (3.4x fixed) ──
    case (_o find "m145" >= 0 ||
          _o find "c79" >= 0 ||
          _o find "mgo" >= 0):             { [3.4, 28, 8.5, 0.68, 8.2, 0] };
    default                                  { [4, 32, 7, 0.42, 8, 0] };
};

// ─── Corpus route: data/device/, family "optic" (issue #215) ─────────────
// The device corpus is the authority.  fnc_getDeviceData returns the optic
// value row [magnification, objective_mm, fov_deg, weight_kg,
// exit_pupil_mm, active], the same contract this function returns, so a
// corpus figure overrides the static fallback above per field.  A field the
// corpus leaves absent arrives as 0 or "" and the fallback stands, and a
// figure is never copied from a sibling device.
private _row = [_optic, "optic"] call EFUNC(nightvision,getDeviceData);
if (_row isEqualTo []) exitWith { _fallback };

private _mag = _row select 0;
if ((_mag isEqualType 0) && (_mag > 0)) then { _fallback set [0, _mag]; };
private _objective = _row select 1;
if ((_objective isEqualType 0) && (_objective > 0)) then { _fallback set [1, _objective]; };
private _fov = _row select 2;
if ((_fov isEqualType 0) && (_fov > 0)) then { _fallback set [2, _fov]; };
private _weight = _row select 3;
if ((_weight isEqualType 0) && (_weight > 0)) then { _fallback set [3, _weight]; };
private _exitPupil = _row select 4;
if ((_exitPupil isEqualType 0) && (_exitPupil > 0)) then { _fallback set [4, _exitPupil]; };
// The corpus holds the word, the return contract holds 1 (active) or 0.
private _active = _row select 5;
if (_active == "active") then { _fallback set [5, 1]; };
if (_active == "passive") then { _fallback set [5, 0]; };

_fallback
