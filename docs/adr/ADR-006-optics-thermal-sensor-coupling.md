# ADR-006: Keep the optics/thermal Sensor Coupling Bidirectional

Status: Accepted
Date: 2026-10-04
Decision: Keep the two-way dependency between `optics` and `thermal`. The sensor lifecycle belongs to optics and the rendering primitives belong to thermal.

## Context

The generated dependency map (`docs/architecture/addon-dependencies.md`)
shows a cycle between `optics` and `thermal`. Issue #203 removed a cycle of
the same shape (`environmental` and `thermal`) by moving a shared coefficient
to the `material` leaf addon.

The optics/thermal cycle has two edges from thermal back into optics:

1. `addons/thermal/initSettings.inc.sqf` calls
   `EFUNC(optics,updateThermalHostSetting)` from the `thermalBaseChannel`
   setting callback. The callback starts or stops the DTV host driver.
2. `addons/thermal/functions/display/fnc_applySelectionThermal.sqf` calls
   `EFUNC(optics,getOpticProperties)` for the mounted optic's magnification.

The forward edge (optics to thermal) is the sensor lifecycle.
`addons/optics/functions/vision/` owns the DTV host, the thermal sensor
ENTER and EXIT, and the per-tick thermal pass, and calls the thermal
rendering functions.

## Decision

Keep the coupling. Do not move the sensor lifecycle or the optic classifier.
Record the coupling here and in the dependency-map commentary.

## Rationale

Reverse edge 1 is a control input. The `thermalBaseChannel` setting selects
the display host, so the setting belongs to thermal, while the host driver it
starts is the optics DTV driver. Inverting it needs the driver moved into
thermal. The driver calls the sensor ENTER and EXIT and the thermal pass, so
the move drags the whole vision pipeline between addons.

Reverse edge 2 is a data input. The thermal renderer needs the mounted
optic's magnification. The classifier that produces it lives in
`addons/optics/functions/sensor/fnc_getOpticProperties.sqf`. Removing the
call needs the classifier moved to a shared leaf addon or copied into
thermal. A copy would drift from the optics classifier.

Both changes move ownership of the vision pipeline and change when the optic
properties resolve. The module-hygiene scope must not change thermal or NVG
exposure behaviour. The concurrent astronomy move also owns the
`optics/functions/sensor/` folder. A safe untangle is therefore out of scope
for this increment.

## Consequences

- The cycle stays in the dependency map as a known, accepted coupling.
- A later increment can remove reverse edge 2 first, if the optic classifier
  gets a shared-leaf home, then remove reverse edge 1.
- The load-order-relevant direction (optics drives thermal) is documented in
  the optics vision functions.

## References

- `docs/architecture/addon-dependencies.md` (generated)
- `tools/tests/test_addon_dependencies.py` (the environmental/thermal guard)
- `addons/optics/functions/vision/` (the sensor lifecycle)
- `addons/thermal/functions/display/fnc_applySelectionThermal.sqf`
- `addons/optics/functions/sensor/fnc_getOpticProperties.sqf`
