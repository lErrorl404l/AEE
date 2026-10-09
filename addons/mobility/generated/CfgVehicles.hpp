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
// One block carries every key: the engine lint rejects a second
// CfgVehicles block in the same addon.

class CfgVehicles {
    class AFV_Wheeled_01_base_F;
    class APC_Wheeled_02_base_v2_F;
    class B_APC_Tracked_01_base_F;
    class B_APC_Wheeled_01_base_F;
    class B_MBT_01_base_F;
    class Hatchback_01_base_F;
    class Hatchback_01_sport_base_F;
    class I_APC_Wheeled_03_base_F;
    class I_APC_tracked_03_base_F;
    class I_MBT_03_base_F;
    class MRAP_01_base_F;
    class MRAP_02_base_F;
    class MRAP_03_base_F;
    class O_APC_Tracked_02_base_F;
    class O_MBT_02_base_F;
    class Truck_01_base_F;
    class Truck_02_transport_base_F;

    class B_AFV_Wheeled_01_cannon_F: AFV_Wheeled_01_base_F {
        maxSpeed = 80;
        mass = 15559.394557;
    };
    class B_APC_Tracked_01_rcws_F: B_APC_Tracked_01_base_F {
        mass = 12988.662235;
    };
    class B_APC_Wheeled_01_cannon_F: B_APC_Wheeled_01_base_F {
        maxSpeed = 80;
        mass = 15559.394557;
    };
    class B_MBT_01_cannon_F: B_MBT_01_base_F {
        maxSpeed = 72;
        mass = 62273.044493;
    };
    class B_MRAP_01_F: MRAP_01_base_F {
        mass = 12725.525416;
    };
    class B_Truck_01_transport_F: Truck_01_base_F {
        maxSpeed = 88;
        mass = 10870.982873;
    };
    class C_Hatchback_01_F: Hatchback_01_base_F {
        mass = 1710.389328;
    };
    class C_Hatchback_01_sport_F: Hatchback_01_sport_base_F {
        mass = 1710.389328;
    };
    class I_APC_Wheeled_03_cannon_F: I_APC_Wheeled_03_base_F {
        maxSpeed = 80;
        mass = 15559.394557;
    };
    class I_APC_tracked_03_cannon_F: I_APC_tracked_03_base_F {
        mass = 12988.662235;
    };
    class I_MBT_03_cannon_F: I_MBT_03_base_F {
        maxSpeed = 72;
        mass = 62273.044493;
    };
    class I_MRAP_03_F: MRAP_03_base_F {
        mass = 12725.525416;
    };
    class I_Truck_02_transport_F: Truck_02_transport_base_F {
        maxSpeed = 88;
        mass = 10870.982873;
    };
    class O_APC_Tracked_02_cannon_F: O_APC_Tracked_02_base_F {
        mass = 12988.662235;
    };
    class O_APC_Wheeled_02_rcws_v2_F: APC_Wheeled_02_base_v2_F {
        maxSpeed = 80;
        mass = 15559.394557;
    };
    class O_MBT_02_cannon_F: O_MBT_02_base_F {
        maxSpeed = 72;
        mass = 62273.044493;
    };
    class O_MRAP_02_F: MRAP_02_base_F {
        mass = 12725.525416;
    };
    class O_Truck_02_transport_F: Truck_02_transport_base_F {
        maxSpeed = 88;
        mass = 10870.982873;
    };
};
