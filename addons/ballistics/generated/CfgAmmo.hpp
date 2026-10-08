/* SPDX-License-Identifier: GPL-2.0-or-later */
// Generated engine config override. Do not edit by hand.
// Regenerate with: python3 tools/validation/gen_engine_overrides.py
//
// CfgAmmo airFriction. This is a load-time, global override of the vanilla
// engine projectile drag. The engine reads airFriction when the projectile is
// created, and config cannot be gated at runtime, so the PBO is the only off
// switch.
//
// Each class restates its immediate real parent, and every parent is
// forward-declared once. A reopen that omits the parent invokes the engine
// Empty syntax and strips the vanilla class of every inherited property. The
// generator never emits a bare class.
//
// airFriction is DERIVED, never copied. The engine applies quadratic drag
// a = airFriction * v^2. The verified AEE drag model states the same form with
// retard = 0.00068418 * (Cd / BC) * v^2. The value is that coefficient at the
// reference muzzle Mach (the cartridge service muzzle velocity at ISA sea
// level):
//     airFriction = -0.00068418 * Cd(muzzleMach) / BC
// BC is the held measured or documented ballistic coefficient and Cd is the
// held standard drag curve (data/ballistics/projectiles.json and
// data/ballistics/sources/drag_functions.json, JBM and McCoy). The
// ammo-to-projectile link is the committed cache
// data/engine/ammo_bindings.json.

class CfgAmmo {
    class BulletBase;

    class B_127x99_Ball: BulletBase {
        airFriction = -0.000531115;
    };
    class B_556x45_Ball: BulletBase {
        airFriction = -0.001175773;
    };
    class B_762x51_Ball: BulletBase {
        airFriction = -0.000929668;
    };
};
