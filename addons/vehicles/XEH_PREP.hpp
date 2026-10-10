// XEH_PREP.hpp - function prep includes for aee_vehicles
//
// Vehicle identity, mass, geometry and engine data.  Split out of
// aee_mobility (ADR-032).  Every kernel is PREP'd from functions/; callers
// use FUNC.

PREP(calculateCoolantDerate);
PREP(calculateCoolantTemperature);
PREP(calculateEngineLoad);
PREP(calculateEnginePower);
PREP(calculateExhaustPlume);
PREP(calculateFuelRate);
PREP(calculateRoadLoad);
PREP(classifyVehicle);
PREP(getFuelData);
PREP(getVehicleBands);
PREP(getVehicleData);
PREP(getVehicleGeometry);
PREP(getVehicleMatch);
PREP(getVehicleMassModel);
PREP(estimateVehicleMass);
PREP(estimateVehicleMassCore);
PREP(updateFuelConsumption);
PREPS(common,getNearbyVehicles);
