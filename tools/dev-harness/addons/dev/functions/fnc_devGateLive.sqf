/*
fnc_devGateLive - the driver for fnc_devGate.

Reads the engine conditions once and returns the four-layer gate. It logs
nothing, so a failed gate is silent.

Layer 1 is the build marker set by XEH_preInit. Layer 2 is true unless the
mission marks the build a release. Layer 3 reads isFilePatchingEnabled, the
sentinel file and the host role. Layer 4 is true: the verb table is a fixed
whitelist and no agent input is compiled.
*/
private _structural = missionNamespace getVariable ["aee_dev_present", false];
private _release = missionNamespace getVariable ["aee_dev_release", false];
private _sentinel = "aee_dev\enable.txt";
private _devHost = (!isDedicated) || {missionNamespace getVariable ["aee_dev_allowServer", false]};

[
    _structural,
    !_release,
    isFilePatchingEnabled,
    fileExists _sentinel,
    _devHost,
    true
] call aee_dev_fnc_devGate
