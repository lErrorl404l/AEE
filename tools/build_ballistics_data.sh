#!/usr/bin/env bash
#
# Build the verified ballistics database and its runtime projections.
#
# One command, no network. The fetch_* tools are separate because they
# only run when a new source is added.
#
# The order is not arbitrary. Each step is listed with the reason it sits
# where it does, and a step that rebuilds a set always runs before the
# steps that enrich that set.
#
# Run:  make data        (or)   tools/build_ballistics_data.sh
#
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
V="tools/validation"

step() {
    printf '\n==> %s\n' "$1"
    shift
    "$PYTHON" "$@"
}

# ─── The cartridge and projectile records ─────────────────────────────────
# The register tools only add a record that is absent, so they run first.
step "cartridges: C.I.P. register" "$V/gen_cartridges_from_cip.py"
step "cartridges: SAAMI register" "$V/gen_cartridges_from_saami.py"
step "cartridges: NATO EPVAT" "$V/gen_cartridges_nato.py"

# gen_projectiles rebuilds the maker catalogue records, so everything that
# enriches a projectile runs after it.
step "projectiles: maker catalogues" "$V/gen_projectiles.py"
step "projectiles: Aberdeen Proving Ground" "$V/gen_projectiles_from_apg.py"
step "projectiles: lengths" "$V/gen_lengths.py"

# gen_found_data merges the held documents into both layers.
step "found data: pressures, twists, lengths" "$V/gen_found_data.py"
# The reference twists and the records no register holds, after the
# register tools and the found data, so nothing overwrites a held value.
step "cartridges: reference twists" "$V/gen_cartridge_standards.py"

step "projectiles: corroboration" "$V/gen_bc_corroboration.py"
# A derived value is deliberately absent from the database.
step "projectiles: strip derived BC" "$V/strip_derived_bc.py"
# Stability needs the mass, the length and the twist, so it runs last of
# the projectile steps.
step "projectiles: Miller stability" "$V/gen_stability.py"

# ─── The loads ────────────────────────────────────────────────────────────
# gen_loads_from_mil rebuilds the load set, so the velocity anchors run
# after it.
step "loads: military documents" "$V/gen_loads_from_mil.py"
step "loads: velocity anchors" "$V/gen_loads_from_velocity.py"

# ─── The weapon layer ─────────────────────────────────────────────────────
step "weapons: catalogue" "$V/gen_weapons.py"
# Service designations become aliases of the real weapon, so a national
# designation resolves to that weapon's own twist. Runs after the
# catalogue, which holds the target records.
step "weapons: service designations" "$V/gen_designations.py"
# The chambering join is complete now, so the gaps are the true ones. The
# report drives the research that adds the missing cartridge records.
step "weapons: chambering gaps" "$V/gen_chambering_gaps.py"
step "weapons: corpus leads" "$V/gen_weapon_leads.py"
step "weapons: verification worklist" "$V/gen_weapon_worklist.py"
# The mass worklist is the research backlog grouped by manufacturer, so one
# catalogue page covers a family. It reads the weapon records, which hold
# the maker, so no row is left unattributed.
step "weapons: mass worklist" "$V/gen_weapon_mass_worklist.py"

# The recoil inputs: a weapon mass and a propellant charge mass. They
# merge after the catalogue, because a mass attaches to a weapon record.
step "weapons: mass and load charge" "$V/gen_recoil_data.py"

# ─── The drag functions ───────────────────────────────────────────────────
step "drag: merge the functions" "$V/merge_drag_functions.py"

# ─── The runtime projections ──────────────────────────────────────────────
# These read the research database and write the SQF tables, so they run
# after every research step and before the gates.
step "runtime: cartridges" "$V/gen_runtime_cartridges.py"
step "runtime: projectiles" "$V/gen_runtime_projectiles.py"
step "runtime: weapons" "$V/gen_runtime_weapons.py"
step "runtime: drag tables" "$V/gen_runtime_drag.py"
# The magazine mass feeds the load model in physiology.
step "runtime: magazine mass" "$V/gen_runtime_magazines.py"
# The equipment captures (uniforms, garments, vests, rucksacks, helmets,
# devices and kit) project onto the item-mass resolver the load walk uses.
step "runtime: equipment item mass" "$V/gen_equipment_data.py"

# ─── The human-readable outputs ───────────────────────────────────────────
step "docs: ballistics index and CSV" "$V/render_ballistics_index.py"
step "docs: CSV export" "$V/export_ballistics_csv.py"

# ─── The gate ─────────────────────────────────────────────────────────────
step "gate: data contract" "$V/validate_ballistics_data.py"
step "gate: runtime tests" "tools/tests/test_runtime_weapons.py"
step "gate: coverage audit" "$V/audit_coverage.py"

printf '\nballistics data: complete\n'
