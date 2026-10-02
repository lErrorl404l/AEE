#include "..\script_component.hpp"
/*
Per-device NVG tube model (operator request, follows issue #215).

fnc_getNvgDeviceProperties returns the GENERATION physics (the fallback).
This function reads the generated per-DEVICE table that
tools/validation/gen_device_data.py builds from the corpus under
data/device/. The table holds the published corrections that override the
generation: output colour, limiting resolution, signal-to-noise ratio and
halo.

The operator's rule: a device is a device, not a generation.  Two Gen 3
tubes differ in build, output colour and performance, and must render and
behave differently.

Every value now lives in the corpus with its unit, source, locator, state
and grade. The generator writes the runtime table from it, so the values
are generated SQF and not hand-kept here. The generation fallback stays:
an unmatched device returns no corrections and fnc_applyNVGTubeModel keeps
the generation value.

Fields a device does not publish return -1 and the caller keeps the
generation value.  A field is never copied from a sibling device.

Returns [deviceKey, colour, resLpmm, snr, haloMm, sourced]
  deviceKey - the resolved device family, for the log
  colour    - "grn" (P43 green), "wht" (P45 white), or "" (states none)
  resLpmm   - limiting resolution lp/mm, or -1 (unsourced)
  snr       - signal-to-noise ratio, or -1 (unsourced)
  haloMm    - halo diameter on the tube face, mm, or -1 (unsourced)
  sourced   - true when at least one field came from a device source
*/

params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { ["GEN1", "", -1, -1, -1, false] };

private _hmd = hmd _unit;
if (_hmd == "") exitWith { ["GEN1", "", -1, -1, -1, false] };

// The generated table resolves the class to its night-vision row. The
// family filter stops a class that a thermal row also names (the ENVG-B)
// from tying here.
private _match = [_hmd, "nvg"] call FUNC(getDeviceMatch);
if (_match isEqualTo []) exitWith { ["GEN1", "", -1, -1, -1, false] };

private _key = _match select 0;
private _values = _match select 5;
private _tableColour = _values select 0;

// ─── Output colour the device states in its classname ─────────────────────
// P43 green and P45 white are the two phosphors in service (Exosens,
// Elbit).  A device that states a colour in its classname states its own
// tube, so that token wins over the catalogue value.
private _colour = "";
{
    switch (_x) do {
        case "grn";
        case "green";
        case "p43": { _colour = "grn"; };
        case "wht";
        case "white";
        case "wp";
        case "p45": { _colour = "wht"; };
    };
} forEach ((toLower _hmd) splitString "_");
if ((_colour == "") && (_tableColour == "green")) then { _colour = "grn"; };
if ((_colour == "") && (_tableColour == "white")) then { _colour = "wht"; };

// A field the row leaves absent arrives as 0, so return -1 and the caller
// keeps the generation value.
private _res = -1;
private _snr = -1;
private _halo = -1;
if ((_values select 1) > 0) then { _res = _values select 1; };
if ((_values select 2) > 0) then { _snr = _values select 2; };
if ((_values select 3) > 0) then { _halo = _values select 3; };

private _sourced = (_colour != "") || (_res > 0) || (_snr > 0) || (_halo > 0);
[_key, _colour, _res, _snr, _halo, _sourced]
