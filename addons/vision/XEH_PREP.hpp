// XEH_PREP.hpp - function prep includes for aee_vision
//
// The post-process arbiter, the base grade and acuity pass, the human-vision
// model (perception) and the scene-aware shadow distance.  Every kernel is
// PREP'd from functions/{vision,grade,perception}/; callers use FUNC.

PREPS(vision,managePostProcess);
PREPS(vision,teardownSensors);
PREPS(vision,runThermalPass);
PREPS(vision,enterThermalSensors);
PREPS(vision,exitThermalSensors);
PREPS(vision,updateThermalHost);
PREPS(vision,updateThermalHostSetting);
PREPS(vision,dtvHostTick);
PREPS(vision,dtvHostStart);
PREPS(vision,dtvHostStop);
PREPS(vision,calculateViewDistance);
// Scene-aware shadow distance (aee-workshop-copy item 6).
PREPS(vision,shadowSamplePattern);
PREPS(vision,shadowClassifyScene);
PREPS(vision,shadowTargetDistance);
PREPS(vision,shadowSmoothDistance);
PREPS(vision,shadowFpsGovernor);
PREPS(vision,shadowStabilizeDepth);
PREPS(vision,ppEffectCreate);
PREPS(vision,destroyBasePostProcess);
PREPS(vision,weatherGrainParams);
PREPS(vision,applyWeatherGrain);
PREPS(vision,initWeatherGrain);

// Grade (image realism): the normal-vision base grade and acuity pass.
PREPS(grade,baseGradeParams);
PREPS(grade,applyBaseGrade);
PREPS(grade,initBaseGrade);
PREPS(grade,teardownBaseGrade);

// Perception (human-vision model): the pure tone and composition kernels.
PREPS(perception,perceptionToneResponse);
PREPS(perception,perceptionIlluminant);
PREPS(perception,perceptionChromaticAdaptation);
PREPS(perception,perceptionMesopicColor);
PREPS(perception,perceptionBaseGrade);
PREPS(perception,perceptionParams);
PREPS(perception,perceptionSample);
PREPS(perception,perceptionAdaptState);
PREPS(perception,perceptionUpdate);
PREPS(perception,perceptionDetectDeviation);
