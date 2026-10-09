/*
fnc_devExec - the console operation table.

One operation is a pure function of its arguments plus the engine state it
reads. The dispatcher calls it after parsing the request literal and turns
any result into a reply. Every guard returns an error string, so an unknown or
refused operation answers with an error and the channel stays up.

Layer 4: no operation compiles agent input. The `eval` verb is added in the
console command set and is reachable only because the channel itself exists
only when the four-layer gate holds.
*/
params [["_op", ""], ["_args", []]];

if (_op == "ping") exitWith { "pong" };
if (_op == "verbs") exitWith { aee_dev_verbs };

"error: unknown verb"
