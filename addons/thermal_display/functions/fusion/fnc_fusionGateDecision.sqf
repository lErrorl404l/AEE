#include "..\..\script_component.hpp"
/*
 * Fusion capability decision (issue #204, Track B ENVG-B).
 *
 * Pure decision kernel: no engine state, no player, no hasInterface.  The
 * caller fnc_isFusionCapable reads the engine state (the vision mode, the
 * HMD config's thermal channel and the fusionAlwaysOn setting) and passes
 * it here, so the rule lives in one testable place and the caller stays a
 * thin reader.  The P80 probe and the unit suite execute this kernel.
 *
 * Fusion needs BOTH an active NVG base (vision mode 1) AND either a
 * thermal-capable headset or the fusionAlwaysOn setting.  A non-NVG mode
 * (mode 2 thermal, mode 0 normal) is never capable, even when
 * fusionAlwaysOn is on, because there is no intensified base to fuse over.
 *
 * Params:
 *   0: _visionMode (SCALAR) - currentVisionMode of the operator.
 *   1: _hasThermal (BOOL) - the HMD config exposes a thermal channel.
 *   2: _fusionAlwaysOn (BOOL) - the aee_thermal_display_fusionAlwaysOn setting.
 *
 * Returns: BOOL - true when the fusion overlay may render.
 */
params [
    ["_visionMode", -1, [0]],
    ["_hasThermal", false, [true]],
    ["_fusionAlwaysOn", false, [true]]
];

(_visionMode == 1) && (_fusionAlwaysOn || _hasThermal)
