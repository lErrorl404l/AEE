#include "..\..\script_component.hpp"
/*
Magazine mass (the load-carriage library). GENERATED FILE.

This is a runtime projection of the magazine research data under
data/ballistics/. It is written by
tools/validation/gen_runtime_magazines.py and must not be edited by hand.

A mod classname carries two signals: the capacity before "Rnd" and the
chambering token, as in "30Rnd_556x45_Stanag". The table holds the median
of the published masses for each capacity and chambering, so an unknown
magazine still resolves. A classname that states no capacity falls back to
the capacity tier.

Argument:
  0: magazine (STRING, a CfgMagazines classname, default "")

Returns the empty magazine mass in kg, or 0 when nothing matches.
*/

params [["_magazine", "", [""]]];
if (_magazine == "") exitWith { 0 };

private _lower = toLower _magazine;

// The capacity: the digits that precede "rnd".
private _capacity = 0;
private _marker = _lower find "rnd";
if (_marker > 0) then {
    private _digits = "";
    private _index = _marker - 1;
    while {_index >= 0} do {
        private _character = _lower select [_index, 1];
        if !(_character in "0123456789") exitWith {};
        _digits = _character + _digits;
        _index = _index - 1;
    };
    if (_digits != "") then { _capacity = parseNumber _digits; };
};

// [chambering token, capacity, empty mass g, published count]
private _TABLE = [
    ["40sw", 13, 50.0, 1],
    ["40sw", 30, 170.0, 1],
    ["45acp", 7, 70.8, 1],
    ["45acp", 10, 110.0, 1],
    ["45acp", 12, 110.0, 2],
    ["45acp", 20, 181.4, 1],
    ["45acp", 25, 170.0, 1],
    ["45acp", 50, 1134.0, 1],
    ["45acp", 100, 1769.0, 1],
    ["46x30", 20, 100.0, 1],
    ["46x30", 40, 200.0, 1],
    ["50bmg", 5, 453.6, 1],
    ["545x39", 30, 181.4, 3],
    ["556x45", 10, 80.9, 2],
    ["556x45", 20, 113.4, 1],
    ["556x45", 30, 141.7, 8],
    ["556x45", 35, 300.0, 1],
    ["556x45", 40, 187.1, 1],
    ["556x45", 50, 420.0, 1],
    ["556x45", 60, 581.2, 1],
    ["556x45", 200, 269.3, 1],
    ["762x39", 10, 113.4, 1],
    ["762x39", 20, 141.7, 1],
    ["762x39", 30, 184.3, 6],
    ["762x39", 40, 201.3, 1],
    ["762x39", 60, 357.2, 1],
    ["762x51", 5, 87.9, 1],
    ["762x51", 10, 116.2, 2],
    ["762x51", 20, 167.3, 3],
    ["762x51", 25, 184.3, 1],
    ["762x51", 50, 771.1, 1],
    ["9x19", 10, 70.0, 1],
    ["9x19", 12, 65.2, 2],
    ["9x19", 13, 85.0, 1],
    ["9x19", 15, 84.0, 8],
    ["9x19", 16, 80.0, 1],
    ["9x19", 17, 48.2, 3],
    ["9x19", 21, 80.8, 2],
    ["9x19", 25, 200.0, 1],
    ["9x19", 27, 56.7, 1],
    ["9x19", 40, 138.9, 1],
    ["9x19", 50, 472.0, 2]
];

private _match = 0;
{
    _x params ["_calibre", "_cap", "_mass"];
    if ((_lower find _calibre >= 0) && _cap == _capacity) exitWith {
        _match = _mass;
    };
} forEach _TABLE;

if (_match == 0 && _capacity == 0) then {
    // No capacity stated: the first row for the chambering. A stated
    // capacity that the table lacks falls through to the tier instead,
    // so a 75 round magazine never takes a 30 round mass.
    {
        _x params ["_calibre", "_cap", "_mass"];
        if (_lower find _calibre >= 0) exitWith { _match = _mass; };
    } forEach _TABLE;
};

if (_match == 0) then {
    // The capacity tier.
    private _tiers = [
    [5, 85],
    [7, 71],
    [10, 85],
    [15, 105],
    [17, 90],
    [20, 113],
    [25, 200],
    [30, 142],
    [40, 187],
    [50, 227],
    [60, 250],
    [75, 300],
    [100, 500]
    ];
    {
        _x params ["_cap", "_mass"];
        if (_cap == _capacity) exitWith { _match = _mass; };
    } forEach _tiers;
};

if (_match == 0) exitWith { 0 };
_match / 1000
