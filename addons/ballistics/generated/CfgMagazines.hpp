/* SPDX-License-Identifier: GPL-2.0-or-later */
// Generated engine config override. Do not edit by hand.
// Regenerate with: python3 tools/validation/gen_engine_overrides.py
//
// CfgMagazines initSpeed. This is a load-time, global override of the vanilla
// engine magazine velocity. The engine reads initSpeed when the magazine is
// created, and config cannot be gated at runtime, so the PBO is the only off
// switch.
//
// Each class restates its immediate real parent, and every parent is
// forward-declared once. A reopen that omits the parent invokes the engine
// Empty syntax and strips the vanilla class of every inherited property. The
// generator never emits a bare class.
//
// initSpeed is the muzzle velocity in m/s of the held load whose projectile
// nature (ball, APFSDS, HEAT, HE, ...) matches the magazine's ammo; a
// magazine whose nature no documented load holds keeps its vanilla value.
// Artillery, mortar and underwater magazines are never overridden.  For ball:
//   * the documented service velocity from the US military specifications and
//     TM 43-0001-27 (grade documented); or, when none is held,
//   * the manufacturer velocity table from Hornady or Lapua (grade claimed).
// The value is held per cartridge in data/ballistics/loads.json. The
// magazine-to-cartridge link is the committed cache
// data/engine/magazine_bindings.json, resolved from the installed game
// config.
//
// CfgMagazines mass is the magazine LOADED mass in the engine unit (0.1 lb,
// 45.359237 g; kg / 0.045359237), from the held
// loaded-mass projection data/ballistics/magazine_masses.json (schema
// aee.ballistics.magazine_mass/1). The loaded mass is the held value where
// it is held, or DERIVED as empty_mass_g + capacity * round_mass_g from the
// held round mass for the chambering. It resolves by the classname capacity
// plus the chambering token, exactly as fnc_getMagazineMass parses a
// classname. A magazine that resolves no mass keeps its initSpeed and is
// recorded below as a mass lead. No engine number is copied.

class CfgMagazines {
    class 1000Rnd_762x51_Belt;
    class 100Rnd_127x99_mag;
    class 12Rnd_125mm_HEAT;
    class 2000Rnd_65x39_Belt;
    class 2000Rnd_762x51_Belt;
    class 200Rnd_127x99_mag;
    class 30Rnd_120mm_HE_shells;
    class 30Rnd_556x45_Stanag_Sand;
    class CA_Magazine;
    class VehicleMagazine;

    class 1000Rnd_762x51_Belt_Green: 1000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 1000Rnd_762x51_Belt_Red: 1000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 1000Rnd_762x51_Belt_Yellow: 1000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 100Rnd_127x99_mag_Tracer_Green: 100Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 100Rnd_127x99_mag_Tracer_Red: 100Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 100Rnd_127x99_mag_Tracer_Yellow: 100Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 150Rnd_762x51_Box: CA_Magazine {
        initSpeed = 838.2;
    };
    class 2000Rnd_762x51_Belt_Green: 2000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 2000Rnd_762x51_Belt_Red: 2000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 2000Rnd_762x51_Belt_Yellow: 2000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 200Rnd_127x99_mag_Tracer_Green: 200Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 200Rnd_127x99_mag_Tracer_Red: 200Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 200Rnd_127x99_mag_Tracer_Yellow: 200Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 200Rnd_762x51_Belt: VehicleMagazine {
        initSpeed = 838.2;
    };
    class 20Rnd_105mm_HEAT_MP: 12Rnd_125mm_HEAT {
        initSpeed = 1173;
    };
    class 20Rnd_120mm_HEAT_MP: VehicleMagazine {
        initSpeed = 1139.95;
    };
    class 20Rnd_762x51_Mag: CA_Magazine {
        initSpeed = 838.2;
        mass = 14.99;
    };
    class 30Rnd_120mm_APFSDS_shells: 30Rnd_120mm_HE_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_556x45_Stanag: CA_Magazine {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Sand_Tracer_Red: 30Rnd_556x45_Stanag_Sand {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Sand_green: 30Rnd_556x45_Stanag_Sand {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Sand_red: 30Rnd_556x45_Stanag_Sand {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 5000Rnd_762x51_Belt: 2000Rnd_65x39_Belt {
        initSpeed = 838.2;
    };
    class 500Rnd_127x99_mag: VehicleMagazine {
        initSpeed = 886.97;
    };
    class 200Rnd_762x51_Belt_Green: 200Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 200Rnd_762x51_Belt_Red: 200Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 200Rnd_762x51_Belt_Yellow: 200Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 20Rnd_105mm_HEAT_MP_T_Green: 20Rnd_105mm_HEAT_MP {
        initSpeed = 1173;
    };
    class 20Rnd_105mm_HEAT_MP_T_Red: 20Rnd_105mm_HEAT_MP {
        initSpeed = 1173;
    };
    class 20Rnd_105mm_HEAT_MP_T_Yellow: 20Rnd_105mm_HEAT_MP {
        initSpeed = 1173;
    };
    class 20Rnd_120mm_HEAT_MP_T_Green: 20Rnd_120mm_HEAT_MP {
        initSpeed = 1139.95;
    };
    class 20Rnd_120mm_HEAT_MP_T_Red: 20Rnd_120mm_HEAT_MP {
        initSpeed = 1139.95;
    };
    class 20Rnd_120mm_HEAT_MP_T_Yellow: 20Rnd_120mm_HEAT_MP {
        initSpeed = 1139.95;
    };
    class 30Rnd_120mm_APFSDS_shells_Tracer_Green: 30Rnd_120mm_APFSDS_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_120mm_APFSDS_shells_Tracer_Red: 30Rnd_120mm_APFSDS_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_120mm_APFSDS_shells_Tracer_Yellow: 30Rnd_120mm_APFSDS_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_556x45_Stanag_Sand_Tracer_Green: 30Rnd_556x45_Stanag_Sand_Tracer_Red {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Sand_Tracer_Yellow: 30Rnd_556x45_Stanag_Sand_Tracer_Red {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Tracer_Green: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Tracer_Red: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_Tracer_Yellow: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_green: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 30Rnd_556x45_Stanag_red: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
        mass = 11.26;
    };
    class 5000Rnd_762x51_Yellow_Belt: 5000Rnd_762x51_Belt {
        initSpeed = 838.2;
    };
    class 500Rnd_127x99_mag_Tracer_Green: 500Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 500Rnd_127x99_mag_Tracer_Red: 500Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 500Rnd_127x99_mag_Tracer_Yellow: 500Rnd_127x99_mag {
        initSpeed = 886.97;
    };
};

// Withheld bindings (no sourced value):
//   1000Rnd_65x39_Belt_Green: no projectile nature in B_65x39_Case_green
//   1000Rnd_65x39_Belt_Tracer_Red: no projectile nature in B_65x39_Caseless
//   1000Rnd_65x39_Belt_Yellow: no projectile nature in B_65x39_Case_Yellow
//   100Rnd_65x39_caseless_mag: no projectile nature in B_65x39_Caseless
//   10Rnd_762x54_Mag: no documented ball load for 7_62_x_54_r
//   11Rnd_45ACP_Mag: no documented ball load for 45_auto
//   150Rnd_762x54_Box: no documented ball load for 7_62_x_54_r
//   16Rnd_9x21_green_Mag: no documented ball load for 9_x_21
//   16Rnd_9x21_red_Mag: no documented ball load for 9_x_21
//   16Rnd_9x21_yellow_Mag: no documented ball load for 9_x_21
//   2000Rnd_65x39_Belt_Green: no projectile nature in B_65x39_Case_Green
//   2000Rnd_65x39_Belt_Tracer_Green_Splash: no projectile nature in B_65x39_Minigun_Caseless_Green_splash
//   2000Rnd_65x39_Belt_Tracer_Red: no projectile nature in B_65x39_Minigun_Caseless_Red_splash
//   2000Rnd_65x39_Belt_Tracer_Yellow_Splash: no projectile nature in B_65x39_Minigun_Caseless_Yellow_splash
//   2000Rnd_65x39_Belt_Yellow: no projectile nature in B_65x39_Case_Yellow
//   200Rnd_65x39_Belt: no projectile nature in B_65x39_Caseless
//   200Rnd_65x39_Belt_Tracer_Green: no projectile nature in B_65x39_Case_green
//   200Rnd_65x39_Belt_Tracer_Red: no projectile nature in B_65x39_Caseless
//   200Rnd_65x39_Belt_Tracer_Yellow: no projectile nature in B_65x39_Case_yellow
//   200Rnd_65x39_cased_Box: no projectile nature in B_65x39_Caseless_yellow
//   200Rnd_65x39_cased_Box_Red: no projectile nature in B_65x39_Caseless
//   200Rnd_65x39_cased_Box_Tracer_Red: no projectile nature in B_65x39_Caseless
//   20Rnd_556x45_UW_mag: artillery, mortar or underwater round (engine-owned initSpeed)
//   30Rnd_120mm_HE_shells: no documented he load for 120mm_m256_smoothbore
//   30Rnd_120mm_HE_shells_Tracer_Green: no documented he load for 120mm_m256_smoothbore
//   30Rnd_120mm_HE_shells_Tracer_Red: no documented he load for 120mm_m256_smoothbore
//   30Rnd_120mm_HE_shells_Tracer_Yellow: no documented he load for 120mm_m256_smoothbore
//   30Rnd_45ACP_Mag_SMG_01: no documented ball load for 45_auto
//   30Rnd_45ACP_Mag_SMG_01_Tracer_Green: no documented ball load for 45_auto
//   30Rnd_45ACP_Mag_SMG_01_Tracer_Yellow: no documented ball load for 45_auto
//   30Rnd_65x39_caseless_green: no projectile nature in B_65x39_Caseless_green
//   30Rnd_65x39_caseless_mag: no projectile nature in B_65x39_Caseless
//   30Rnd_9x21_Green_Mag: no documented ball load for 9_x_21
//   30Rnd_9x21_Mag: no documented ball load for 9_x_21
//   30Rnd_9x21_Mag_SMG_02_Tracer_Green: no documented ball load for 9_x_21
//   30Rnd_9x21_Mag_SMG_02_Tracer_Red: no documented ball load for 9_x_21
//   30Rnd_9x21_Mag_SMG_02_Tracer_Yellow: no documented ball load for 9_x_21
//   30Rnd_9x21_Red_Mag: no documented ball load for 9_x_21
//   30Rnd_9x21_Yellow_Mag: no documented ball load for 9_x_21
//   40Rnd_105mm_APFSDS: no documented apfsds load for 105mm_m68
//   40Rnd_105mm_APFSDS_T_Green: no documented apfsds load for 105mm_m68
//   40Rnd_105mm_APFSDS_T_Red: no documented apfsds load for 105mm_m68
//   40Rnd_105mm_APFSDS_T_Yellow: no documented apfsds load for 105mm_m68
//   450Rnd_127x108_Ball: no documented ball load for 12_7_x_108
//   5Rnd_127x108_APDS_Mag: no documented apds load for 12_7_x_108
//   5Rnd_127x108_Mag: no documented ball load for 12_7_x_108
//   9Rnd_45ACP_Mag: no documented ball load for 45_auto
//   PylonWeapon_500Rnd_127mm_HEIAP_belt_right: no documented heiap load for 50_bmg

// Mass leads (no resolved loaded mass):
//   1000Rnd_762x51_Belt_Green: no resolved loaded mass
//   1000Rnd_762x51_Belt_Red: no resolved loaded mass
//   1000Rnd_762x51_Belt_Yellow: no resolved loaded mass
//   100Rnd_127x99_mag_Tracer_Green: no resolved loaded mass
//   100Rnd_127x99_mag_Tracer_Red: no resolved loaded mass
//   100Rnd_127x99_mag_Tracer_Yellow: no resolved loaded mass
//   150Rnd_762x51_Box: no resolved loaded mass
//   2000Rnd_762x51_Belt_Green: no resolved loaded mass
//   2000Rnd_762x51_Belt_Red: no resolved loaded mass
//   2000Rnd_762x51_Belt_Yellow: no resolved loaded mass
//   200Rnd_127x99_mag_Tracer_Green: no resolved loaded mass
//   200Rnd_127x99_mag_Tracer_Red: no resolved loaded mass
//   200Rnd_127x99_mag_Tracer_Yellow: no resolved loaded mass
//   200Rnd_762x51_Belt: no resolved loaded mass
//   200Rnd_762x51_Belt_Green: no resolved loaded mass
//   200Rnd_762x51_Belt_Red: no resolved loaded mass
//   200Rnd_762x51_Belt_Yellow: no resolved loaded mass
//   20Rnd_105mm_HEAT_MP: no resolved loaded mass
//   20Rnd_105mm_HEAT_MP_T_Green: no resolved loaded mass
//   20Rnd_105mm_HEAT_MP_T_Red: no resolved loaded mass
//   20Rnd_105mm_HEAT_MP_T_Yellow: no resolved loaded mass
//   20Rnd_120mm_HEAT_MP: no resolved loaded mass
//   20Rnd_120mm_HEAT_MP_T_Green: no resolved loaded mass
//   20Rnd_120mm_HEAT_MP_T_Red: no resolved loaded mass
//   20Rnd_120mm_HEAT_MP_T_Yellow: no resolved loaded mass
//   30Rnd_120mm_APFSDS_shells: no resolved loaded mass
//   30Rnd_120mm_APFSDS_shells_Tracer_Green: no resolved loaded mass
//   30Rnd_120mm_APFSDS_shells_Tracer_Red: no resolved loaded mass
//   30Rnd_120mm_APFSDS_shells_Tracer_Yellow: no resolved loaded mass
//   5000Rnd_762x51_Belt: no resolved loaded mass
//   5000Rnd_762x51_Yellow_Belt: no resolved loaded mass
//   500Rnd_127x99_mag: no resolved loaded mass
//   500Rnd_127x99_mag_Tracer_Green: no resolved loaded mass
//   500Rnd_127x99_mag_Tracer_Red: no resolved loaded mass
//   500Rnd_127x99_mag_Tracer_Yellow: no resolved loaded mass
