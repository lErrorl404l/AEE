#include "..\script_component.hpp"

/*
Acoustic source-level table (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps a sound event kind to a source level in dB.  The caller may scale the
result for a specific source, for example with the ammo audible-fire factor.
An unknown kind is silent, so an unmodelled event never spooks an animal.

PROVENANCE.

  gunshot 160 dB peak SPL.  SOURCED.  The measured peak level of an
    unsuppressed centre-fire weapon is 160 to 170 dB at the shooter or the
    instructor position.  NIOSH Health Hazard Evaluation report
    2013-0124-3208, Results: an M4 rifle measured 152 dB and a 9 mm pistol
    146 dB peak at the instructor position, rising to about 160 dB for the
    5 yard exercises.  NIOSH Science Bulletin, "Hit the Mark" (2017):
    "sound levels often reaching 160-170 dB peak sound pressure levels".
    The table takes 160 dB, the low end of the published range.

  suppressed 138 dB peak SPL.  SOURCED, derived from the gunshot value.  A
    firearm suppressor lowers the peak by 17 to 24 dB at the ear (Murphy,
    Flamme and others 2017, "The reduction of gunshot noise and auditory
    risk through the use of firearm suppressors and low-velocity
    ammunition", International Journal of Audiology, DOI
    10.1080/14992027.2017.1407459, abstract).  The table takes the mid
    reduction, 22 dB: 160 - 22 = 138 dB.

  explosion, grenade, aircraft, vehicle, footstep.  UNSOURCED.  No primary
    source for a 1 m source level is held in this repository, so the values
    are modelling choices that order the kinds by loudness: an explosion is
    louder than a gunshot, a vehicle engine is quieter than a grenade, a
    footstep is the quietest.  The register in
    docs/wiki/research/wildlife-ecology-constants.md holds them.

GAME MAPPING.  Only the gunshot and suppressed rows carry a measured level.
The level the engine consumes is a game quantity: the caller maps it onto a
vanilla sound class or a playSound3D volume, and that mapping is a game
mapping, not a measured value.  The two layers stay apart on purpose.

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
if (_key == "suppressed") then { _db = 138; };
if (_key == "explosion") then { _db = 180; };
if (_key == "grenade") then { _db = 170; };
if (_key == "aircraft") then { _db = 130; };
if (_key == "vehicle") then { _db = 100; };
if (_key == "footstep") then { _db = 50; };

_db
