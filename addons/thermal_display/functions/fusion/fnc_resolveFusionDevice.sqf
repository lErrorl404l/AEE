#include "..\..\script_component.hpp"
/*
 * Fusion device pair resolver (issue #204, Track B ENVG-B).
 *
 * Returns BOTH channels of the headset: the image-intensifier tube row from
 * fnc_getNvgDeviceProperties (family nvg) and the thermal channel row from
 * fnc_getThermalDeviceProperties (family thermal), plus the thermal
 * channel's half-angle and the provenance of that figure.
 *
 * The thermal device is read from the corpus through the generated matcher
 * with the "thermal" family filter, so a class that resolves to a corpus
 * thermal row (the ECOTI) drives the field.  No vanilla class resolves to
 * the ECOTI row: the row is DATA-ONLY in that case, the field stays the
 * declared default, and the caller's gate log prints the raw thermal device
 * id, which is empty for the data-only case.  That is the honest record
 * that the row is not triggered in game.
 *
 * The hmd classname tokens identify the fused headsets that hold no corpus
 * thermal row: the ENVG-B (nvgogglesb) and the BNVD-FUSED (bnvd / fbino).
 * This mirrors the tube model, which identifies the phosphor from the same
 * classname.
 *
 * Params:
 *   0: _unit (OBJECT, default player) - the operator.
 *
 * Returns: [nvgRow, thermalRow, halfAngleDeg, sourceLabel, axisLabel,
 *           deviceLabel, thermalDeviceId].
 *   nvgRow      - [generation, sensitivity, resolution, weightKg, tubeCount,
 *                  fovDeg] from fnc_getNvgDeviceProperties.
 *   thermalRow  - [netdDegC, resX, resY, weightKg, refreshHz, cooled] from
 *                  fnc_getThermalDeviceProperties.
 *   halfAngleDeg- the thermal channel half-angle in degrees.
 *   sourceLabel - declared, derived or published.
 *   axisLabel   - declared, diagonal or circular.
 *   deviceLabel - ECOTI, BNVD-FUSED, ENVG-B or unknown.
 *   thermalDeviceId - the corpus thermal device id, or "" when no class
 *                  resolves to a thermal corpus row.
 */
params [["_unit", player, [objNull]]];

private _nvgRow = [_unit] call EFUNC(nightvision,getNvgDeviceProperties);
private _thermalRow = [_unit] call EFUNC(thermal,getThermalDeviceProperties);

private _hmd = toLower (hmd _unit);
private _match = [_hmd, "thermal"] call EFUNC(nightvision,getDeviceMatch);
private _deviceId = if (_match isEqualTo []) then { "" } else { _match select 0 };

private _deviceLabel = "unknown";
if (_deviceId == "ecoti") then {
    _deviceLabel = "ECOTI";
} else {
    {
        if ((_x == "nvgogglesb") || (_x == "envg")) then { _deviceLabel = "ENVG-B"; };
        if ((_x == "bnvd") || (_x == "fbino") || (_x == "fbinof")) then { _deviceLabel = "BNVD-FUSED"; };
    } forEach (_hmd splitString "_");
};

private _field = [_deviceLabel] call FUNC(fusionThermalField);
[
    _nvgRow,
    _thermalRow,
    _field select 0,
    _field select 1,
    _field select 2,
    _deviceLabel,
    _deviceId
]
