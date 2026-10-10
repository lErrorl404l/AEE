/* SPDX-License-Identifier: GPL-2.0-or-later */
// Generated engine config override. Do not edit by hand.
// Regenerate with: python3 tools/validation/gen_physics_config.py
//
// This is a load-time, global override of vanilla engine config. The
// engine reads it when the config loads and config cannot be gated at
// runtime, so the PBO is the only off switch.
//
// Each class restates its immediate real parent, and the parent is
// forward-declared once:
//
//     class <Parent>;
//     class <X>: <Parent> { maxSpeed = v; mass = w; };
//
// A reopen that omits the parent invokes the engine Empty syntax and
// strips the vanilla class of every inherited property. A forward
// declaration alone does not carry the parent, so the child restates
// it. The generator never emits a bare class.
//
// It declares maxSpeed and mass for the pre-existing land classes. Those
// keys are NOT identity-derived and the aircraft gate never
// retro-applies to them. thermal and optics own htMin, htMax, afMax,
// mfMax, mFact and tBody; a redeclaration here would win and change the
// thermal model, so no thermal key is admitted. Each mass is a
// calibrated scale of a held real mass, never a copied engine number,
// from data/physics/mass_calibration.json.
//
// The aircraft fuel keys are gated at BUILD TIME: they are emitted
// only when the class identity grade and the held value grade are both
// documented. Config is load-time and global, so the build-time
// predicate is the only gate. Every aircraft class binding is claimed
// today, so NO aircraft key ships yet. That is the gate working, not a
// broken generator.
//
// fuelConsumptionRate = 0 is a STRUCTURAL ZERO. It disables the
// engine's own burn, so the scripted burn from the sourced systems-row
// fuel_consumption_rate is authoritative and the two never double-count.
// The sourced rate stays in the systems row and is never emitted here.
// The zero is emitted ONLY for a class the fuel driver covers, so a
// class never has infinite fuel when the script is not running.
//
// The aircraft mass key is gated the same way. CfgVehicles mass is the
// PHYSX mass, NOT the RotorLib flight-dynamics mass: a RotorLib airframe
// carries a separate emptyMass and an RTD XML Mass, two different
// values. The mass is the sourced operating_weight_kg. The land mass
// calibration is a ground fit over ground classes and is NEVER applied
// to an aircraft.
//
// The centre of gravity is emitted as centerOfMass only where the engine
// accepts it, from the sourced cg_empty_m, under the same build-time
// gate. Moments of inertia are REFERENCE ONLY: the engine has no runtime
// inertia hook, so no inertia key is emitted.
//
// The land carx/tankx/shipx physics surface is gated the SAME way, on the
// class identity grade (data/vehicle/class_bindings.json) and the held
// value grade. EVERY land class binding is claimed today, so the predicate
// emits NO new land key and the surface is UNPROVEN this phase until a
// binding becomes documented. The engine-schema structural keys are engine
// tuning and are never emitted. enginePower, peakTorque, torqueCurve and
// the gearbox ratios are EXCLUDED until the in-engine probe resolves the
// enginePower unit and the drivability. This is the gate working, not a
// broken generator.
//
// One block carries every key: the engine lint rejects a second
// CfgVehicles block in the same addon.

class CfgVehicles {
    class B_MBT_01_base_F;

    class B_MBT_01_cannon_F: B_MBT_01_base_F {
        maxBrakeTorque = 55000;
    };
};
