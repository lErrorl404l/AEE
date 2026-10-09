/*
fnc_devDispatch - the SQF half of the extension callback bridge.

The extension raises the `ExtensionCallback` mission event with the name
"aee_dev", the function "exec" and an SQF-literal request. This function parses
the request with `parseSimpleArray` ONLY, runs the named operation through
fnc_devExec, and returns the `callExtension` argument list that answers the
extension:

    ["reply", [id, payload]]

The caller (the event handler in XEH_postInit) forwards that list to
`"aee_dev" callExtension`, which unblocks the waiting HTTP request. The id is
echoed so the extension can correlate the reply with the request it allocated.

The parse is the trust boundary. Agent input is a literal array and is never
compiled. A malformed request returns an error reply correlated by the id it
can read, and the callback stays up.
*/
params [["_function", ""], ["_data", ""]];

if (_function != "exec") exitWith {};

private _request = parseSimpleArray _data;
if ((count _request) < 3) exitWith {
    private _id = if ((count _request) > 0) then { _request select 0 } else { 0 };
    ["reply", [str _id, "error: malformed payload"]]
};

private _result = [_request select 1, _request select 2] call aee_dev_fnc_devExec;

["reply", [str (_request select 0), str _result]]
