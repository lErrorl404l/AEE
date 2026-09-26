# Vehicle mass estimate: modelled layer

The vehicle mass estimate is a modelled layer. It is not a catalogue entry.
The layer gives a bounded mass range for a ground vehicle when the sourced
catalogue holds no weight for it.

The value is modelled, not sourced. The catalogue keeps its no-invention
rule. The estimate is separate from the sourced catalogue.

## 1. What the estimate reads

The engine reports the vehicle box size. The model combines the box volume
with a cited material density and a calibrated fill factor. The estimate is
AEE-relative and engine-relative. The engine value is not a real-world mass.

The catalogue path runs first. When a sourced weight exists, the estimate
returns the sourced weight and the model does not run. When no sourced
weight exists, the estimate returns a bounded range. Tests guard the
separation of the model from the catalogue, the generated matcher and the
NRMM soil function.

## 2. Enable state

The estimate is off by default. Two conditions must both hold.

1. The CBA setting `aee_mobility_estimateVehicleMassEnabled` must be true.
2. The model approval flag `calibration.approved` must be true.

When either condition is false, the function returns `unavailable`. The
function never returns a number when the model is unapproved or the setting
is off.

## 3. Calibration

The model is calibrated against the documented catalogue weights. The gate
passes these metrics.

| Metric | Value |
|---|---|
| Entries | 46 |
| Fraction in band | 1.0 |
| MdAPE | 0.1402 |
| Wheeled width ratio | 3.9821 |
| Tracked width ratio | 2.3405 |
| Approved | true |

The gate thresholds are n>=30, fraction_in_band>=0.80, MdAPE<=0.35 and a
class width ratio <=6.

## 4. Power-to-weight band

The power-to-weight band is disabled. The in-engine probe returned engine
values only. The engine `enginePower` value is a PhysX tuning value with no
verified real-world unit. The probe found an engine-relative spread of
6.033 over five classes. This spread is wider than the hard factor 2.0. The
sample classes carry no cited published power, so the tracking check cannot
be evaluated. No band is written. The evidence is
`.omo/evidence/vehicle-mass-model/power-probe.json`.

## 5. Files

| Path | Role |
|---|---|
| `data/vehicle/mass_model.json` | Cited densities, calibrated fills and the approval flag. |
| `tools/validation/validate_vehicle_mass_model.py` | Calibration and approval gate. |
| `tools/validation/gen_vehicle_mass_model.py` | Renders the runtime table. |
| `addons/mobility/functions/fnc_getVehicleMassModel.sqf` | Generated parameter table. |
| `addons/mobility/functions/fnc_estimateVehicleMassCore.sqf` | Pure bounded arithmetic. |
| `addons/mobility/functions/fnc_estimateVehicleMass.sqf` | Engine-reading wrapper. |
| `addons/mobility/functions/fnc_getVehicleMatch.sqf` | The sourced matcher. This layer does not change it. |
| `addons/mobility/functions/fnc_calculateSoilStrength.sqf` | The NRMM path. This layer does not change it. |

The governing rules are JSP 945 for configuration management and Def Stan
05-138 for cyber security.
