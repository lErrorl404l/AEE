#define COMPONENT ballistics
#define COMPONENT_BEAUTIFIED AEE Ballistics
#include "\z\aee\addons\lib\script_mod.hpp"
#include "\z\aee\addons\lib\script_macros.hpp"

// Ammo shot heat, degC per joule of round energy.  One definition, because
// the setting default, the read fallback and the type guard must agree; two
// copies of the number drift (see tools/tests/test_value_markers.py).
// Declared default with no published source, labelled in
// fnc_calculateAmmoTemperature.
#define AEE_AMMO_HEAT_PER_SHOT_DEFAULT 0.0001
