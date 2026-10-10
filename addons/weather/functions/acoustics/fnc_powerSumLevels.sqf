#include "..\..\script_component.hpp"

/*
Power sum of sound levels (issue #109).

Independent, incoherent sound sources add by POWER, not by level.  The
combined level of the levels L_i is

    L_total = 10 * log10( sum_i 10^(L_i / 10) )        dB

SOURCE: the energetic (logarithmic) addition of sound levels is the standard
decibel-addition procedure.  ISO 1996-1:2016, "Acoustics - Description,
measurement and assessment of environmental noise - Part 1: Basic quantities
and assessment procedures", defines the combined level of incoherent sources
this way.  Two equal 50 dB sources sum to 53 dB (10*log10(2) = +3.01 dB).

A level at or below 0 dB (or a non-number) is a SILENT source: it contributes
nothing, so an empty list or an all-silent list returns 0 rather than
10*log10(count).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.

Arguments:
  0: Array - the source levels in dB

Returns:
  Number - the combined level in dB
*/

params [["_levels", [], [[]]]];

private _sum = 0;
{
    if ((_x isEqualType 0) && (_x > 0)) then {
        _sum = _sum + (10 ^ (_x / 10));
    };
} forEach _levels;

if (_sum <= 0) exitWith { 0 };

10 * (log _sum)
