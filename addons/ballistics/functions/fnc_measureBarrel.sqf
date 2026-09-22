#include "..\script_component.hpp"
/*
Barrel measurement (issue #170, the ADR-001 measure-from-model principle).

MEASURES the real barrel length of a weapon from its model, using the
engine's memory points (the muzzle and chamber points defined in the
weapon model).  The measured length feeds the cartridge velocity-length
curve (fnc_deriveCartridge): a mod weapon gets its real MV from its own
model - no table entry, works first load.

Measurement: the weapon model's muzzle and chamber memory points.  The
engine exposes the memory-point position in the MODEL frame (local,
metres) via selectionPosition on the weapon model's geometryLOD; the
barrel length is the muzzle-to-chamber distance.

The chamber point may be named "chamber" or the attachment point; the
fallback measures from the weapon's bounding box front to the ejection
point when the named points are absent.

A model without usable points returns 0. The caller then lets
fnc_deriveCartridge use the cartridge reference barrel, which carries
the cartridge's standard muzzle velocity. A guessed barrel would be
worse than the cartridge's own standard.

Arguments:
  0: weapon (STRING, the CfgWeapons classname, default "")
  1: weaponHolder (OBJECT, the weapon object, default objNull - the
     measurement needs the actual model)

Returns the measured barrel length in metres. Returns 0 when the model
has no usable memory points.
*/
params [["_weapon", "", [""]], ["_holder", objNull, [objNull]]];
if (_weapon == "") exitWith { 0 };

// Measure from the model: the muzzle and chamber memory points.  The
// muzzle point is the standard "muzzle" on weapon models; the chamber
// is the "chamber" or the "ugl_muzzle"/"pistol" attachment reference.
private _measured = 0;
if (!isNull _holder) then {
    private _muzzlePos = _holder selectionPosition ["muzzle", "Memory"];
    if (count _muzzlePos == 3) then {
        private _chamberPos = _holder selectionPosition ["chamber", "Memory"];
        if (count _chamberPos != 3) then {
            _chamberPos = _holder selectionPosition ["ugl_muzzle", "Memory"];
        };
        if (count _chamberPos == 3) then {
            private _dx = (_muzzlePos select 0) - (_chamberPos select 0);
            private _dy = (_muzzlePos select 1) - (_chamberPos select 1);
            private _dz = (_muzzlePos select 2) - (_chamberPos select 2);
            _measured = sqrt ((_dx ^ 2) + (_dy ^ 2) + (_dz ^ 2));
        };
    };
};

// Sanity: a measured barrel must be between 4" and 40" (0.1-1.0 m).  A
// value outside the physical band means the memory points are not a
// muzzle/chamber pair (some mods use "muzzle" for a rail mount).  Return
// 0 so the cartridge reference barrel is used instead of a guess.
if (_measured < 0.1 || _measured > 1.0) exitWith { 0 };

_measured
