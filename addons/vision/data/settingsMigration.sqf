/* SPDX-License-Identifier: GPL-2.0-or-later */
// ADR-032 one-time settings migration pairs for aee_vision.
// The post-process, base-grade, human-vision and shadow settings moved here
// from aee_optics and took the aee_vision_* names. fnc_migrateLegacySettings
// copies each set old value to the new name. The leaf is preserved verbatim,
// so only the module token changes.
[
    ["aee_optics_weatherGrainIntensity", "aee_vision_weatherGrainIntensity"],
    ["aee_optics_weatherGrainRainThreshold", "aee_vision_weatherGrainRainThreshold"],
    ["aee_optics_shadowAdaptiveEnabled", "aee_vision_shadowAdaptiveEnabled"],
    ["aee_optics_shadowMinDistance", "aee_vision_shadowMinDistance"],
    ["aee_optics_shadowMaxDistance", "aee_vision_shadowMaxDistance"],
    ["aee_optics_shadowSampleCount", "aee_vision_shadowSampleCount"],
    ["aee_optics_shadowUpdateInterval", "aee_vision_shadowUpdateInterval"],
    ["aee_optics_shadowOpeningSensitivity", "aee_vision_shadowOpeningSensitivity"],
    ["aee_optics_shadowFarSceneInfluence", "aee_vision_shadowFarSceneInfluence"],
    ["aee_optics_shadowMovementProtection", "aee_vision_shadowMovementProtection"],
    ["aee_optics_shadowCameraTurnProtection", "aee_vision_shadowCameraTurnProtection"],
    ["aee_optics_shadowOpticsProtection", "aee_vision_shadowOpticsProtection"],
    ["aee_optics_shadowTargetFPS", "aee_vision_shadowTargetFPS"],
    ["aee_optics_viewDistanceEnabled", "aee_vision_viewDistanceEnabled"],
    ["aee_optics_baseGradeEnabled", "aee_vision_baseGradeEnabled"],
    ["aee_optics_baseGradeContrast", "aee_vision_baseGradeContrast"],
    ["aee_optics_baseGradeBrightness", "aee_vision_baseGradeBrightness"],
    ["aee_optics_baseGradeBlackPoint", "aee_vision_baseGradeBlackPoint"],
    ["aee_optics_baseGradeSaturation", "aee_vision_baseGradeSaturation"],
    ["aee_optics_baseGradeSharpness", "aee_vision_baseGradeSharpness"],
    ["aee_optics_baseGradeGrain", "aee_vision_baseGradeGrain"],
    ["aee_optics_baseGradeAcuityEnabled", "aee_vision_baseGradeAcuityEnabled"],
    ["aee_optics_visionModelEnabled", "aee_vision_visionModelEnabled"],
    ["aee_optics_visionToneEnabled", "aee_vision_visionToneEnabled"],
    ["aee_optics_visionToneStrength", "aee_vision_visionToneStrength"],
    ["aee_optics_visionContrastScale", "aee_vision_visionContrastScale"],
    ["aee_optics_visionWhiteBalance", "aee_vision_visionWhiteBalance"],
    ["aee_optics_visionAdaptationDegree", "aee_vision_visionAdaptationDegree"],
    ["aee_optics_visionMesopicDesaturation", "aee_vision_visionMesopicDesaturation"],
    ["aee_optics_visionPurkinjeStrength", "aee_vision_visionPurkinjeStrength"],
    ["aee_optics_perceptionMonitor", "aee_vision_perceptionMonitor"],
    ["aee_optics_perceptionHud", "aee_vision_perceptionHud"],
    ["aee_optics_perceptionInterval", "aee_vision_perceptionInterval"]
]
