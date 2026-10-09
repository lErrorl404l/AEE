// XEH_PREP.hpp — function prep includes for aee_core
//
// Registered via CBA's PREP system.  Each entry corresponds to a
// functions/fnc_<name>.sqf file that is compiled at mission start.

PREP(createPPEffect);
PREP(destroyPPEffect);
PREP(calculateSeededWeatherProgression);
PREP(deterministicRandom);
PREP(diagnostic);
PREP(dumpPerformanceCounters);
PREP(getWorldLocation);
PREPS(geo,buildGeoAnchor);
PREPS(geo,getGeoAnchor);
PREPS(geo,latLonToUtm);
PREPS(geo,utmToLatLon);
PREPS(geo,utmToWorld);
PREPS(geo,formatMgrs);
PREPS(geo,parseMgrs);
PREPS(geo,worldToMgrs);
PREPS(geo,mgrsToWorld);
PREPS(geo,gnssErrorEllipse);
PREPS(geo,gnssFixState);
PREPS(geo,datalinkState);
PREPS(geo,evaluateGeoConsistency);
PREPS(geo,runGeoConsistency);
PREP(init);
PREP(moduleInit);
PREP(moduleStormInit);
PREP(updateEnvironment);
PREP(updateSimClock);
PREP(getEyeState);
PREP(getSmoothedWeather);
PREP(handleCollisionDamage);
PREP(attachObjectEngineHandler);
PREP(installObjectEngineHandler);
PREP(installPlayerEngineHandler);
PREP(readState);
PREP(calculateIlluminance);
PREP(dumpState);
PREP(reportModuleHealth);
PREP(coreBodyTemp);
PREP(evaluateConsistency);
PREP(consistencyLoadTable);
PREP(consistencyFailureLine);
PREP(consistencyLog);
PREP(runConsistencyCheck);
