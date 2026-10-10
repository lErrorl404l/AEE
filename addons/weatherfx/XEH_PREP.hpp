// XEH_PREP.hpp - function prep includes for aee_weatherfx
//
// Split out of its source addon (ADR-032).  Every kernel is PREP'd from
// functions/; callers use FUNC.

PREPS(weather,applyAtmosphericDust);
PREPS(weather,applyBreathCondensation);
PREPS(weather,applyExhaustShimmer);
PREPS(weather,applyFootfallDust);
PREPS(weather,applyRotorWash);
PREPS(weather,applyRainSurfaceDrops);
PREPS(weather,applyRainVehicleSound);
PREPS(weather,applyVehicleDust);
PREPS(weather,applyWeatherParticles);
PREPS(weather,applyWindNoise);
PREPS(weather,calculateLightningStrikeEffects);
PREPS(weather,triggerLightning);
PREPS(weather,triggerSevereWeatherFX);
