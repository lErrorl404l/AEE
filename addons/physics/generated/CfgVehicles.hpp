/* SPDX-License-Identifier: GPL-2.0-or-later */
// Generated engine config override. Do not edit by hand.
// Regenerate with: python3 tools/validation/gen_physics_config.py
//
// This is a load-time, global override of vanilla engine config. The
// engine reads it when the config loads and config cannot be gated at
// runtime, so the PBO is the only off switch.
//
// It declares maxSpeed and no other key. thermal and optics already
// override htMin, htMax, afMax, mfMax, mFact and tBody, and this addon
// loads last, so redeclaring those keys here would silently win.

class CfgVehicles {
    class B_AFV_Wheeled_01_cannon_F {
        maxSpeed = 80;
    };
    class B_APC_Wheeled_01_cannon_F {
        maxSpeed = 80;
    };
    class B_MBT_01_cannon_F {
        maxSpeed = 72;
    };
    class B_Truck_01_transport_F {
        maxSpeed = 88;
    };
    class I_APC_Wheeled_03_cannon_F {
        maxSpeed = 80;
    };
    class I_MBT_03_cannon_F {
        maxSpeed = 72;
    };
    class I_Truck_02_transport_F {
        maxSpeed = 88;
    };
    class O_APC_Wheeled_02_rcws_v2_F {
        maxSpeed = 80;
    };
    class O_MBT_02_cannon_F {
        maxSpeed = 72;
    };
    class O_Truck_02_transport_F {
        maxSpeed = 88;
    };
};
