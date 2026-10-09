// XEH_PREP.hpp - function prep includes for aee_mobility
//
// Ground traction, soil, mud, rollover and off-road terrain drag.  Flight,
// vehicle-data and hydrology kernels moved to aee_flight, aee_vehicles and
// aee_hydrology (ADR-032).  Every kernel is PREP'd from functions/; callers
// use FUNC.

PREP(applyAccretionMass);
PREP(applyGripLoss);
PREP(applyRollover);
PREP(applyTerrainDrag);
PREP(calculateAccretionMass);
PREP(calculateMudAccretion);
PREP(calculateRolloverThreshold);
PREP(calculateRouteDegradation);
PREP(calculateSoilBearingStrength);
PREP(calculateSoilStrength);
PREP(calculateSSF);
PREP(calculateTerrainLimits);
PREP(calculateTraction);
PREP(calculateWetTraction);
PREP(getTerrainSpeedFactor);
PREP(updateGroundState);
