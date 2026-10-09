/*
fnc_devRemote - the server half of the remoteExec bridge.

The console runs server-side, so a plain read reaches server-local state only.
This bridge broadcasts a request to every client. Each client answers into a
public variable named aee_dev_client_<verb>_<name>, which the console then
reads. With no client connected the reply variable is absent and the console
reports no value; a dedicated server renders no local state. This is the
documented client-local ceiling, never a failed console call.
*/
params [["_verb", ""], ["_name", ""]];

[_verb, _name] remoteExecCall ["aee_dev_fnc_devClientReply", -2];

"requested"
