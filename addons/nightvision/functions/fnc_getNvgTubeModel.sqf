#include "..\script_component.hpp"
/*
Per-device NVG tube model (operator request, follows issue #215).

fnc_getNvgDeviceProperties returns the GENERATION physics (the fallback).
This function returns the PUBLISHED per-DEVICE corrections that override
it: output colour, limiting resolution, signal-to-noise ratio and halo.
The operator's rule: a device is a device, not a generation.  Two Gen 3
tubes differ in build, output colour and performance, and must render and
behave differently.

Fields a device does not publish return -1 and the caller keeps the
generation value.  A field is never copied from a sibling device.

Returns [deviceKey, colour, resLpmm, snr, haloMm, sourced]
  deviceKey - the resolved device family, for the log
  colour    - "grn" (P43 green), "wht" (P45 white), or "" (states none)
  resLpmm   - limiting resolution lp/mm, or -1 (unsourced)
  snr       - signal-to-noise ratio, or -1 (unsourced)
  haloMm    - halo diameter on the tube face, mm, or -1 (unsourced)
  sourced   - true when at least one field came from a device source

Sources (per value):
  Elbit AN/PVS-14 datasheet: P43 green (F9815) / P45 white (F9415).
  L3Harris AN/PVS-31C datasheet: P-45 white, 72 lp/mm min, SNR 33.0 min.
  L3Harris GPNVG-18 spec sheet: white phosphor, four MX-10160 tubes.
  L3Harris ENVG-B sell sheet: Gen III white phosphor, 72 lp/mm, SNR 32.
  L3Harris AN/PVS-15 (M953): Gen III, 27 mm objective.
  Elbit AN/AVS-9 datasheet: Gen 3 gated Pinnacle.
  ANVS AN/PVS-7 datasheet: multi-alkali, SNR 12-20.
  Exosens P43/P45: P43 is green, P45 is white (independent corroboration).
  sensor-device-library.md: PVS-5 28 lp/mm, 1PN58/63 30 lp/mm, 1PN138
    no tube figure; 1PN93 no tube figure.
  Cui et al., Chinese Optics Letters 10(6) 060401 (2012), Fig. 4: halo
    0.2388 mm (Gen II+) and 0.5533 mm (Gen III) at the tube face.
  Luminous gain and photocathode sensitivity are NOT published per device
  in any source read, so they stay on the generation value and are logged
  as unsourced rather than invented.
*/

params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { ["", "", -1, -1, -1, false] };

private _hmd = toLower (hmd _unit);
if (_hmd == "") exitWith { ["", "", -1, -1, -1, false] };

// ─── Output colour the device states in its classname ─────────────────────
// P43 green and P45 white are the two phosphors in service (Exosens,
// Elbit).  A device that states neither keeps the generation shape.
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

// ─── Device family and its published tube figures ─────────────────────────
// The order mirrors fnc_getNvgDeviceProperties so the two agree on the
// family.  A value of -1 means the device publishes no figure for it.
private _key = "";
private _res = -1;
private _snr = -1;
private _halo = -1;

switch (true) do {
    // GPNVG-18: white phosphor, four MX-10160 tubes (L3Harris).
    case (_hmd find "gpnvg" >= 0
        || _hmd find "pano" >= 0
        || _hmd find "nv_wide" >= 0): {
        _key = "GPNVG-18";
        _colour = "wht";
        _res = 64;
        _halo = 0.5533;
    };
    // ENVG-B / ENVG-II fused: Gen III white phosphor (L3Harris ENVG-B).
    case (_hmd find "envg" >= 0
        || _hmd find "psq-42" >= 0
        || _hmd find "psq-44" >= 0
        || _hmd find "nvgogglesb" >= 0): {
        _key = "ENVG";
        _colour = "wht";
        _res = 72;
        _snr = 32;
        _halo = 0.5533;
    };
    // PVS-31C is P-45 white, 72 lp/mm, SNR 33 (L3Harris datasheet).  The
    // PVS-31A is offered green or white, so a colour token still wins.
    case (_hmd find "pvs31" >= 0
        || _hmd find "pvs_31" >= 0
        || _hmd find "nvg_w" >= 0): {
        _key = "PVS-31";
        if (_colour == "") then { _colour = "wht"; };
        _res = 72;
        _snr = 33;
        _halo = 0.5533;
    };
    // AN/AVS-9 and ANVIS: Gen 3 gated Pinnacle, available green or white.
    case (_hmd find "anvis" >= 0
        || _hmd find "avs-9" >= 0
        || _hmd find "avs9" >= 0): {
        _key = "AN/AVS-9";
        _res = 64;
        _halo = 0.5533;
    };
    // AN/PVS-15: Gen III, 27 mm objective (L3Harris M953), green or white.
    case (_hmd find "pvs15" >= 0
        || _hmd find "pvs_15" >= 0): {
        _key = "AN/PVS-15";
        _res = 64;
        _halo = 0.5533;
    };
    // AN/PVS-14: Gen 3 GaAs, green (F9815) or white (F9415), SNR 31 min.
    case (_hmd find "pvs14" >= 0
        || _hmd find "pvs_14" >= 0
        || _hmd find "pvs-14" >= 0): {
        _key = "AN/PVS-14";
        _res = 64;
        _snr = 31;
        _halo = 0.5533;
    };
    // AN/PVS-7: multi-alkali, SNR 12-20 (ANVS sheet); resolution is
    // UNKNOWN per device (the sheet's 51-72 conflicts with the library's
    // 28, so neither is claimed here).
    case (_hmd find "pvs7" >= 0
        || _hmd find "pvs_7" >= 0): {
        _key = "AN/PVS-7";
        _snr = 12;
        _halo = 0.2388;
    };
    // AN/PVS-5: Gen 2, 28 lp/mm (sensor-device-library.md).
    case (_hmd find "pvs5" >= 0
        || _hmd find "pvs_5" >= 0): {
        _key = "AN/PVS-5";
        _res = 28;
        _halo = 0.2388;
    };
    // 1PN138 / 1PN97: no published tube figure.  Fall back explicitly.
    case (_hmd find "1pn138" >= 0
        || _hmd find "1pn97" >= 0): {
        _key = "1PN138/1PN97";
    };
    // 1PN93: no published tube figure.  Fall back explicitly.
    case (_hmd find "1pn93" >= 0): {
        _key = "1PN93";
    };
    // 1PN63 / 1PN58: Gen 1 S-20, 30 lp/mm (sensor-device-library.md).
    case (_hmd find "1pn63" >= 0
        || _hmd find "1pn58" >= 0): {
        _key = "1PN63/1PN58";
        _res = 30;
    };
    // Vanilla Gen 3 goggles: generation figure only, no device datasheet.
    case (_hmd find "nvgen3" >= 0
        || _hmd find "nvgoggles_indep" >= 0
        || _hmd find "nvgoggles" >= 0): {
        _key = "NVGoggles";
        _halo = 0.5533;
    };
    // Vanilla Gen 2 goggles.
    case (_hmd find "nvgen2" >= 0
        || _hmd find "nvgoggles_opfor" >= 0): {
        _key = "NVGoggles_OPFOR";
        _halo = 0.2388;
    };
    default {
        _key = "GEN1";
    };
};

private _sourced = (_colour != "") || (_res > 0) || (_snr > 0) || (_halo > 0);
[_key, _colour, _res, _snr, _halo, _sourced]
