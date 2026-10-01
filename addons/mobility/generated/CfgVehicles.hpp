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
//     class <X>: <Parent> { maxSpeed = v; };
//
// A reopen that omits the parent invokes the engine Empty syntax and
// strips the vanilla class of every inherited property. A forward
// declaration alone does not carry the parent, so the child restates
// it. The generator never emits a bare class.
//
// It declares maxSpeed and no other key. thermal and optics own htMin,
// htMax, afMax, mfMax, mFact and tBody; a redeclaration here would win
// and change the thermal model, so only maxSpeed is admitted.

class CfgVehicles {
    class AFV_Wheeled_01_base_F;
    class APC_Wheeled_02_base_v2_F;
    class B_APC_Wheeled_01_base_F;
    class B_MBT_01_base_F;
    class I_APC_Wheeled_03_base_F;
    class I_MBT_03_base_F;
    class O_MBT_02_base_F;
    class Truck_01_base_F;
    class Truck_02_transport_base_F;

    class B_AFV_Wheeled_01_cannon_F: AFV_Wheeled_01_base_F {
        maxSpeed = 80;
    };
    class B_APC_Wheeled_01_cannon_F: B_APC_Wheeled_01_base_F {
        maxSpeed = 80;
    };
    class B_MBT_01_cannon_F: B_MBT_01_base_F {
        maxSpeed = 72;
    };
    class B_Truck_01_transport_F: Truck_01_base_F {
        maxSpeed = 88;
    };
    class I_APC_Wheeled_03_cannon_F: I_APC_Wheeled_03_base_F {
        maxSpeed = 80;
    };
    class I_MBT_03_cannon_F: I_MBT_03_base_F {
        maxSpeed = 72;
    };
    class I_Truck_02_transport_F: Truck_02_transport_base_F {
        maxSpeed = 88;
    };
    class O_APC_Wheeled_02_rcws_v2_F: APC_Wheeled_02_base_v2_F {
        maxSpeed = 80;
    };
    class O_MBT_02_cannon_F: O_MBT_02_base_F {
        maxSpeed = 72;
    };
    class O_Truck_02_transport_F: Truck_02_transport_base_F {
        maxSpeed = 88;
    };
};
