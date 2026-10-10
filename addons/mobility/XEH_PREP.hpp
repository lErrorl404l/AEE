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

// Frost heave (issue #20): the soil-dependent heave magnitude, the road-vs-
// field differential, and the terrain grid for the engine setTerrainHeight
// command.
PREPS(heave,calculateFrostHeave);
PREPS(heave,differentialHeave);
PREPS(heave,heaveTerrainPoints);
