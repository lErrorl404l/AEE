#include "..\script_component.hpp"

/*
NRMM soil strength is QUARANTINED until sourced records exist (issue #117).

The go/no-go test needs a Vehicle Cone Index (VCI) for the vehicle. The VCI
needs per-vehicle records and a verified prediction source. Neither is
available yet, so this function publishes no numeric result.

Verified and usable later:
  - RCI = CI * RI, the Rating Cone Index.
    Source: ERDC/GSL SR-13-2 Eq. 1; FM 5-430-00-1 Ch. 7.
  - The wheeled Mobility Index and the VCI1 low branch.
    Source: Priddy 1999, ERDC TR GL-99-8 (DTIC ADA368656), p. 42-43.

Not verified, so not implemented:
  - The VCI50 prediction equations. They are absent from Priddy 1999 and
    from ERDC/GSL SR-13-2.
  - The tracked Mobility Index derivatives, which need the track contact
    length and the Nr*As product that the engine does not expose.
  - The per-vehicle weight, tyre width, tyre diameter, ground clearance,
    net power and drivetrain. Engine config values are tuning values with
    no verified real-world unit.

Status published on every call:
  aee_mobility_currentSoilStrengthKnown = false
  aee_mobility_currentSoilStrengthReason = one of:
    "null"              the vehicle argument is a null object
    "tracked"           the vehicle is a Tank or a Tracked_APC
    "unverifiedInputs"  every other vehicle, and every malformed argument

The three numeric variables aee_mobility_currentVCI1,
aee_mobility_currentVCI50 and aee_mobility_currentMobilityIndex are cleared
with nil. No numeric result is returned.

The status flag and the numeric clears run before the argument parse and
before any argument-type check. A malformed or missing argument cannot
leave stale numeric state behind. The params form has no type arrays, so a
wrongly typed element does not throw.

Arguments:
  0: vehicle (OBJECT)
  1: rci (NUMBER) - the Rating Cone Index at the vehicle's position

Return Value: ARRAY [false, reason]
Example: [cursorObject, 72] call aee_mobility_fnc_calculateSoilStrength
Public: No
*/

// Clear stale state first. No argument-type operation runs before this.
missionNamespace setVariable [QGVAR(currentSoilStrengthKnown), false];
missionNamespace setVariable [QGVAR(currentVCI1), nil];
missionNamespace setVariable [QGVAR(currentVCI50), nil];
missionNamespace setVariable [QGVAR(currentMobilityIndex), nil];

// Permissive params: no type arrays, so a wrongly typed element cannot throw.
params [
    ["_vehicle", objNull],
    ["_rci", 0]
];

private _reason = "unverifiedInputs";

// Safe object-type check.  isEqualType cannot throw on a non-object, so a
// malformed vehicle argument stays "unverifiedInputs".
if (_vehicle isEqualType objNull) then {
    if (isNull _vehicle) then {
        _reason = "null";
    } else {
        if (_vehicle isKindOf "Tank" || {_vehicle isKindOf "Tracked_APC"}) then {
            _reason = "tracked";
        };
    };
};

missionNamespace setVariable [QGVAR(currentSoilStrengthReason), _reason];

[false, _reason]
