// XEH_PREP.hpp - function prep includes for aee_optics
//
// The optical sensor kernels and their viewport effects.  Every kernel is
// PREP'd from functions/<category>/; callers use FUNC.

PREPS(fx,applyAtmosphericSeeingFX);
PREPS(fx,applyDewOnOpticsFX);
PREPS(fx,applyHeatShimmerFX);
PREPS(fx,applyMirageFX);
PREPS(fx,applyRainOnOpticsFX);
PREPS(fx,applySnowBlindnessFX);
PREPS(fx,applySolarGlareFX);
PREPS(sensor,calculateAtmosphericSeeing);
PREPS(sensor,calculateAttenuation);
PREPS(sensor,calculateDewOnOptics);
PREPS(sensor,calculateGreenFlash);
PREPS(sensor,calculateMirageIntensity);
PREPS(sensor,calculatePrecipitationVisibility);
PREPS(sensor,calculateRainOnOptics);
PREPS(sensor,calculateSmokePersistence);
PREPS(sensor,calculateSnowBlindness);
PREPS(sensor,calculateSolarGlare);
PREPS(sensor,calculateVehicleHeatShimmer);
PREPS(sensor,getOpticProperties);
PREP(dumpState);
