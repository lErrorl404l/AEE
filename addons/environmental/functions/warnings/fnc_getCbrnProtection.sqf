#include "..\..\script_component.hpp"
/*
CBRN protective equipment (issue #119, the CBRN gear table).

Classifies the unit's CBRN protection from the equipment slots (the
goggles slot holds the respirator; the uniform holds the suit) and
returns a protection factor 0..1 - the fraction of airborne agent the
kit blocks.  The values are the researched figures from
equipment-library.md (CBRN section):

  JSLIST 2.63 kg, 24 h protection, 45 days / 6 launderings
  M50 JSGPM 0.86 kg (CBRN Cap 1, >36 h agent resistance)
  M40/M42, FM12/FM50/C50, S10, PMK-3, GP-5/7 (0.49-0.96 kg)
  MOPP-4 ~8 kg system; L-1/OKZK (RU) impermeable suits

Protection model (the contamination gate in fnc_integrateACM scales the
global persistence by 1 - protection):
  Respirator alone   ~0.75  (the mask blocks inhalation; skin is exposed)
  Suit alone         ~0.60  (skin covered; the respirator still needed)
  Full kit (mask+suit) ~0.95 (both barriers, per the 24 h JSLIST profile)

Arguments:
  0: unit (OBJECT, default player)

Returns the CBRN protection factor 0..1.
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0.0 };

// The respirator: the goggles slot classifies CBRN masks (M50/FM12/
// PMK-3/GP-7 etc) as ~0.86 kg CBRN Cap 1 items.
private _goggle = goggles _unit;
private _hasMask = false;
if (_goggle != "") then {
    private _g = toLower _goggle;
    _hasMask = (_g find "m50" >= 0 || _g find "m40" >= 0 || _g find "m42" >= 0
        || _g find "fm12" >= 0 || _g find "fm50" >= 0 || _g find "c50" >= 0
        || _g find "s10" >= 0 || _g find "gp-5" >= 0 || _g find "gp-7" >= 0
        || _g find "pmk" >= 0 || _g find "respirator" >= 0);
};

// The suit: the uniform classname carries the CBRN suit signal
// (JSLIST/MOPP/overwhite/L-1/OKZK/6B44).
private _uniform = uniform _unit;
private _hasSuit = false;
if (_uniform != "") then {
    private _u = toLower _uniform;
    _hasSuit = (_u find "jslist" >= 0 || _u find "mopp" >= 0
        || _u find "l-1" >= 0 || _u find "okzk" >= 0 || _u find "6b44" >= 0
        || _u find "cbrn" >= 0 || _u find "nbc" >= 0 || _u find "nrbc" >= 0
        || _u find "chemical" >= 0);
};

if (_hasMask && _hasSuit) then { 0.95 } else {
    if (_hasMask) then { 0.75 } else {
        if (_hasSuit) then { 0.60 } else { 0.0 }
    }
}