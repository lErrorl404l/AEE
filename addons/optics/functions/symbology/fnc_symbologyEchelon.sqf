#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyEchelon
 *
 * Pure echelon kernel.  Maps a group size to an echelon token.  PURE: the
 * size arrives as an argument, so the kernel reads no group, no unit and no
 * world.
 *
 * The bands are AEE derivation, UNSOURCED.  MIL-STD-2525D and APP-6(C) give
 * a nominal strength for each echelon, not a count function, so the band
 * edges are AEE own and are marked as such.  The bands are monotone: a
 * larger group never yields a lower echelon.
 *
 * Arguments:
 *   0: _groupSize <NUMBER> the group size
 *
 * Return: <STRING> an echelon token, for example "squad".
 */
params [
    ["_groupSize", 0, [0]]
];

private _size = round _groupSize;
if (_size < 1) then { _size = 1; };

private _bands = [
    [1, "team"],
    [6, "squad"],
    [13, "section"],
    [40, "platoon"],
    [150, "company"],
    [500, "battalion"],
    [2000, "regiment"],
    [6000, "brigade"],
    [15000, "division"],
    [60000, "corps"],
    [120000, "army"],
    [300000, "army_group"]
];

private _token = "region";
private _found = false;
for "_i" from 0 to ((count _bands) - 1) do {
    if (!_found && (_size <= ((_bands select _i) select 0))) then {
        _token = (_bands select _i) select 1;
        _found = true;
    };
};

_token
