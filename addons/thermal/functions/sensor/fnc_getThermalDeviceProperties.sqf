#include "..\..\script_component.hpp"
/*
Thermal device properties (issue #215).

Classifies the thermal device (the player's thermal sight, binocular or
clip-on) by its classname family keywords and returns the researched
sensor physics from sensor-device-library.md:

  [netdDegC, resolutionX, resolutionY, weightKg, refreshHz, cooled]

Groups (sortable by country -> company -> detector):
  USA military 1990s+  | PAS-13E(V)1/2/3 (uncooled VOx 320/640) ->
    PAS-29 COTI (clip-on) -> PSQ-42 ENVG-B (fused)
  USA commercial       | FLIR (Recon, Scout, COTI), L3/Safran
  Europe               | Thales Sophie (uncooled), Thales Sophie
    Ultima + Catherine-MP (cooled MCT 1280), Safran JIM LR (InSb)
  Russia 2000s+        | 1PN97 Mowgli (uncooled), 1PN139/140 Shakhin
    (uncooled), Pulsar Helion/Thermion (commercial uncooled)
  China                | IRay, Guide (uncooled)

Detector physics (the NETD the thermal contrast consumes):
  uncooled microbolometer (LWIR 8-14 um) NETD 40-60 mK
  cooled InSb (MWIR 3-5 um) NETD 20-30 mK
  cooled MCT NETD <25 mK
  resolution 160x120 to 1280x1024; refresh 30 Hz US, 50 Hz EU/RU

Arguments:
  0: unit (OBJECT, default player)
  1: weapon (OBJECT, the mounted weapon, default the primary)

Returns [netdDegC, resX, resY, weightKg, refreshHz, cooled]
  netdDegC  - the noise-equivalent temperature difference in C
  resX/resY - the detector resolution in pixels
  weightKg  - the device weight
  refreshHz - the frame rate
  cooled    - 1 cooled (InSb/MCT), 0 uncooled (microbolometer)
*/
params [["_unit", player, [objNull]], ["_weapon", objNull, [objNull]]];
if (isNull _unit) exitWith { [0.05, 640, 480, 1.5, 30, 0] };

// The thermal device: the weapon's optics slot (mounted thermal sight)
// or the unit's NVG (fused/goggle thermal).
private _optic = "";
if (!isNull _weapon) then { _optic = primaryWeaponItems _weapon param [2, ""]; };
if (_optic == "") then { _optic = hmd _unit; };
if (_optic == "") exitWith { [0.05, 640, 480, 1.5, 30, 0] };

private _t = toLower _optic;
switch (true) do {
    // ── Cooled high-res (InSb/MCT): the sniper/observation class ──
    // Catherine-MP (1280x1024 MCT), JIM LR (InSb 384), Sophie Ultima.
    case (_t find "catherine" >= 0 ||
          _t find "jim" >= 0 ||
          _t find "ultima" >= 0 ||
          _t find "recon" >= 0):            { [0.025, 640, 512, 2.5, 50, 1] };
    // ── US PAS-13E(V)2/3 (640x480 uncooled VOx) ──
    case (_t find "pas-13" >= 0 ||
          _t find "pas13" >= 0 ||
          _t find "v2" >= 0 ||
          _t find "v3" >= 0):               { [0.05, 640, 480, 1.3, 30, 0] };
    // ── US PAS-13E(V)1 (320x240 uncooled, the light weapon sight) ──
    case (_t find "v1" >= 0):               { [0.05, 320, 240, 0.885, 30, 0] };
    // ── Clip-ons (COTI, PAS-29): overlay the day scope ──
    case (_t find "coti" >= 0 ||
          _t find "pas-29" >= 0 ||
          _t find "clipon" >= 0):           { [0.05, 320, 240, 0.15, 30, 0] };
    // ── ENVG-B fusion (Gen 3 + uncooled 640x480) ──
    case (_t find "envg" >= 0 ||
          _t find "psq-42" >= 0):           { [0.04, 640, 480, 1.133, 30, 0] };
    // ── Thales Sophie (uncooled 384/640) ──
    case (_t find "sophie" >= 0):           { [0.05, 384, 288, 2.0, 50, 0] };
    // ── Russian 1PN139/140 Shakhin + 1PN97 Mowgli (uncooled) ──
    case (_t find "shakhin" >= 0 ||
          _t find "1pn139" >= 0 ||
          _t find "1pn140" >= 0 ||
          _t find "1pn97" >= 0 ||
          _t find "mowgli" >= 0):           { [0.05, 320, 240, 1.5, 30, 0] };
    // ── Pulsar commercial (Helion/Thermion, uncooled, high NETD) ──
    case (_t find "pulsar" >= 0 ||
          _t find "thermion" >= 0 ||
          _t find "helion" >= 0):           { [0.05, 640, 480, 0.9, 50, 0] };
    // ── FLIR Scout (uncooled handheld) ──
    case (_t find "scout" >= 0 ||
          _t find "flir" >= 0):             { [0.05, 640, 512, 0.34, 30, 0] };
    default                                  { [0.05, 640, 480, 1.5, 30, 0] };
};
