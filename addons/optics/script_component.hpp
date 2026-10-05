#define COMPONENT optics
#define COMPONENT_BEAUTIFIED AEE Optics
#include "\z\aee\addons\main\script_mod.hpp"
#include "\z\aee\addons\main\script_macros.hpp"

// Weather film grain (aee-workshop-copy item 5).  Interim module constants;
// the register-and-probe todo promotes them to the weatherGrainIntensity and
// weatherGrainRainThreshold CBA settings.  The off-threshold is below the
// on-threshold, so a rain value at the boundary does not toggle every tick.
#define AEE_WEATHER_GRAIN_INTENSITY 0.5
#define AEE_WEATHER_GRAIN_RAIN_ON 0.2
#define AEE_WEATHER_GRAIN_RAIN_OFF 0.1
