/*
fnc_devExec - the console operation table.

One operation is a function of its arguments plus the engine state it reads.
The dispatcher calls it after parsing the request literal and turns any result
into a reply. Every guard returns an error string, so an unknown or refused
operation answers with an error and the channel stays up.

`set` refuses a variable name that is not ours. `callfunc` refuses a function
that is not in the fnc_devFuncs whitelist. `dump`, `scenario` and `probes`
resolve a named function and call it; a missing name is an error.

Layer 4: no operation compiles agent input except `eval`. `eval` is reachable
only because the channel itself exists only when the four-layer gate holds.
*/
params [["_op", ""], ["_args", []]];

if (_op == "ping") exitWith { "pong" };

if (_op == "verbs") exitWith { aee_dev_verbs };

if (_op == "get") exitWith {
    if ((count _args) < 1) exitWith { "error: get needs a name" };
    str (missionNamespace getVariable (_args select 0))
};

if (_op == "set") exitWith {
    if ((count _args) < 2) exitWith { "error: set needs a name and a value" };
    private _name = _args select 0;
    if ((_name select [0, 4]) != "aee_") exitWith { "error: set name must start aee_" };
    missionNamespace setVariable [_name, _args select 1];
    "ok"
};

if (_op == "dump") exitWith {
    if ((count _args) < 1) exitWith { "error: dump needs a component" };
    private _fnc = missionNamespace getVariable ("aee_" + (_args select 0) + "_fnc_dumpState");
    if (isNil "_fnc" || { (typeName _fnc) != "CODE" }) exitWith { "error: no dump for component" };
    str ([] call _fnc)
};

if (_op == "eval") exitWith {
    if ((count _args) < 1) exitWith { "error: eval needs code" };
    str ([] call compile (_args select 0))
};

if (_op == "callfunc") exitWith {
    if ((count _args) < 1) exitWith { "error: callfunc needs a function name" };
    private _fncName = _args select 0;
    private _allowed = false;
    { if (_x == _fncName) then { _allowed = true; }; } forEach aee_dev_funcs;
    if (!_allowed) exitWith { "error: function not whitelisted" };
    private _fnc = missionNamespace getVariable _fncName;
    if (isNil "_fnc" || { (typeName _fnc) != "CODE" }) exitWith { "error: no such function" };
    private _fncArgs = if ((count _args) > 1) then { _args select 1 } else { [] };
    str (_fncArgs call _fnc)
};

if (_op == "batch") exitWith {
    private _out = [];
    { _out pushBack ([_x select 0, _x select 1] call aee_dev_fnc_devExec); } forEach _args;
    _out
};

if (_op == "scenario") exitWith {
    if ((count _args) < 1) exitWith { "error: scenario needs a name" };
    private _fnc = missionNamespace getVariable ("aee_dev_scenario_" + (_args select 0));
    if (isNil "_fnc" || { (typeName _fnc) != "CODE" }) exitWith { "error: no such scenario" };
    str ([] call _fnc)
};

if (_op == "probes") exitWith {
    if ((count _args) < 1) exitWith { "error: probes needs a batch name" };
    private _fnc = missionNamespace getVariable ("aee_dev_probes_" + (_args select 0));
    if (isNil "_fnc" || { (typeName _fnc) != "CODE" }) exitWith { "error: no such probe batch" };
    [] call _fnc
};

if (_op == "remote") exitWith {
    if ((count _args) < 2) exitWith { "error: remote needs a verb and a name" };
    [(_args select 0), (_args select 1)] call aee_dev_fnc_devRemote
};

"error: unknown verb"
