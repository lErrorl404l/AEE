// XEH_PREP.hpp - function prep includes for aee_lib (the lib infrastructure
// addon).  Compiles the shared framework functions and the shared kernels at
// preInit.

PREPS(settings,migrateLegacySettings);
PREP(createPPEffect);
PREP(destroyPPEffect);
PREP(deterministicRandom);
PREP(getWorldLocation);
PREP(attachObjectEngineHandler);
PREP(installObjectEngineHandler);
PREP(installPlayerEngineHandler);
PREP(readState);
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
