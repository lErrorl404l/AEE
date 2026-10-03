#include "..\..\script_component.hpp"
/*
 * Outline skeleton and capsule descriptors by level of detail
 * (issue #204, fusion outline).
 *
 * Copied from the _lod table in workshop 3811605241 whale_ecoti_llll
 * functions/fn_drawOutlines.sqf.  The source carries four levels of detail,
 * selected from the target's height on the thermal sensor (see
 * fnc_outlineSensorLod).  Each level is
 *
 *   [boneList, capList, probes, pmap, minPts, spIdx]
 *
 *   boneList - the model's own selection memory points, read by
 *              fnc_outlineDraw with selectionPosition and modelToWorldVisual.
 *   capList  - capsules [os A, os B, rayon A, extension, rayon B, role],
 *              role 0 normal | 1 head | 2 torso | 3 backpack.
 *   probes   - capsules used as the occlusion test points.
 *   pmap     - for each capsule, the index into probes of its body zone.
 *   minPts   - the minimum usable bone count for the level.
 *   spIdx    - the two bone indices used as the virtual backpack points.
 *
 * Pure: a literal table, no engine state, so the harness runs it.
 *
 * Returns: ARRAY indexed by LOD 0..3.
 */
[
    // 0 = near: 16 bones (+2 virtual), 13 members, 6 zones.
    [
        ["head", "neck", "spine3", "pelvis",
         "leftarm", "leftforearm", "lefthand",
         "rightarm", "rightforearm", "righthand",
         "leftupleg", "leftleg", "leftfoot",
         "rightupleg", "rightleg", "rightfoot"],
        [[3, 2, 0.16, 0, 0.19, 2], [2, 1, 0.17, 0, 0.08, 2], [0, 1, 0.105, 0.11, 0.095, 1], [4, 7, 0.068, 0, 0.068, 0],
         [4, 5, 0.075, 0, 0.055, 0], [5, 6, 0.055, 0, 0.042, 0],
         [7, 8, 0.075, 0, 0.055, 0], [8, 9, 0.055, 0, 0.042, 0],
         [10, 11, 0.115, 0, 0.07, 0], [11, 12, 0.07, 0, 0.05, 0],
         [13, 14, 0.115, 0, 0.07, 0], [14, 15, 0.07, 0, 0.05, 0],
         [16, 17, 0.15, 0, 0.13, 3]],
        [0, 2, 5, 7, 9, 11],
        [0, 0, 1, 0, 2, 2, 3, 3, 4, 4, 5, 5, 0],
        6,
        [2, 3]
    ],
    // 1 = medium: same 16 bones, 13 members, 6 zones.
    [
        ["head", "neck", "spine3", "pelvis",
         "leftarm", "leftforearm", "lefthand",
         "rightarm", "rightforearm", "righthand",
         "leftupleg", "leftleg", "leftfoot",
         "rightupleg", "rightleg", "rightfoot"],
        [[3, 2, 0.16, 0, 0.19, 2], [2, 1, 0.17, 0, 0.08, 2], [0, 1, 0.105, 0.11, 0.095, 1], [4, 7, 0.068, 0, 0.068, 0],
         [4, 5, 0.075, 0, 0.055, 0], [5, 6, 0.055, 0, 0.042, 0],
         [7, 8, 0.075, 0, 0.055, 0], [8, 9, 0.055, 0, 0.042, 0],
         [10, 11, 0.115, 0, 0.07, 0], [11, 12, 0.07, 0, 0.05, 0],
         [13, 14, 0.115, 0, 0.07, 0], [14, 15, 0.07, 0, 0.05, 0],
         [16, 17, 0.15, 0, 0.13, 3]],
        [0, 2, 5, 7, 9, 11],
        [0, 0, 1, 0, 2, 2, 3, 3, 4, 4, 5, 5, 0],
        6,
        [2, 3]
    ],
    // 2 = far: 7 bones (+2 virtual), 8 members, 4 zones.
    [
        ["head", "spine3", "pelvis", "lefthand", "righthand", "leftfoot", "rightfoot"],
        [[2, 1, 0.17, 0, 0.20, 2], [1, 0, 0.13, 0, 0.09, 2], [0, 1, 0.105, 0.09, 0.095, 1],
         [1, 3, 0.08, 0, 0.05, 0], [1, 4, 0.08, 0, 0.05, 0],
         [2, 5, 0.12, 0, 0.06, 0], [2, 6, 0.12, 0, 0.06, 0],
         [7, 8, 0.15, 0, 0.13, 3]],
        [0, 2, 5, 6],
        [0, 1, 1, 0, 0, 2, 3, 0],
        3,
        [1, 2]
    ],
    // 3 = blob: a target of a few sensor pixels -> a simple shape.
    [
        ["head", "pelvis", "leftfoot", "rightfoot"],
        [[1, 0, 0.24, 0, 0.24, 2], [1, 2, 0.20, 0, 0.20, 0], [1, 3, 0.20, 0, 0.20, 0]],
        [0],
        [0, 0, 0],
        2
    ]
]
