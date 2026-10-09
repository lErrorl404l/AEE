#include "..\script_component.hpp"

/*
The kernel registry (Pillar 2 - the kernel interface dispatcher).

One row per dispatched kernel.  Each row maps the kernel id to:
  0: the SQF reference function (the pure SQF kernel, the fallback), and
  1: the native function name a future extension implements.

Both paths live behind the single dispatcher FUNC(dispatchKernel), so a caller
names the kernel once and never branches on the extension.
*/

private _table = createHashMapFromArray [
    ["calculateHailEnergy", ["aee_atmos_fnc_calculateHailEnergy", "kernel.calculateHailEnergy"]],
    ["calculateBallisticDrag", ["aee_ballistics_fnc_calculateBallisticDrag", "kernel.calculateBallisticDrag"]],
    ["eyeAdaptStep", ["aee_optics_fnc_eyeAdaptStep", "kernel.eyeAdaptStep"]],
    ["eyeMesopicWeight", ["aee_optics_fnc_eyeMesopicWeight", "kernel.eyeMesopicWeight"]],
    ["eyePupilSteady", ["aee_optics_fnc_eyePupilSteady", "kernel.eyePupilSteady"]],
    ["eyePupilStep", ["aee_optics_fnc_eyePupilStep", "kernel.eyePupilStep"]],
    ["eyeTimeSkip", ["aee_optics_fnc_eyeTimeSkip", "kernel.eyeTimeSkip"]],
    ["thermalImperfectionParams", ["aee_thermal_fnc_thermalImperfectionParams", "kernel.thermalImperfectionParams"]],
    ["thermalWetDistortionParams", ["aee_thermal_fnc_thermalWetDistortionParams", "kernel.thermalWetDistortionParams"]]
];

missionNamespace setVariable [QGVAR(kernelTable), _table];
