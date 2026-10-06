#include "..\..\script_component.hpp"
/*
Thermal device properties (issue #215).

Resolves the thermal device (the player's thermal sight, binocular or
clip-on) and returns its researched sensor physics.

SOURCE OF TRUTH. The device corpus under data/device/ is the only home for a
device value. The generator tools/validation/gen_device_data.py writes the
thermal family rows into the generated matcher
addons/nightvision/functions/fnc_getDeviceMatch.sqf. This function reads the
corpus through that matcher with the "thermal" family filter. A corpus figure
is the authority and it carries its unit, source and grade in the corpus.

STATIC FALLBACK. The switch below is the named fallback. It runs only when
the corpus holds no row for the device, or when a matched row holds no figure
for one field. It is this device's own researched row from
sensor-device-library.md, never a sibling's. A corpus figure always wins.

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
bound in the corpus.  The "~" devices use the nominal figure as printed.
Manufacturer datasheets were opened for the resolution and, where noted, the
weight; NETD was not on every sheet, so those stay as the library prints them.

Arguments:
  0: unit (OBJECT, default player)
  1: weapon (OBJECT, the mounted weapon, default the primary)

Returns [netdDegC, resX, resY, weightKg, refreshHz, cooled, band]
  netdDegC  - the noise-equivalent temperature difference in C
  resX/resY - the detector resolution in pixels
  weightKg  - the device weight
  refreshHz - the frame rate
  cooled    - 1 cooled (InSb/MCT), 0 uncooled (microbolometer)
  band      - the detector band token: "lwir" (8-14 um) or "mwir" (3-5 um)
*/
params [["_unit", player, [objNull]], ["_weapon", objNull, [objNull]]];
if (isNull _unit) exitWith { [0.05, 640, 480, 1.5, 30, 0, "lwir"] };

// The thermal device: the weapon's optics slot (mounted thermal sight)
// or the unit's NVG (fused/goggle thermal).
private _optic = "";
if (!isNull _weapon) then { _optic = primaryWeaponItems _weapon param [2, ""]; };
if (_optic == "") then { _optic = hmd _unit; };
if (_optic == "") exitWith { [0.05, 640, 480, 1.5, 30, 0, "lwir"] };

private _t = toLower _optic;

// PAS-13 variant tokens are two characters ("v1"), so a bare find matches
// any classname that happens to contain them.  Gate every variant on the
// family token so only a real PAS-13 can select a variant tuple.
private _isPas = (_t find "pas-13" >= 0) || (_t find "pas13" >= 0);

// ─── Static fallback: sensor-device-library.md ────────────────────────────
// Return order [netd, resX, resY, weight, refresh, cooled].  Every tuple is
// reconciled against sensor-device-library.md L111-127.  NETD: "~" values
// are typical, "<" values are the datasheet limit, used here as a
// conservative stand-in because the doc publishes no typical figure for
// those devices (see the header note).  Used only when the corpus has no
// row for the device or no figure for one field.
private _fallback = switch (true) do {
    // ── Cooled high-res (InSb/MCT): the observation class ──
    // Catherine-MP LW: cooled MCT 1280x1024, <25 mK, 7.9 kg (doc L123).  The
    // detector is MCT and the user-selectable band is LWIR (the "LW" in the
    // name).  The band is per-device, not a function of the cooled flag.
    case (_t find "catherine" >= 0):          { [0.025, 1280, 1024, 7.9, 50, 1, "lwir"] };
    // Sophie Ultima: cooled MWIR 640x512, ~25 mK, <2.5 kg (doc L122).
    case (_t find "ultima" >= 0):             { [0.025, 640, 512, 2.5, 50, 1, "mwir"] };
    // FLIR Recon V: cooled MWIR 640x480 InSb (doc L118).  The weight is
    // 1.9 kg from the opened FLIR datasheet (SV_0018, 4.25 lb with
    // batteries); the doc's ~1.6 kg is the bare / Ultra-Lite figure.
    case (_t find "recon" >= 0):              { [0.025, 640, 480, 1.9, 50, 1, "mwir"] };
    // Safran JIM LR: cooled InSb 384x288, ~25 mK, <2.8 kg (doc L120).
    case (_t find "jim" >= 0):                { [0.025, 384, 288, 2.8, 50, 1, "mwir"] };
    // ── PAS-13E(V) family (uncooled VOx, US 30 Hz, doc L113-115) ──
    case (_isPas && (_t find "v1" >= 0)):     { [0.05, 320, 240, 0.885, 30, 0, "lwir"] };
    case (_isPas && (_t find "v2" >= 0)):     { [0.05, 640, 480, 1.134, 30, 0, "lwir"] };
    case (_isPas && (_t find "v3" >= 0)):     { [0.05, 640, 480, 1.497, 30, 0, "lwir"] };
    // A PAS-13 with no variant token: the 640x480 MWTS class.
    case (_isPas):                            { [0.05, 640, 480, 1.134, 30, 0, "lwir"] };
    // ── Clip-ons (COTI, PAS-29): overlay the day scope (doc L116) ──
    case (_t find "coti" >= 0 ||
          _t find "pas-29" >= 0 ||
          _t find "clipon" >= 0):             { [0.05, 320, 240, 0.15, 30, 0, "lwir"] };
    // ── ENVG-B fusion (Gen 3 + uncooled 640x480, ~40 mK, doc L117) ──
    case (_t find "envg" >= 0 ||
          _t find "psq-42" >= 0):             { [0.04, 640, 480, 1.133, 30, 0, "lwir"] };
    // ── Thales Sophie (uncooled 384x288, ~50 mK, doc L121) ──
    case (_t find "sophie" >= 0):             { [0.05, 384, 288, 2.0, 50, 0, "lwir"] };
    // ── 1PN139/140 Shakhin (uncooled, doc L125): the doc gives the family
    //    as a variant range 160x120-640x480 and 1.3-2.2 kg; the family's
    //    maximum stated resolution and weight are the representative.
    case (_t find "shakhin" >= 0 ||
          _t find "1pn139" >= 0 ||
          _t find "1pn140" >= 0):             { [0.05, 640, 480, 2.2, 50, 0, "lwir"] };
    // ── 1PN97 Mowgli-2M (uncooled 320x240, ~50 mK, ~1.5 kg, doc L124) ──
    case (_t find "1pn97" >= 0 ||
          _t find "mowgli" >= 0):             { [0.05, 320, 240, 1.5, 50, 0, "lwir"] };
    // ── Pulsar Thermion XP50 (uncooled 17um, <25 mK, 0.9 kg, doc L126) ──
    case (_t find "thermion" >= 0):           { [0.025, 640, 480, 0.9, 50, 0, "lwir"] };
    // ── Pulsar Helion (uncooled 384x288, <40 mK, ~0.5 kg, doc L127) ──
    case (_t find "helion" >= 0):             { [0.04, 384, 288, 0.5, 50, 0, "lwir"] };
    // ── FLIR Scout III 640 (uncooled VOx 640x512, ~50 mK, 0.34 kg, L119) ──
    case (_t find "scout" >= 0):              { [0.05, 640, 512, 0.34, 30, 0, "lwir"] };
    // ── Unmatched: the documented uncooled microbolometer class (doc L106
    //    40-60 mK) at the common 640x480 LWIR array.  The weight has no
    //    source and is UNVERIFIED.  The unmatched band is lwir: LWIR is the
    //    sane default and the honest one.
    default                                   { [0.05, 640, 480, 1.5, 30, 0, "lwir"] };
};

// ─── Corpus route: data/device/, family "thermal" ─────────────────────────
// The generated matcher filters its table by family before the identity
// ladder, so a class two families name (the ENVG-B) cannot tie here.  A
// unique match returns [device_id, family, confidence, matched_by, source,
// value_row]; no match returns [].
private _match = [_optic, "thermal"] call EFUNC(nightvision,getDeviceMatch);
if (_match isEqualTo []) exitWith { _fallback };

// Generated thermal value row, in corpus projection order:
//   [netd_c, resolution_x, resolution_y, refresh_hz, cooled, weight_kg, band]
private _row = _match select 5;

// Per field: a corpus figure wins.  A field the row leaves absent arrives
// as 0 (number) or "" (word) at grade absent, so fall back to this device's
// own static row.  A sibling's figure is never borrowed.
private _netd = _row select 0;
if (_netd <= 0) then { _netd = _fallback select 0; };
private _resX = _row select 1;
if (_resX <= 0) then { _resX = _fallback select 1; };
private _resY = _row select 2;
if (_resY <= 0) then { _resY = _fallback select 2; };
private _refresh = _row select 3;
if (_refresh <= 0) then { _refresh = _fallback select 4; };
private _weight = _row select 5;
if (_weight <= 0) then { _weight = _fallback select 3; };

// The corpus holds the word, the return contract holds 1 (cooled) or 0.
private _cooledToken = _row select 4;
private _cooled = _fallback select 5;
if (_cooledToken == "cooled") then { _cooled = 1; };
if (_cooledToken == "uncooled") then { _cooled = 0; };

// The band token is a word, so an absent "" leaves this device's static band.
private _bandToken = _row select 6;
private _band = _fallback select 6;
if (_bandToken == "lwir" || _bandToken == "mwir") then { _band = _bandToken; };

[_netd, _resX, _resY, _weight, _refresh, _cooled, _band]
