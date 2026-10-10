#include "..\..\script_component.hpp"

/*
Cold-weather human performance model.

Computes wind chill temperature, manual dexterity loss, frostbite
time-to-injury, and the TB MED 508 cold-weather danger category from the
shared environmental state.  Pure maths, no player state.

Wind chill (Osczevski & Bluestein 2001, NWS/Environment Canada metric
formula):
    WCT = 13.12 + 0.6215*T - 11.37*V^0.16 + 0.3965*T*V^0.16
T is air temperature (degC), V is wind speed (km/h).  The formula is
valid for T <= 10 degC and V > 4.8 km/h.  Outside that band the air
temperature is used unchanged.  WCT is clamped to the air temperature
because wind cannot make the air feel warmer.

Manual dexterity (Heus, Daanen & Havenith 1995, Appl Ergon 26(1):5-13,
PMID 15676995; Daanen 2009): dexterity falls with wind chill.  Anchors
used here, linearly interpolated:
    WCT >= 0 degC   -> 90 %   (mild reduction)
    WCT -10 degC    -> 70 %
    WCT -20 degC    -> 50 %
    WCT -30 degC    -> 30 %
    WCT <= -40 degC -> 10 %   (nearly incapacitated)
The slope is 2 % per degC; the floor is 10 %.

Frostbite time-to-injury (Tikuisis & Osczevski 2002, J. Appl. Meteor.
41:1226; anchored to the NOAA / US Army Research Institute frostbite
chart):
    t = 90 * exp(0.11 * WCT)  minutes, floor 1 minute
    WCT -10 -> ~30 min, -20 -> ~10 min, -40 -> ~1 min

Danger categories (TB MED 508, Prevention and Management of Cold Weather
Injuries): little / increased / great / immediate.

Input:  []
Output: wind chill temperature (degC)
Sets:   QEGVAR(core,windChillTemp)        degC
        QEGVAR(core,dexterityPercent)     0..100
        QEGVAR(core,frostbiteMinutes)     minutes
        QEGVAR(core,coldDangerCategory)   "little"|"increased"|"great"|"immediate"
*/

params [];

private _enabled = missionNamespace getVariable [QGVAR(coldWeatherEnabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if !(_enabled) exitWith {};

// ─── Read state ───────────────────────────────────────────────────────────
private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tempC isEqualType 0) then { _tempC = 15; };
private _windMs = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_windMs isEqualType 0) then { _windMs = 0; };
private _windKmh = _windMs * 3.6;

// ─── Wind chill (Osczevski-Bluestein) ─────────────────────────────────────
private _wct = _tempC;
if (_tempC <= 10 && _windKmh > 4.8) then {
    private _vExp = _windKmh ^ 0.16;
    private _chill = 13.12 + 0.6215 * _tempC - 11.37 * _vExp + 0.3965 * _tempC * _vExp;
    _wct = _chill min _tempC;
};

// ─── Manual dexterity (Heus 1995, Daanen 2009) ────────────────────────────
private _dexterity = 90;
if (_wct < 0) then {
    _dexterity = (90 + 2 * _wct) max 10;
};

// ─── Frostbite time-to-injury (Tikuisis & Osczevski 2002) ─────────────────
private _frostbite = (90 * exp (0.11 * _wct)) max 1;

// ─── Danger category (TB MED 508) ─────────────────────────────────────────
private _category = "little";
if (_wct < -28) then { _category = "increased"; };
if (_wct < -39) then { _category = "great"; };
if (_wct < -54) then { _category = "immediate"; };

missionNamespace setVariable [QEGVAR(core,windChillTemp), _wct];
missionNamespace setVariable [QEGVAR(core,dexterityPercent), _dexterity];
missionNamespace setVariable [QEGVAR(core,frostbiteMinutes), _frostbite];
missionNamespace setVariable [QEGVAR(core,coldDangerCategory), _category];

_wct
