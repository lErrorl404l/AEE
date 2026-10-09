#include "..\script_component.hpp"

/*
AEE real-time simulation clock (Pillar 1 - one clock).

One authoritative monotonic time source for every throttled model.  It
publishes QGVAR(simTime) (aee_core_simTime) once per frame, advanced from
diag_tickTime.  diag_tickTime is real seconds since game start: it is
monotonic, it advances during pause, and it ignores accTime
(docs/engine/engine-commands-and-features.md:424).

It does NOT publish a shared per-frame delta.  A throttled handler that read a
per-frame delta as its interval would read about 1/FPS and under-integrate -
the eye-driver and thermal-AGC defect class (commits f36bc216 and fc81d68e,
probe P79).  Each throttled model instead keeps its own _lastSimTime and
computes _dt = aee_core_simTime - _lastSimTime once per run.  A model that needs
simulation rather than real time scales by accTime explicitly.

Tick order (declared once): the per-frame handler in XEH_postInit.sqf is
registered before the environment tick and before every model handler, so
aee_core_simTime is current when any model reads it in the same frame.
*/

private _now = diag_tickTime;

// Real monotonic time, published as the one clock.  diag_tickTime never
// decreases, so the published series is monotonic by construction.
missionNamespace setVariable [QGVAR(simTime), _now];

// ─── World-clock jump contract ─────────────────────────────────────────────
// A time skip (skipTime, setDate, an Eden time change) moves the world clock
// (dayTime) in one step; diag_tickTime does not.  Compare dayTime - NOT time,
// which does not jump on skipTime - and wrap the 86400 s (24 h) day so a
// midnight crossing is not read as a jump.  On a jump, raise
// QGVAR(clockJump) for exactly one tick so the eye adaptation and the thermal
// AGC re-seed (arrive adapted) instead of chasing the jumped scene.  The
// 0.05 h threshold sits above the largest advance one frame can produce under
// the 100x accTime clamp and below the smallest useful skip (the same bound
// fnc_eyeTimeSkip uses).
private _day = dayTime;
private _prevDay = missionNamespace getVariable [QGVAR(clockLastDayTime), -1];
private _jump = false;
if (_prevDay isEqualType 0) then {
    if (_prevDay >= 0) then {
        private _delta = _day - _prevDay;
        if (_delta > 12) then { _delta = _delta - 24; };
        if (_delta < -12) then { _delta = _delta + 24; };
        _jump = abs _delta > 0.05;
    };
};
missionNamespace setVariable [QGVAR(clockLastDayTime), _day];
missionNamespace setVariable [QGVAR(clockJump), _jump];
