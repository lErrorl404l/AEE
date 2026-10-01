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
  resolution 160x120 to 1280x1024; refresh 30 Hz US, 50 Hz Pulsar/cooled

NETD VALUE SELECTION.  The library writes "~" for a nominal figure and "<"
for a datasheet limit (the upper bound the unit must meet).  For a DETECTION
THRESHOLD the correct input is the LIMIT, because the threshold is a
worst-case detection floor and a nominal figure would claim sensitivity the
qualified unit may not have (a datasheet NETD is a test-condition figure;
FLIR normalises it to 300 K and f/1.0).  The "<" devices therefore use the
bound: Catherine, JIM LR, Recon V and Thermion use 0.025 from "<25"; Helion
uses 0.04 from "<40"; the PAS-13 family uses 0.05 from "<50".  The "~"
devices use the nominal figure as printed.  Manufacturer datasheets were
opened for the resolution and, where noted, the weight; NETD was not on
every sheet, so those stay as the library prints them.

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

// PAS-13 variant tokens are two characters ("v1"), so a bare find matches
// any classname that happens to contain them.  Gate every variant on the
// family token so only a real PAS-13 can select a variant tuple.
private _isPas = (_t find "pas-13" >= 0) || (_t find "pas13" >= 0);

// Every tuple is reconciled against sensor-device-library.md L111-127.
// NETD: "~" values are typical, "<" values are the datasheet limit, used
// here as a conservative stand-in because the doc publishes no typical
// figure for those devices (see the header note).
switch (true) do {
    // ── Cooled high-res (InSb/MCT): the observation class ──
    // Catherine-MP LW: cooled MCT 1280x1024, <25 mK, 7.9 kg (doc L123).
    case (_t find "catherine" >= 0):          { [0.025, 1280, 1024, 7.9, 50, 1] };
    // Sophie Ultima: cooled MWIR 640x512, ~25 mK, <2.5 kg (doc L122).
    case (_t find "ultima" >= 0):             { [0.025, 640, 512, 2.5, 50, 1] };
    // FLIR Recon V: cooled MWIR 640x480 InSb (doc L118).  The weight is
    // 1.9 kg from the opened FLIR datasheet (SV_0018, 4.25 lb with
    // batteries); the doc's ~1.6 kg is the bare / Ultra-Lite figure.
    case (_t find "recon" >= 0):              { [0.025, 640, 480, 1.9, 50, 1] };
    // Safran JIM LR: cooled InSb 384x288, ~25 mK, <2.8 kg (doc L120).
    case (_t find "jim" >= 0):                { [0.025, 384, 288, 2.8, 50, 1] };
    // ── PAS-13E(V) family (uncooled VOx, US 30 Hz, doc L113-115) ──
    case (_isPas && (_t find "v1" >= 0)):     { [0.05, 320, 240, 0.885, 30, 0] };
    case (_isPas && (_t find "v2" >= 0)):     { [0.05, 640, 480, 1.134, 30, 0] };
    case (_isPas && (_t find "v3" >= 0)):     { [0.05, 640, 480, 1.497, 30, 0] };
    // A PAS-13 with no variant token: the 640x480 MWTS class.
    case (_isPas):                            { [0.05, 640, 480, 1.134, 30, 0] };
    // ── Clip-ons (COTI, PAS-29): overlay the day scope (doc L116) ──
    case (_t find "coti" >= 0 ||
          _t find "pas-29" >= 0 ||
          _t find "clipon" >= 0):             { [0.05, 320, 240, 0.15, 30, 0] };
    // ── ENVG-B fusion (Gen 3 + uncooled 640x480, ~40 mK, doc L117) ──
    case (_t find "envg" >= 0 ||
          _t find "psq-42" >= 0):             { [0.04, 640, 480, 1.133, 30, 0] };
    // ── Thales Sophie (uncooled 384x288, ~50 mK, doc L121) ──
    case (_t find "sophie" >= 0):             { [0.05, 384, 288, 2.0, 50, 0] };
    // ── 1PN139/140 Shakhin (uncooled, doc L125): the doc gives the family
    //    as a variant range 160x120-640x480 and 1.3-2.2 kg; the family's
    //    maximum stated resolution and weight are the representative.
    case (_t find "shakhin" >= 0 ||
          _t find "1pn139" >= 0 ||
          _t find "1pn140" >= 0):             { [0.05, 640, 480, 2.2, 50, 0] };
    // ── 1PN97 Mowgli-2M (uncooled 320x240, ~50 mK, ~1.5 kg, doc L124) ──
    case (_t find "1pn97" >= 0 ||
          _t find "mowgli" >= 0):             { [0.05, 320, 240, 1.5, 50, 0] };
    // ── Pulsar Thermion XP50 (uncooled 17um, <25 mK, 0.9 kg, doc L126) ──
    case (_t find "thermion" >= 0):           { [0.025, 640, 480, 0.9, 50, 0] };
    // ── Pulsar Helion (uncooled 384x288, <40 mK, ~0.5 kg, doc L127) ──
    case (_t find "helion" >= 0):             { [0.04, 384, 288, 0.5, 50, 0] };
    // ── FLIR Scout III 640 (uncooled VOx 640x512, ~50 mK, 0.34 kg, L119) ──
    case (_t find "scout" >= 0):              { [0.05, 640, 512, 0.34, 30, 0] };
    // ── Unmatched: the documented uncooled microbolometer class (doc L106
    //    40-60 mK) at the common 640x480 LWIR array.  The weight has no
    //    source and is UNVERIFIED.
    default                                   { [0.05, 640, 480, 1.5, 30, 0] };
};
