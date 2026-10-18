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
    10.1080/14992027.2017.1407459, abstract).  The band is 17 to 24 dB, so its
    mid is 20.5 dB.  The table takes 22 dB, one value inside the band and near
    its upper end: 160 - 22 = 138 dB.  It is a chosen operating point, not the
    band's mid, and the constants register states the same.

  grenade, explosion.  SOURCED.  The Kinney & Graham (1985) peak
    overpressure (fnc_blastPeakDb) at 100 m, in the acoustic far field,
    carried back to 1 m by spherical spreading (+40 dB), so the level the
    propagation kernels spread is the far-field-equivalent source level.
    grenade: the M67, 6.5 oz (184 g) of Composition B (TM 3-23.30), TNT
    equivalence 1.11 in peak pressure (UFC 3-340-02): 0.204 kg TNT.
    explosion: the 155 mm M107 shell, 6.6 kg TNT (TM 43-0001-28).
  vehicle 99.5 dB.  SOURCED as the regulatory ceiling: EU Regulation
    540/2014 Annex III limits a heavy goods vehicle (N3, > 250 kW) to
    82 dB(A) at 7.5 m in the ISO 362 pass-by, +17.5 dB to 1 m.
  aircraft, footstep.  UNSOURCED.  No primary source for a 1 m level is
    held; they are ordered by loudness.  The register in
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
if (_key == "explosion") then { _db = ([6.6, 100] call EFUNC(lib,blastPeakDb)) + 40; };
if (_key == "grenade") then { _db = ([0.184 * 1.11, 100] call EFUNC(lib,blastPeakDb)) + 40; };
if (_key == "aircraft") then { _db = 130; };
if (_key == "vehicle") then { _db = 82 + (20 * (log 7.5)); };
if (_key == "footstep") then { _db = 50; };

_db
