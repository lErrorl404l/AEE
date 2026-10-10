/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_eye.
// The eye-adaptation settings moved here from aee_optics and took the
// aee_eye_* names. fnc_migrateLegacySettings copies each set old value to the
// new name. The leaf is preserved verbatim, so only the module token changes.
[
    ["aee_optics_eyeAdaptationEnabled", "aee_eye_eyeAdaptationEnabled"],
    ["aee_optics_eyeReflectance", "aee_eye_eyeReflectance"],
    ["aee_optics_eyeTauLight", "aee_eye_eyeTauLight"],
    ["aee_optics_eyeTauDarkCone", "aee_eye_eyeTauDarkCone"],
    ["aee_optics_eyeTauDarkRod", "aee_eye_eyeTauDarkRod"],
    ["aee_optics_eyePupilTauConstrict", "aee_eye_eyePupilTauConstrict"],
    ["aee_optics_eyePupilTauDilate", "aee_eye_eyePupilTauDilate"],
    ["aee_optics_eyeMesopicLow", "aee_eye_eyeMesopicLow"],
    ["aee_optics_eyeMesopicHigh", "aee_eye_eyeMesopicHigh"],
    ["aee_optics_eyeFastBlend", "aee_eye_eyeFastBlend"],
    ["aee_optics_eyeAmbientLuxScale", "aee_eye_eyeAmbientLuxScale"],
    ["aee_optics_eyeLocalLuxScale", "aee_eye_eyeLocalLuxScale"],
    ["aee_optics_eyeBlindingLuxScale", "aee_eye_eyeBlindingLuxScale"]
]
