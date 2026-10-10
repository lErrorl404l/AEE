// XEH_PREP.hpp - function prep includes for aee_physiology
//
// The shared physiology state (fatigue/sleep, the ZH-L16C solver) and the
// heat-stress HUD warning.  The strain, altitude, dive and clothing kernels
// split out to their own addons (ADR-032).

PREPS(state,updateFatigueState);
PREPS(state,updatePsychologyState);
PREPS(state,zh16cStep);
PREPS(state,coldStress);
PREPS(state,heatStress);
PREPS(state,survivalPressure);
PREPS(state,survivalState);
PREPS(hud,applyHeatStressHUD);
PREP(dumpState);
