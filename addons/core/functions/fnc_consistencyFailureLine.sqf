#include "..\script_component.hpp"

/*
Consistency failure line (pure).

Builds the one-line human report for a failing invariant row.  It names every
producer that disagrees with the row expectation and its value, then the row
tolerance and the observed drift.  It is pure: no missionNamespace, no module
global and no engine command, so the tests drive it with fixtures.

The string it returns is the AEE_LOG_WARN payload.  The macro adds the
[AEE][core][WARN] tag, so the emitted line reads

  [AEE][core][WARN] consistency: <id> <name> | <moduleA> <var>=<v> | ... | tolerance <t> | drift <d>

The disagreement set mirrors fnc_evaluateConsistency: only the producers that
fail the row predicate are named, so the count of named entries matches the
verdict's modulesInDisagreement for the agree_within rows.  When the predicate
cannot localise the disagreement the whole producer set is named, so the line
never loses a value.

Arguments:
  0: Array - one invariant row
             [id, name, producers, predicate, tolerance, severity, grade, note].
  1: Array - the value map: [variableName, value] pairs.  A string value is
             treated as absent, matching the evaluator.
  2: Array - the evaluator verdict [id, pass, detail, modulesInDisagreement].

Returns:
  Array - [message, drift, disagreeingCount].
*/

params [
    ["_row", [], [[]]],
    ["_values", [], [[]]],
    ["_verdict", [], [[]]]
];

private _id = _row select 0;
private _name = _row select 1;
private _producers = _row select 2;
private _predicate = _row select 3;
private _tolerance = _row select 4;

private _missing = "__aee_no_data__";

// First matching pair.  A non-scalar value marks the producer absent, exactly
// as the evaluator's own lookup does.
private _lookup = {
    params ["_pairs", "_name", "_default"];
    private _out = _default;
    private _n = count _pairs;
    private _i = 0;
    while { _i < _n } do {
        private _pair = _pairs select _i;
        if ((_pair select 0) == _name) then { _out = _pair select 1; };
        _i = _i + 1;
    };
    _out
};

// The producer entries that carry a scalar value (NUMBER or BOOL), in row
// order.  A container (for example the per-cell aee_thermal_groundNodeStack
// HashMap) is dropped, matching the evaluator, so the line never compares a
// non-scalar.
private _present = [];
{
    private _v = [_values, _x select 1, _missing] call _lookup;
    if (_v isEqualTypeAny [0, true]) then {
        _present pushBack [_x select 0, _x select 1, _v];
    };
} forEach _producers;

private _ref = 0;
if (_present isNotEqualTo []) then { _ref = (_present select 0) select 2; };

// The producers that disagree with the row expectation.
private _bad = [];

if (_predicate == "agree_within") then {
    {
        if ((abs ((_x select 2) - _ref)) > _tolerance) then { _bad pushBack _x; };
    } forEach _present;
};

if (_predicate == "night_scene_agreement") then {
    if ((count _present) >= 3) then {
        private _scene = (_present select 1) select 2;
        private _isNight = (_present select 2) select 2;
        if (_isNight) then {
            if ((abs (_scene - _ref)) > (_tolerance * ((abs _ref) max 1))) then { _bad pushBack (_present select 1); };
        };
    };
};

if (_predicate == "daynight_consistent") then {
    if ((count _present) >= 4) then {
        private _skyTemp = (_present select 1) select 2;
        private _isNight = (_present select 2) select 2;
        private _nightClass = (_present select 3) select 2;
        private _skyMax = [_values, "aee_thermal_skyBandTempC_max", 60] call _lookup;
        if (_ref > _tolerance) then {
            if (_isNight) then { _bad pushBack (_present select 2); };
            if (_nightClass != 0) then { _bad pushBack (_present select 3); };
        };
        if (_ref < -_tolerance) then {
            if (!_isNight) then { _bad pushBack (_present select 2); };
            if (_nightClass == 0) then { _bad pushBack (_present select 3); };
            if (_skyTemp > _skyMax) then { _bad pushBack (_present select 1); };
        };
    };
};

// A predicate that cannot localise the disagreement names every producer.
if (_bad isEqualTo []) then { _bad = _present; };

// Drift is the spread of the present NUMBER values; a BOOL (the night flag
// INV-1 and INV-5 both carry) has no magnitude and is skipped.  A `for` loop,
// not a forEach
// block: an assignment to a file-local must survive the loop.
private _vmin = 0;
private _vmax = 0;
private _haveRange = false;
for "_i" from 0 to ((count _present) - 1) do {
    private _v = (_present select _i) select 2;
    if (_v isEqualType 0) then {
        if (_haveRange) then {
            if (_v < _vmin) then { _vmin = _v; };
            if (_v > _vmax) then { _vmax = _v; };
        } else {
            _vmin = _v;
            _vmax = _v;
            _haveRange = true;
        };
    };
};
private _drift = _vmax - _vmin;

private _message = "consistency: " + _id + " " + _name;
for "_i" from 0 to ((count _bad) - 1) do {
    private _entry = _bad select _i;
    _message = _message + " | " + (_entry select 0) + " " + (_entry select 1) + "=" + (str (_entry select 2));
};
_message = _message + " | tolerance " + (str _tolerance) + " | drift " + (str _drift);

[_message, _drift, count _bad]
