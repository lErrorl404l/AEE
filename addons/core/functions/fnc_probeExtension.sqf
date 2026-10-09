#include "..\script_component.hpp"

/*
Probe the native dev extension exactly once, at preInit.

callExtension returns an empty string when the extension is absent or a call
fails, and the payload string on success (the C ABI returns the payload only
when RVExtension returns errorCode 0).  So a non-empty probe means the
extension is present and ready.  The verdict is cached in QGVAR(extReady):
this probe is the ONLY callExtension that runs when the extension is missing,
so the hot path never calls the engine.

The extension is dev-only (ADR-033); it ships in no release artefact.
*/

private _extName = "aee_dev";
private _probe = _extName callExtension ["__probe__", []];
private _ready = (_probe isEqualType "") && {_probe != ""};

missionNamespace setVariable [QGVAR(extName), _extName];
missionNamespace setVariable [QGVAR(extReady), _ready];
