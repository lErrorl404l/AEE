/*
fnc_devClientReply - the client half of the remoteExec bridge.

Runs on every client with an interface. It publishes the named client-local
variable as a public string, so the server console can read it as
aee_dev_client_<verb>_<name>. A headless client has hasInterface false and is
skipped.
*/
if (!hasInterface) exitWith {};

params [["_verb", ""], ["_name", ""]];

private _value = missionNamespace getVariable _name;
missionNamespace setVariable [
    format ["aee_dev_client_%1_%2", _verb, _name],
    str _value,
    true
];
