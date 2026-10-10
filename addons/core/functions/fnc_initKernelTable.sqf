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
    ["eyeAdaptStep", ["aee_eye_fnc_eyeAdaptStep", "kernel.eyeAdaptStep"]],
    ["eyeMesopicWeight", ["aee_eye_fnc_eyeMesopicWeight", "kernel.eyeMesopicWeight"]],
    ["eyePupilSteady", ["aee_eye_fnc_eyePupilSteady", "kernel.eyePupilSteady"]],
    ["eyePupilStep", ["aee_eye_fnc_eyePupilStep", "kernel.eyePupilStep"]],
    ["eyeTimeSkip", ["aee_eye_fnc_eyeTimeSkip", "kernel.eyeTimeSkip"]],
    ["thermalImperfectionParams", ["aee_thermal_display_fnc_thermalImperfectionParams", "kernel.thermalImperfectionParams"]],
    ["thermalWetDistortionParams", ["aee_thermal_display_fnc_thermalWetDistortionParams", "kernel.thermalWetDistortionParams"]],
    ["calculateStationPressure", ["aee_atmos_fnc_calculateStationPressure", "kernel.calculateStationPressure"]],
    ["calculateRelativeHumidity", ["aee_atmos_fnc_calculateRelativeHumidity", "kernel.calculateRelativeHumidity"]],
    ["calculateAirDensityKernel", ["aee_ballistics_fnc_calculateAirDensityKernel", "kernel.calculateAirDensityKernel"]],
    ["solveTwoNodeKernel", ["aee_thermal_fnc_solveTwoNodeKernel", "kernel.solveTwoNodeKernel"]]
];

missionNamespace setVariable [QGVAR(kernelTable), _table];
