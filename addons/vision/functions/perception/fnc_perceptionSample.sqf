#include "..\..\script_component.hpp"

/*
Perception sample kernel (human-vision model, pure aggregate).

Pure: the kernel reads no world state, no module global, and runs no engine
command.  The perception driver calls this every tick.  The kernel lays the
reconstructed view state out in one fixed-length array, so the driver, the
deviation kernel and the tests read the same order.

The kernel reads NOTHING from the world.  The caller supplies a value map keyed
by the schema names below.  A HashMap is deliberately not accepted: reading one
needs the `get` engine command, which the pure boundary forbids.  The value map
is a flat array of [key, value] pairs, in any order and with any subset of keys.

PERCEPTION_SCHEMA - the fixed field order the kernel returns (14 fields):

  index  key                  type    shape and meaning
  0      sceneLux             Number  scene illuminance, cd/m2 equivalent
  1      adaptedLux           Number  adapted scene luminance, cd/m2
  2      eyeAperture          Number  applied camera aperture (fnc_eyeAperture)
  3      pupilMm              Number  pupil diameter, mm
  4      mesopicWeight        Number  CIE 191:2010 photopic fraction, 0 to 1
  5      appliedGrade         Array   [brightness, contrast, offset, alpha]
  6      cameraTint           Array   colour multiply [r, g, b, alpha]
  7      nvgState             Array   [active, gain, tier, perceived, gate]
  8      thermalState         Array   [active, mode, band, selTemperatureC,
                                      bandRadiance]
  9      uvIndex              Number  UV index
  10     stressState          Array   [wbgtC, windChillC, hypothermiaRisk,
                                      dehydrationRisk]
  11     injuryState          Array   [pain, damage]
  12     activeEffects        Array   list of active visual-effect names
  13     eyeAdaptationState   Array   [level, target, direction, timeToAdapt]

Immutable defaults.  A key missing from the value map returns the default for
its field, in PERCEPTION_SCHEMA order.  Each default is graded:

  sceneLux            1            UNSOURCED.  A neutral 1 cd/m2 marker so a
                                   missing key never fakes daylight or dark.
  adaptedLux          1            UNSOURCED.  Neutral marker, as sceneLux.
  eyeAperture         8            SOURCED: fnc_eyeAperture night anchor (BI
                                   wiki setApertureNew example [2, 8, 14]).
                                   Chosen wide open, the more-lit fallback.
  pupilMm             4.9          SOURCED: the de Groot and Gebhard 1952 mid
                                   constant used by fnc_eyePupilSteady.
  mesopicWeight       1            SOURCED: CIE 191:2010 photopic endpoint;
                                   fraction 1 is fully photopic.
  appliedGrade        [1, 1, 0, 0] SOURCED: the engine neutral grade
                                   brightness 1, contrast 1, offset 0
                                   (CfgPostProcessTemplates >> Default) with a
                                   zero desaturation alpha.
  cameraTint          [1,1,1,1]    SOURCED: the engine neutral colorize
                                   {1,1,1,1} (same config template).
  nvgState            [false,0,0,0,false]  UNSOURCED.  The off state.
  thermalState        [false,0,0,0,0]      UNSOURCED.  The off state.
  uvIndex             0            UNSOURCED.  The night floor.
  stressState         [0,0,0,0]    UNSOURCED.  No heat and cold stress.
  injuryState         [0,0]        UNSOURCED.  No pain, no damage.
  activeEffects       []           UNSOURCED.  No effect active.
  eyeAdaptationState  [0,0,0,0]    UNSOURCED.  Level and target 0 (log10 of
                                   1 cd/m2), no direction, no remaining time.

Arguments:
  0: Array - value map, an array of [key, value] pairs

Returns:
  Array - 14 values in PERCEPTION_SCHEMA order.  A malformed pair is skipped.
*/

params [
    ["_map", [], [[]]]
];

// PERCEPTION_SCHEMA: the field names in return order.
private _schema = [
    "sceneLux",
    "adaptedLux",
    "eyeAperture",
    "pupilMm",
    "mesopicWeight",
    "appliedGrade",
    "cameraTint",
    "nvgState",
    "thermalState",
    "uvIndex",
    "stressState",
    "injuryState",
    "activeEffects",
    "eyeAdaptationState"
];

// The immutable fallbacks, in PERCEPTION_SCHEMA order.  Graded in the header.
private _defaults = [
    1,
    1,
    8,
    4.9,
    1,
    [1, 1, 0, 0],
    [1, 1, 1, 1],
    [false, 0, 0, 0, false],
    [false, 0, 0, 0, 0],
    0,
    [0, 0, 0, 0],
    [0, 0],
    [],
    [0, 0, 0, 0]
];

// forEach, not apply: only forEach provides _forEachIndex in the engine.
// apply sets _x alone, so an _forEachIndex read there is undefined at run
// time even though the pure kernel harness accepts it.
private _result = [];
{
    private _key = _x;
    private _index = _forEachIndex;
    // First pair whose key matches.  -1 when the key is absent.
    private _found = _map findIf {
        private _pair = _x;
        if (_pair isEqualType []) then {
            if ((count _pair) >= 2) then {
                ((_pair select 0) isEqualType "") && {(_pair select 0) == _key}
            } else {
                false
            }
        } else {
            false
        }
    };
    _result pushBack (if (_found >= 0) then {
        (_map select _found) select 1
    } else {
        _defaults select _index
    });
} forEach _schema;
_result
