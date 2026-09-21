#include "..\script_component.hpp"
/*
NVG device properties (issue #215).

Classifies the NVG device (the player's worn goggles) by its classname
family keywords and returns the researched tube physics from
sensor-device-library.md:

  [generation, sensitivity uA/lm, resolution lp/mm, weight kg,
   tubeCount, fovDeg]

Groups (sortable by country -> company -> generation):
  USA military 1970s+  | PVS-5 (Gen 2) -> PVS-7 (Gen 2/3) -> PVS-14
    (Gen 3, the monocular standard) -> PVS-15/31 (Gen 3+) -> GPNVG-18
    (quad, filmless)
  USA commercial       | L3Harris (F6015/6030/6050 tubes), Elbit
    (MX-10160/MX-11769), Photonis 4G (filmless)
  UK / Europe          | Pilos, LUCIE (Gen 2+), Mikron
  Russia 1960s+        | 1PN58 (Gen 1) -> 1PN63 (Gen 1) -> 1PN93
    (Gen 2+) -> 1PN138 (Gen 2+ monocular, Ratnik) -> 1PN97
  China                | NVT-7/14 (Gen 2+)

Generation physics (the tube ladder fnc_applyNVGTubeModel consumes):
  Gen 0  S-1 photocathode, <200 gain, IR-active
  Gen 1  S-20, <800 gain
  Gen 2  S-25 multialkali, ~550 uA/lm, MCP ~20-30k gain
  Gen 3  GaAs, ~1100 uA/lm, ~30-50k gain
  Gen 3+ filmless GaAs, ~2000 uA/lm (L3Harris/Photonis 4G), SNR 33

Arguments:
  0: unit (OBJECT, default player)

Returns [generation, sensitivity, resolution, weightKg, tubeCount, fovDeg]
  generation  - the tube generation string (GEN1/GEN2/GEN3/PVS31)
  sensitivity - photocathode luminous sensitivity uA/lm
  resolution  - tube resolution lp/mm
  weightKg    - the device weight
  tubeCount   - monocular 1 / binocular 2 / panoramic quad 4
  fovDeg      - the objective field of view
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { ["GEN3", 1100, 64, 0.355, 1, 40] };

// The player's worn NVG: ACE3's NVD-Goggles classnames + vanilla.
// The engine hmd command returns the head-mounted device class.
private _hmd = hmd _unit;
if (_hmd == "") exitWith { ["GEN3", 1100, 64, 0.355, 1, 40] };

private _h = toLower _hmd;
switch (true) do {
    // ── Panoramic quad (GPNVG-18, 4x tubes, 97H FOV) ──
    case (_h find "gpnvg" >= 0 ||
          _h find "pano" >= 0 ||
          _h find "nv_wide" >= 0):          { ["PVS31", 2000, 72, 0.79, 4, 97] };
    // ── Binocular modern filmless (PVS-31A/B, ENVG, ANVIS, quad-capable) ──
    case (_h find "pvs31" >= 0 ||
          _h find "pvs_31" >= 0 ||
          _h find "envg" >= 0 ||
          _h find "anvis" >= 0 ||
          _h find "nvgogglesb" >= 0 ||
          _h find "nvg_w" >= 0):            { ["PVS31", 2000, 72, 0.45, 2, 40] };
    // ── PVS-15 (Gen 3+ binocular) ──
    case (_h find "pvs15" >= 0 ||
          _h find "pvs_15" >= 0):           { ["GEN3", 1500, 64, 0.726, 2, 40] };
    // ── PVS-14 (Gen 3 monocular, the standard) ──
    case (_h find "pvs14" >= 0 ||
          _h find "pvs_14" >= 0 ||
          _h find "pvs-14" >= 0):           { ["GEN3", 1100, 64, 0.355, 1, 40] };
    // ── PVS-7 (Gen 2/3 monocular, the older standard) ──
    case (_h find "pvs7" >= 0 ||
          _h find "pvs_7" >= 0):            { ["GEN2", 550, 28, 0.68, 1, 40] };
    // ── PVS-5 (Gen 2 binocular, the 1970s standard) ──
    case (_h find "pvs5" >= 0 ||
          _h find "pvs_5" >= 0):            { ["GEN2", 550, 28, 0.85, 2, 40] };
    // ── Russian 1PN138 (Gen 2+ monocular, Ratnik) ──
    case (_h find "1pn138" >= 0 ||
          _h find "1pn97" >= 0):            { ["GEN2", 550, 45, 0.35, 1, 40] };
    // ── Russian 1PN93 (Gen 2+ weaponsight / monocular) ──
    case (_h find "1pn93" >= 0):            { ["GEN2", 550, 45, 1.2, 1, 6] };
    // ── Russian 1PN63/1PN58 (Gen 1) ──
    case (_h find "1pn63" >= 0 ||
          _h find "1pn58" >= 0):            { ["GEN1", 250, 30, 1.5, 1, 40] };
    // ── Vanilla Gen 3 (NVGoggles/INDEP = Gen 3, the engine's tier) ──
    case (_h find "nvgen3" >= 0 ||
          _h find "nvgoggles_indep" >= 0 ||
          _h find "nvgoggles" >= 0):        { ["GEN3", 1100, 64, 0.355, 1, 40] };
    // ── Vanilla Gen 2 (OPFOR) ──
    case (_h find "nvgen2" >= 0 ||
          _h find "nvgoggles_opfor" >= 0):  { ["GEN2", 550, 28, 0.68, 1, 40] };
    // ── Vanilla Gen 1 (the oldest) ──
    case (_h find "gen1" >= 0):             { ["GEN1", 250, 30, 1.0, 1, 40] };
    default                                  { ["GEN3", 1100, 64, 0.355, 1, 40] };
};
