// XEH_PREP.hpp - function prep includes for aee_flight
//
// Helicopter lift, airframe load, atmospheric turbulence and the flight
// model.  Split out of aee_mobility (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREP(applyFlightTurbulence);
PREP(applyAirframeLoad);
PREP(logAirframeState);
PREP(resolveFlightModel);
PREP(calculateTurbulenceForce);
PREP(resolveTurbulenceArea);
PREP(calculateAeroPenalty);
PREP(calculateAirEngineLoad);
PREP(calculateHelicopterLift);
PREP(getAircraftData);
PREP(getAircraftMatch);
