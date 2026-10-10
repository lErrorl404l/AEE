#include "..\..\script_component.hpp"
/*
 * Fusion thermal-channel field (issue #204, Track B ENVG-B).
 *
 * Maps the resolved thermal-channel device to its half-angle and the
 * provenance of that figure.  The device label comes from
 * fnc_resolveFusionDevice, which identifies the headset from the corpus
 * thermal row and from the hmd classname tokens.  This kernel is the
 * labelled table, and it is pure so the P80 probe and the unit suite can
 * execute it directly.
 *
 * ENVG-B: L3Harris publishes ONE fused 40 degree field covering both
 * channels, so there is no thermal-only figure to take.  The fused 40 is
 * NOT split here and no sibling's thermal figure is borrowed for it.  The
 * channel takes the declared default half-angle 20 and the label declared.
 *
 * BNVD-FUSED: TNVC (distributor grade) publishes a 34 degree DIAGONAL
 * thermal field, so the half-angle is the derived 17 and the axis is
 * diagonal.
 *
 * ECOTI: the Safran Optics 1 E-COTI Data Sheet publishes a 30 degree
 * CIRCULAR thermal field, so the half-angle is the published 15 and the
 * axis is circular.  The label is published, not declared.
 *
 * Params:
 *   0: _deviceLabel (STRING) - ECOTI, BNVD-FUSED, ENVG-B or unknown.
 *
 * Returns: [halfAngleDeg, sourceLabel, axisLabel].
 */
params [["_deviceLabel", "unknown", [""]]];

if (_deviceLabel == "ECOTI") exitWith { [15, "published", "circular"] };
if (_deviceLabel == "BNVD-FUSED") exitWith { [17, "derived", "diagonal"] };

// ENVG-B and every unrecognised headset: the declared default.
[20, "declared", "declared"]
