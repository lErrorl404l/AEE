// The dev channel starts only when the four-layer gate holds. Failure is a
// silent no-op: no per-frame handler, no verb table, no log line.
if !(call aee_dev_fnc_devGateLive) exitWith {};

aee_dev_verbs = call aee_dev_fnc_devVerbs;

// The extension raises this event for every request it forwards. The dispatcher
// parses the request literal and answers with the callExtension argument list.
// A refused or malformed request answers with an error and the handler stays up.
addMissionEventHandler ["ExtensionCallback", {
    params ["_name", "_function", "_data"];
    if (_name != "aee_dev") exitWith {};
    private _reply = [_function, _data] call aee_dev_fnc_devDispatch;
    if !(isNil "_reply") then {
        "aee_dev" callExtension _reply;
    };
}];
