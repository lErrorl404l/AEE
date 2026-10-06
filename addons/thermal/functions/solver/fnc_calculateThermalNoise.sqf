#include "..\..\script_component.hpp"
/*
NETD-based thermal sensor noise floor (pure).

The display grain path needs a normalised noise figure in 0..1.  It grows
with the sensor-to-target range squared, because the atmospheric path adds
scintillation and absorption noise along the line of sight, and water vapour
adds its own noise.  A lower-resolution detector samples the scene more
coarsely, so it carries more spatial noise against the 640-wide uncooled
reference.

The noise is

    noise = netd * ((rangeM / 1000) ^ 2) * (640 / max(resX, 1))
                 * (1 + (humidityPct / 100) * 0.5)

clamped to 0..1.  The range is a REAL sensor-to-target range supplied by the
caller, never the engine view distance.  The 640 detector-width reference
and the 0.5 humidity coefficient are UNSOURCED display heuristics recorded
in the per-constant register (docs/wiki/chapters/sensor-value-audit.md).

The caller supplies the range.  Where no target exists (a dedicated server,
or a display-only tick), the caller uses the declared default 1000 m, also
UNSOURCED, because the device corpus holds no detection range.

Arguments:
  0: _netdDegC    (NUMBER) device NETD in C, >= 0
  1: _rangeM      (NUMBER) sensor-to-target range in metres, >= 0
  2: _resX        (NUMBER) detector width in pixels, >= 1
  3: _humidityPct (NUMBER) relative humidity in percent, 0..100

Return Value: NUMBER - the normalised noise floor, 0..1.
Public: No
*/

params [
    ["_netdDegC", 0.05, [0]],
    ["_rangeM", 1000, [0]],
    ["_resX", 640, [0]],
    ["_humidityPct", 50, [0]]
];

private _netd = _netdDegC max 0;
private _range = _rangeM max 0;
private _res = _resX max 1;
private _hum = (_humidityPct max 0) min 100;

private _noise = _netd * ((_range / 1000) ^ 2) * (640 / _res) * (1 + (_hum / 100) * 0.5);

(_noise max 0) min 1
