// XEH_PREP.hpp - function prep includes for aee_flight
//
// Helicopter lift, airframe load, atmospheric turbulence, the flight model
// and the aircraft systems kernels (fuel, engine, damage, status).  The
// flight kernels are split out of aee_mobility (ADR-032); the systems kernels
// are the aircraft consumer of the shared vehicle systems contract
// (ADR-033).  Every kernel is PREP'd from functions/; callers use FUNC.

PREP(applyFlightTurbulence);
PREP(applyAirframeLoad);
PREP(logAirframeState);
PREP(resolveFlightModel);
PREP(calculateTurbulenceForce);
PREP(resolveTurbulenceArea);
PREP(calculateAeroPenalty);
PREP(calculateDensityAltitude);
PREP(calculatePowerRatio);
PREP(calculateGroundEffect);
PREP(calculateFixedWingPerformance);
PREP(updateFixedWingPerformance);
PREP(logFixedWingState);
PREP(calculateAirEngineLoad);
PREP(calculateHelicopterLift);
PREP(getAircraftData);
PREP(getAircraftMatch);
PREP(getAircraftSystems);
PREP(calculateFuelBurn);
PREP(calculateEngineNg);
PREP(calculateScriptedTgtOil);
PREP(updateFuelSystem);
PREP(updateEngineSystem);
PREP(updateDamageSystem);
PREP(updateStatusSystems);
PREP(updateAircraftSystems);
