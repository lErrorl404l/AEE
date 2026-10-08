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
// initSpeed is the cartridge service muzzle velocity in m/s:
//   * the documented service velocity from the US military specifications and
//     TM 43-0001-27 (grade documented); or, when none is held,
//   * the manufacturer velocity table from Hornady or Lapua (grade claimed).
// The value is held per cartridge in data/ballistics/loads.json. The
// magazine-to-cartridge link is the committed cache
// data/engine/magazine_bindings.json, resolved from the installed game
// config.

class CfgMagazines {
    class 1000Rnd_762x51_Belt;
    class 100Rnd_127x99_mag;
    class 10Rnd_762x51_Mag;
    class 12Rnd_125mm_HEAT;
    class 2000Rnd_65x39_Belt;
    class 2000Rnd_762x51_Belt;
    class 200Rnd_127x99_mag;
    class 24Rnd_125mm_APFSDS;
    class 30Rnd_556x45_Stanag_Sand;
    class 32Rnd_155mm_Mo_shells;
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
    class 1000Rnd_Gatling_30mm_Plane_CAS_01_F: VehicleMagazine {
        initSpeed = 804.67;
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
    class 10Rnd_762x54_Mag: 10Rnd_762x51_Mag {
        initSpeed = 762;
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
        initSpeed = 1679.45;
    };
    class 20Rnd_762x51_Mag: CA_Magazine {
        initSpeed = 838.2;
    };
    class 250Rnd_30mm_HE_shells: VehicleMagazine {
        initSpeed = 804.67;
    };
    class 30Rnd_120mm_HE_shells: VehicleMagazine {
        initSpeed = 1679.45;
    };
    class 30Rnd_556x45_Stanag: CA_Magazine {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Sand_Tracer_Red: 30Rnd_556x45_Stanag_Sand {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Sand_green: 30Rnd_556x45_Stanag_Sand {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Sand_red: 30Rnd_556x45_Stanag_Sand {
        initSpeed = 914.4;
    };
    class 40Rnd_105mm_APFSDS: 24Rnd_125mm_APFSDS {
        initSpeed = 1173;
    };
    class 450Rnd_127x108_Ball: VehicleMagazine {
        initSpeed = 810;
    };
    class 5000Rnd_762x51_Belt: 2000Rnd_65x39_Belt {
        initSpeed = 838.2;
    };
    class 500Rnd_127x99_mag: VehicleMagazine {
        initSpeed = 886.97;
    };
    class 5Rnd_127x108_Mag: CA_Magazine {
        initSpeed = 810;
    };
    class 6Rnd_155mm_Mo_smoke: 32Rnd_155mm_Mo_shells {
        initSpeed = 1679.45;
    };
    class 140Rnd_30mm_MP_shells: 250Rnd_30mm_HE_shells {
        initSpeed = 804.67;
    };
    class 150Rnd_762x54_Box: 150Rnd_762x51_Box {
        initSpeed = 762;
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
        initSpeed = 1679.45;
    };
    class 20Rnd_120mm_HEAT_MP_T_Red: 20Rnd_120mm_HEAT_MP {
        initSpeed = 1679.45;
    };
    class 20Rnd_120mm_HEAT_MP_T_Yellow: 20Rnd_120mm_HEAT_MP {
        initSpeed = 1679.45;
    };
    class 20Rnd_556x45_UW_mag: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
    };
    class 250Rnd_30mm_APDS_shells: 250Rnd_30mm_HE_shells {
        initSpeed = 804.67;
    };
    class 250Rnd_30mm_HE_shells_Tracer_Green: 250Rnd_30mm_HE_shells {
        initSpeed = 804.67;
    };
    class 250Rnd_30mm_HE_shells_Tracer_Red: 250Rnd_30mm_HE_shells {
        initSpeed = 804.67;
    };
    class 30Rnd_120mm_APFSDS_shells: 30Rnd_120mm_HE_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_120mm_HE_shells_Tracer_Green: 30Rnd_120mm_HE_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_120mm_HE_shells_Tracer_Red: 30Rnd_120mm_HE_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_120mm_HE_shells_Tracer_Yellow: 30Rnd_120mm_HE_shells {
        initSpeed = 1679.45;
    };
    class 30Rnd_556x45_Stanag_Sand_Tracer_Green: 30Rnd_556x45_Stanag_Sand_Tracer_Red {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Sand_Tracer_Yellow: 30Rnd_556x45_Stanag_Sand_Tracer_Red {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Tracer_Green: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Tracer_Red: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_Tracer_Yellow: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_green: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
    };
    class 30Rnd_556x45_Stanag_red: 30Rnd_556x45_Stanag {
        initSpeed = 914.4;
    };
    class 40Rnd_105mm_APFSDS_T_Green: 40Rnd_105mm_APFSDS {
        initSpeed = 1173;
    };
    class 40Rnd_105mm_APFSDS_T_Red: 40Rnd_105mm_APFSDS {
        initSpeed = 1173;
    };
    class 40Rnd_105mm_APFSDS_T_Yellow: 40Rnd_105mm_APFSDS {
        initSpeed = 1173;
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
    class 500Rnd_Cannon_30mm_Plane_CAS_02_F: 1000Rnd_Gatling_30mm_Plane_CAS_01_F {
        initSpeed = 804.67;
    };
    class 5Rnd_127x108_APDS_Mag: 5Rnd_127x108_Mag {
        initSpeed = 810;
    };
    class 60Rnd_30mm_APFSDS_shells: 250Rnd_30mm_HE_shells {
        initSpeed = 804.67;
    };
    class PylonWeapon_500Rnd_127mm_HEIAP_belt_right: 500Rnd_127x99_mag {
        initSpeed = 886.97;
    };
    class 140Rnd_30mm_MP_shells_Tracer_Red: 140Rnd_30mm_MP_shells {
        initSpeed = 804.67;
    };
    class 250Rnd_30mm_APDS_shells_Tracer_Green: 250Rnd_30mm_APDS_shells {
        initSpeed = 804.67;
    };
    class 250Rnd_30mm_APDS_shells_Tracer_Red: 250Rnd_30mm_APDS_shells {
        initSpeed = 804.67;
    };
    class 250Rnd_30mm_APDS_shells_Tracer_Yellow: 250Rnd_30mm_APDS_shells {
        initSpeed = 804.67;
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
    class 60Rnd_30mm_APFSDS_shells_Tracer_Green: 60Rnd_30mm_APFSDS_shells {
        initSpeed = 804.67;
    };
    class 60Rnd_30mm_APFSDS_shells_Tracer_Red: 60Rnd_30mm_APFSDS_shells {
        initSpeed = 804.67;
    };
    class 60Rnd_30mm_APFSDS_shells_Tracer_Yellow: 60Rnd_30mm_APFSDS_shells {
        initSpeed = 804.67;
    };
    class 140Rnd_30mm_MP_shells_Tracer_Green: 140Rnd_30mm_MP_shells_Tracer_Red {
        initSpeed = 804.67;
    };
    class 140Rnd_30mm_MP_shells_Tracer_Yellow: 140Rnd_30mm_MP_shells_Tracer_Red {
        initSpeed = 804.67;
    };
};

// Withheld bindings (no sourced value):
//   1000Rnd_65x39_Belt_Green: no muzzle velocity for 6_5_x_39
//   1000Rnd_65x39_Belt_Tracer_Red: no muzzle velocity for 6_5_x_39
//   1000Rnd_65x39_Belt_Yellow: no muzzle velocity for 6_5_x_39
//   100Rnd_65x39_caseless_mag: no muzzle velocity for 6_5_x_39
//   11Rnd_45ACP_Mag: no muzzle velocity for 45_auto
//   16Rnd_9x21_green_Mag: no muzzle velocity for 9_x_21
//   16Rnd_9x21_red_Mag: no muzzle velocity for 9_x_21
//   16Rnd_9x21_yellow_Mag: no muzzle velocity for 9_x_21
//   1Rnd_HE_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_SmokeBlue_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_SmokeGreen_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_SmokeOrange_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_SmokePurple_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_SmokeRed_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_SmokeYellow_Grenade_shell: no muzzle velocity for 40x46_sr
//   1Rnd_Smoke_Grenade_shell: no muzzle velocity for 40x46_sr
//   2000Rnd_65x39_Belt_Green: no muzzle velocity for 6_5_x_39
//   2000Rnd_65x39_Belt_Tracer_Green_Splash: no muzzle velocity for 6_5_x_39
//   2000Rnd_65x39_Belt_Tracer_Red: no muzzle velocity for 6_5_x_39
//   2000Rnd_65x39_Belt_Tracer_Yellow_Splash: no muzzle velocity for 6_5_x_39
//   2000Rnd_65x39_Belt_Yellow: no muzzle velocity for 6_5_x_39
//   200Rnd_40mm_G_belt: no muzzle velocity for 40x46_sr
//   200Rnd_65x39_Belt: no muzzle velocity for 6_5_x_39
//   200Rnd_65x39_Belt_Tracer_Green: no muzzle velocity for 6_5_x_39
//   200Rnd_65x39_Belt_Tracer_Red: no muzzle velocity for 6_5_x_39
//   200Rnd_65x39_Belt_Tracer_Yellow: no muzzle velocity for 6_5_x_39
//   200Rnd_65x39_cased_Box: no muzzle velocity for 6_5_x_39
//   200Rnd_65x39_cased_Box_Red: no muzzle velocity for 6_5_x_39
//   200Rnd_65x39_cased_Box_Tracer_Red: no muzzle velocity for 6_5_x_39
//   30Rnd_45ACP_Mag_SMG_01: no muzzle velocity for 45_auto
//   30Rnd_45ACP_Mag_SMG_01_Tracer_Green: no muzzle velocity for 45_auto
//   30Rnd_45ACP_Mag_SMG_01_Tracer_Yellow: no muzzle velocity for 45_auto
//   30Rnd_65x39_caseless_green: no muzzle velocity for 6_5_x_39
//   30Rnd_65x39_caseless_mag: no muzzle velocity for 6_5_x_39
//   30Rnd_9x21_Green_Mag: no muzzle velocity for 9_x_21
//   30Rnd_9x21_Mag: no muzzle velocity for 9_x_21
//   30Rnd_9x21_Mag_SMG_02_Tracer_Green: no muzzle velocity for 9_x_21
//   30Rnd_9x21_Mag_SMG_02_Tracer_Red: no muzzle velocity for 9_x_21
//   30Rnd_9x21_Mag_SMG_02_Tracer_Yellow: no muzzle velocity for 9_x_21
//   30Rnd_9x21_Red_Mag: no muzzle velocity for 9_x_21
//   30Rnd_9x21_Yellow_Mag: no muzzle velocity for 9_x_21
//   3rnd_UGL_FlareGreen_Illumination_F: no muzzle velocity for 40x46_sr
//   3rnd_UGL_FlareRed_Illumination_F: no muzzle velocity for 40x46_sr
//   3rnd_UGL_FlareWhite_Illumination_F: no muzzle velocity for 40x46_sr
//   3rnd_UGL_FlareYellow_Illumination_F: no muzzle velocity for 40x46_sr
//   40Rnd_40mm_APFSDS_Tracer_Green_shells: no muzzle velocity for 40x46_sr
//   40Rnd_40mm_APFSDS_Tracer_Red_shells: no muzzle velocity for 40x46_sr
//   40Rnd_40mm_APFSDS_Tracer_Yellow_shells: no muzzle velocity for 40x46_sr
//   40Rnd_40mm_APFSDS_shells: no muzzle velocity for 40x46_sr
//   60Rnd_40mm_GPR_Tracer_Green_shells: no muzzle velocity for 40x46_sr
//   60Rnd_40mm_GPR_Tracer_Red_shells: no muzzle velocity for 40x46_sr
//   60Rnd_40mm_GPR_Tracer_Yellow_shells: no muzzle velocity for 40x46_sr
//   60Rnd_40mm_GPR_shells: no muzzle velocity for 40x46_sr
//   7Rnd_408_Mag: no muzzle velocity for 408_chey_tac
//   9Rnd_45ACP_Mag: no muzzle velocity for 45_auto
//   UGL_FlareCIR_F: no muzzle velocity for 40x46_sr
//   UGL_FlareGreen_F: no muzzle velocity for 40x46_sr
//   UGL_FlareGreen_Illumination_F: no muzzle velocity for 40x46_sr
//   UGL_FlareRed_F: no muzzle velocity for 40x46_sr
//   UGL_FlareRed_Illumination_F: no muzzle velocity for 40x46_sr
//   UGL_FlareWhite_F: no muzzle velocity for 40x46_sr
//   UGL_FlareWhite_Illumination_F: no muzzle velocity for 40x46_sr
//   UGL_FlareYellow_F: no muzzle velocity for 40x46_sr
//   UGL_FlareYellow_Illumination_F: no muzzle velocity for 40x46_sr
