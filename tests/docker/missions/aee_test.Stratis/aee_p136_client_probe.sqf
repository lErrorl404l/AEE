// PHASE 136: a client-only probe, guarded !isDedicated.
//
// The [P136] verdict is produced only on a non-dedicated machine. A dedicated
// server reports isDedicated true, so this file exits before it reads anything
// and a server-only run can never claim the probe passed. A headless client has
// hasInterface false; it carries the probe, but it does NOT satisfy an
// interface probe. The console reaches it with remoteExec (fnc_devClientProbe)
// and reads the published aee_dev_clientprobe_P136 verdict.
//
// Emits one [P136] PASS/FAIL line and publishes its verdict for the console.

if (isDedicated) exitWith {};

private _ok = !isDedicated;
private _diag = format ["non-dedicated machine, hasInterface=%1", hasInterface];

missionNamespace setVariable ["aee_dev_clientprobe_P136", str [_ok, _diag], true];

diag_log text format [
    "[P136] [%1] client probe reached a non-dedicated machine (hasInterface=%2)",
    (["FAIL", "PASS"] select _ok),
    hasInterface
];
