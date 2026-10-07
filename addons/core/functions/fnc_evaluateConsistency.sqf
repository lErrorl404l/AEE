#include "..\script_component.hpp"

/*
Pure cross-module consistency evaluator.

It takes the invariant table (data/consistency/invariants.json, compiled in by
fnc_consistencyLoadTable) and a value map, and returns one verdict per row.
It reads NO world state: there is no missionNamespace getVariable and no
engine query.  It calls no other module's function.  The only commands used
are the pure numeric operators abs, min, max, count, select, str and log.

Arguments:
  0: ARRAY - the invariant table.  Each row is
             [id, name, producers, predicate, tolerance, severity, grade, note].
  1: ARRAY - the value map: a list of [variableName, value] pairs.  A name
             absent from the map marks that producer no-data.  The map may
             also carry predicate bounds and references under supplied keys
             (see below); these are data, not world reads.

Supplied keys the map may carry:
  aee_thermal_skyBandTempC_max   NUMBER  the night sky band ceiling,
                                 default 60 C, for daynight_consistent.

Return value:
  ARRAY - [overallPass, verdicts].  overallPass is a BOOL: true when every
  row passes.  verdicts is one entry per table row:
  [id, pass, detail, modulesInDisagreement].
    id                    STRING
    pass                  BOOL
    detail                STRING  short reason
    modulesInDisagreement NUMBER  count of producer values that disagree with
                                  the row expectation (0 when it passes)

Predicate semantics:
  agree_within         every producer is within tolerance of the range.
  night_scene_agreement  only when the night flag is set, the second value
                       (the eye scene lux) agrees with the first (the core
                       illuminance) within the tolerance, a relative fraction.
                       Out of scope (pass) when the flag is clear.
  daynight_consistent  the night flag and the night classification agree
                       with the sun elevation.
*/

params [
    ["_table", [], [[]]],
    ["_values", [], [[]]]
];

// No-data marker.  A producer value is present only when it is a scalar
// (NUMBER or BOOL).  A missing producer resolves to this string, and a
// container (for example the per-cell aee_thermal_groundNodeStack HashMap) is
// treated the same way, so a non-scalar value can never reach a numeric
// comparison and the evaluator never throws on it.
private _missing = "__aee_no_data__";

// Look up a named value in the [name, value] pair list.  A small linear scan
// keeps the evaluator free of any hash container and is bounded by the table.
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

private _verdicts = [];
private _allPass = true;
private _rowCount = count _table;
private _r = 0;
while { _r < _rowCount } do {
    private _row = _table select _r;
    private _id = _row select 0;
    private _producers = _row select 2;
    private _predicate = _row select 3;
    private _tolerance = _row select 4;

    // Gather the producer values the map carries.
    private _vals = [];
    private _producerCount = count _producers;
    private _p = 0;
    while { _p < _producerCount } do {
        private _pair = _producers select _p;
        private _v = [_values, _pair select 1, _missing] call _lookup;
        if (_v isEqualTypeAny [0, true]) then { _vals pushBack _v; };
        _p = _p + 1;
    };

    private _pass = true;
    private _count = 0;
    private _detail = "no-data";

    if ((count _vals) < _producerCount) then {
        // A missing producer is no-data, not a divergence.  The runtime
        // monitor marks the row no-data and never throws.
        _pass = true;
        _count = 0;
        _detail = "no-data";
    } else {
        if (_predicate == "agree_within") then {
            private _ref = _vals select 0;
            private _vmin = _ref;
            private _vmax = _ref;
            private _i = 0;
            while { _i < (count _vals) } do {
                private _value = _vals select _i;
                if (_value < _vmin) then { _vmin = _value; };
                if (_value > _vmax) then { _vmax = _value; };
                if ((abs (_value - _ref)) > _tolerance) then { _count = _count + 1; };
                _i = _i + 1;
            };
            _pass = ((_vmax - _vmin) <= _tolerance);
            _detail = "range " + (str (_vmax - _vmin));
        };

        if (_predicate == "night_scene_agreement") then {
            private _core = _vals select 0;
            private _scene = _vals select 1;
            private _isNight = _vals select 2;
            if (_isNight) then {
                if ((abs (_scene - _core)) > (_tolerance * ((abs _core) max 1))) then { _count = _count + 1; };
            };
            _pass = (_count == 0);
            _detail = "night " + (str _isNight) + " scene " + (str _scene) + " core " + (str _core);
        };

        if (_predicate == "daynight_consistent") then {
            private _sunElev = _vals select 0;
            private _skyTemp = _vals select 1;
            private _isNight = _vals select 2;
            private _nightClass = _vals select 3;
            private _skyMax = [_values, "aee_thermal_skyBandTempC_max", 60] call _lookup;
            if (_sunElev > _tolerance) then {
                if (_isNight) then { _count = _count + 1; };
                if (_nightClass != 0) then { _count = _count + 1; };
            };
            if (_sunElev < -_tolerance) then {
                if (!_isNight) then { _count = _count + 1; };
                if (_nightClass == 0) then { _count = _count + 1; };
                if (_skyTemp > _skyMax) then { _count = _count + 1; };
            };
            _pass = (_count == 0);
            _detail = "sun " + (str _sunElev) + " class " + (str _nightClass);
        };
    };

    if (!_pass) then { _allPass = false; };
    _verdicts pushBack [_id, _pass, _detail, _count];
    _r = _r + 1;
};

[_allPass, _verdicts]
