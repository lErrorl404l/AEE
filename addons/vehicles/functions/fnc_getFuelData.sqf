#include "..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_fuel_data.py

The runtime fuel and coolant constant table (issue #111), projected from
data/physics/fuel.json by tools/gen_fuel_data.py. The corpus is the only home
for a value; this table is the runtime projection. The generator refuses a
corpus that does not validate, so no value here can be one the validator would
reject.

Sections, each a hashmap:
  engine_classes      id -> [bsfc_g_kwh, fuel_id]
  fuels               id -> [density_g_l, lhv_mj_kg]
  rolling_resistance  id -> crr
  terrain_multipliers ground_state -> multiplier
  thermal             id -> value

Arguments: none.
Return Value: HASHMAP - the five sections.
Public: No
*/

private _table = createHashMapFromArray [
    ["engine_classes", createHashMapFromArray [
        ["petrol_na", [225.0, "petrol"]],
        ["petrol_turbo", [240.0, "petrol"]],
        ["diesel", [206.0, "diesel"]]
    ]],
    ["fuels", createHashMapFromArray [
        ["petrol", [740.0, 43.9]],
        ["diesel", [840.0, 42.7]],
        ["jp8", [800.0, 43.0]]
    ]],
    ["rolling_resistance", createHashMapFromArray [
        ["car", 0.0125],
        ["truck", 0.007],
        ["track", 0.03],
        ["dirt_road", 0.05575],
        ["sand", 0.3]
    ]],
    ["terrain_multipliers", createHashMapFromArray [
        ["Normal", 1.0],
        ["Dusty", 1.5],
        ["Frozen", 1.5],
        ["Snow", 2.0],
        ["Mud", 2.5]
    ]],
    ["thermal", createHashMapFromArray [
        ["thermostat_c", 90.0],
        ["coolant_normal_min_c", 85.0],
        ["coolant_normal_max_c", 100.0],
        ["coolant_hot_max_c", 115.0],
        ["coolant_critical_c", 130.0],
        ["coolant_overheat_derate", 0.5],
        ["oil_normal_max_c", 120.0],
        ["oil_limit_c", 140.0],
        ["heat_reject_fraction", 0.333333],
        ["convection_natural_w_m2k", 5.6],
        ["convection_forced_w_m2k_per_ms", 3.9],
        ["coolant_tau_s", 90.0]
    ]]
];

_table
