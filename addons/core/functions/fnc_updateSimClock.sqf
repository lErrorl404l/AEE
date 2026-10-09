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
