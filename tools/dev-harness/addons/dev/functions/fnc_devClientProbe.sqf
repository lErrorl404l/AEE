/*
fnc_devClientProbe - the client half of the probe bridge (ADR-033).

The console runs server-side, so a headless-client probe cannot answer there.
This function runs on a non-dedicated machine, evaluates the named probe and
publishes its verdict as aee_dev_clientprobe_<tag>, which the console reads with
`get`.  A dedicated server skips it.  A headless client has hasInterface false;
it carries a headless-client probe, but an interface probe stays a manual
ceiling and is never claimed here.
*/
if (isDedicated) exitWith {};

params [["_tag", ""]];

private _verdict = [false, "no client predicate for " + _tag];
switch (_tag) do {
    case "P136": {
        _verdict = [!isDedicated, format ["non-dedicated machine, hasInterface=%1", hasInterface]];
    };
    default {};
};

missionNamespace setVariable [format ["aee_dev_clientprobe_%1", _tag], str _verdict, true];
_verdict
