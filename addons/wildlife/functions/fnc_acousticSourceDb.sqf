#include "..\script_component.hpp"

/*
Acoustic source-level table (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps a sound event kind to a source level in dB.  The caller may scale the
result for a specific source, for example with the ammo audible-fire factor.
An unknown kind is silent, so an unmodelled event never spooks an animal.

Every level is an UNSOURCED modelling choice, stated so the register can hold
them.  They order the kinds by loudness: an explosion is louder than a
gunshot, a vehicle engine is quieter than a grenade, a footstep is the
quietest.

Kinds: gunshot, suppressed, explosion, grenade, aircraft, vehicle, footstep.

Arguments:
  0: String - the event kind

Returns:
  Number - the source level in dB, 0 for an unknown kind
*/

params [
    ["_kind", "", [""]]
];

private _key = toLower _kind;
private _db = 0;

if (_key == "gunshot") then { _db = 160; };
if (_key == "suppressed") then { _db = 120; };
if (_key == "explosion") then { _db = 180; };
if (_key == "grenade") then { _db = 170; };
if (_key == "aircraft") then { _db = 130; };
if (_key == "vehicle") then { _db = 100; };
if (_key == "footstep") then { _db = 50; };

_db
