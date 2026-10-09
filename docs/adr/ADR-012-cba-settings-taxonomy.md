# ADR-012: CBA Settings Taxonomy

Status: Accepted
Date: 2026-10-04
Decision: Three top-level categories carry the settings that are not a
per-module model control: AEE Experimental for the thermal-fusion feature
knobs, AEE HUD for the on-screen displays, and AEE Debug for every
diagnostic switch. The move is a relabel. No default changes and no feature
gates.

## Context

The settings menu grew one category per module. The diagnostic switches
spread across every module under a Diagnostics or Penetration subcategory.
The thermal-fusion feature sat under AEE Thermal beside the sensor model. A
user who wanted to raise a HUD panel, or turn on a trace, had to know which
module owned it.

The CBA settings menu is flat metadata. CBA stores each value in
`profileNamespace` under the setting name, for example
`aee_thermal_fusionAlwaysOn`. The category is display metadata only. A
category move therefore keeps every stored value and every runtime
behaviour.

The ADR number is 012. ADR-011 is reserved by the coverage-gaps plan for the
nightly headless regression test.

## Decision

1. **AEE Experimental > Fusion** holds the four thermal-fusion knobs:
   `aee_thermal_fusionAlwaysOn`, `aee_thermal_fusionFovFrame`,
   `aee_thermal_fusionOutline` and `aee_thermal_fusionSolidFill`. The move
   is a relabel. The recorded default is relabel only. To gate the feature,
   an owner changes the `fusionFovFrame` default from true to false and the
   `fusionOutline` default from true to false. That is a separate owner
   decision and is not in this record.

2. **AEE HUD > Displays** holds the four on-screen displays:
   `aee_thermal_fusionHud`, `aee_optics_hudEnabled`,
   `aee_physiology_HUDWarningThreshold` and `aee_nightvision_ltmEnabled`
   (the NVG laser target marker). Precedence rule: a setting that toggles an
   on-screen readout panel goes to HUD even when its code is fusion or ECOTI.
   `fusionFovFrame` and `fusionOutline` are render primitives on the fused
   image, not standalone readout panels, so they stay in Experimental with the
   feature.

3. **AEE Debug > <component>** holds every diagnostic switch: the ten that
   existed and the thirteen that the coverage-gaps plan added. The
   subcategory is the owning component, so `AEE Debug > Thermal` shows both
   thermal switches together. The `aee_radio_logDebug` switch stays inside
   its `if (_hasHost)` guard.

4. A contract test, `tools/tests/test_settings_taxonomy.py`, locks the three
   groups. It fails when a moved setting is mis-categorised or when a new
   setting enters a taxonomy category outside the contract.

5. Sequencing: the coverage-gaps plan runs first and authors its thirteen
   switch lines once. This plan re-categorises those lines once. No switch is
   declared twice.

## Consequences

- Good: a user finds the diagnostics in one place, the HUD displays in one
  place, and the experimental feature in one place. Every stored value
  survives the move.
- Cost: the generated configuration chapter and the Annex C counts change.
  The generator and `validate_cba_settings.py` are the corrective gates.
- Risk: a stale test that locks a moved category string. The repository-wide
  sweep and the full test run catch it.
- No feature is disabled, no default changes, no setting leaves the registry,
  and no stringtable or allowlist entry changes.

## References

- Plan: `.omo/plans/aee-settings-taxonomy.md`.
- `addons/lib/script_macros.hpp`: the macro signature that carries the
  category and subcategory.
- `tools/validation/gen_config_docs.py`: the settings parser and the chapter
  writer.
- `tools/validation/cba_settings_allowlist.txt`: unchanged, because names do
  not change.
- ADR-011 is reserved by `.omo/plans/aee-coverage-gaps.md`.
