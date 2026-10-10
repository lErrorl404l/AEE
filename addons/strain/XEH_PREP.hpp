// XEH_PREP.hpp - function prep includes for aee_strain
//
// Heat/cold strain, dehydration, fatigue, shooter stability and the
// stamina-to-animation coupling.  Split out of aee_physiology (ADR-032).

PREPS(strain,applyCrossSensitivity);
PREPS(strain,applyMovementSpeed);
PREPS(strain,calculateColdWeatherPerformance);
PREPS(strain,calculateDehydrationRisk);
PREPS(strain,calculateFatigueFactor);
PREPS(strain,calculateShooterStability);
PREPS(strain,calculateSleepPressure);
PREPS(strain,calculateUVIndex);
PREPS(strain,getGLoad);
PREPS(strain,integrateSwayFactor);

// Combat-stress psychology kernels (issue #110).  The suppression-psychology
// model: stress and morale indices, the decision-quality multiplier table,
// effective spotting and the morale action gate.  Pure; the driver is in
// aee_physiology (state/updatePsychologyState).
PREPS(psychology,calculateStress);
PREPS(psychology,calculateMorale);
PREPS(psychology,getDecisionMultipliers);
PREPS(psychology,calculateEffectiveSpotting);
PREPS(psychology,getMoraleAction);
