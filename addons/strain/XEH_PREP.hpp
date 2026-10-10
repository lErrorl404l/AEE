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
