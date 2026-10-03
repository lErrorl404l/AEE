#include "..\..\script_component.hpp"
/*
 * Outline skeleton bone lists by level of detail (issue #204, fusion outline).
 *
 * Ported from the _lod boneList entries in workshop 3811605241
 * whale_ecoti_llll functions/fn_drawOutlines.sqf.  The source carries four
 * levels of detail; the bone names are the model's own selection memory
 * points, read with selectionPosition and modelToWorldVisual.  Pure: no
 * engine state, so the harness can execute it.
 *
 * Returns: ARRAY indexed by LOD 0..3, each an ARRAY of bone names.
 */
[
    ["head", "neck", "spine3", "pelvis",
     "leftarm", "leftforearm", "lefthand",
     "rightarm", "rightforearm", "righthand",
     "leftupleg", "leftleg", "leftfoot",
     "rightupleg", "rightleg", "rightfoot"],
    ["head", "neck", "spine3", "pelvis",
     "leftarm", "leftforearm", "lefthand",
     "rightarm", "rightforearm", "righthand",
     "leftupleg", "leftleg", "leftfoot",
     "rightupleg", "rightleg", "rightfoot"],
    ["head", "spine3", "pelvis", "lefthand", "righthand", "leftfoot", "rightfoot"],
    ["head", "pelvis", "leftfoot", "rightfoot"]
]
