#include "..\script_component.hpp"
/*
Free recoil from the conservation of momentum.

The source is the SAAMI Gun Recoil Formulae, which defines the recoiling
momentum as the ejecta momentum plus the propellant gas momentum, with
the gas velocity taken as a multiple of the muzzle velocity:

    I   = m_e v_e + m_p v_p        (kg m/s)
    V   = I / m_f                  (m/s)
    FRE = 0.5 m_f V^2              (J)

The gas factor is 1.75 for a high powered rifle, 1.50 for a shotgun or a
pistol and revolver, and 1.25 for a long barrelled shotgun. The cartridge
classification gives the arm type, so the caller does not have to.

A cannon uses a different term. The SAAMI factors are fitted to cartridge
small arms. For a cannon the Lagrange approximation gives the recoil
momentum as (m_ejecta + m_charge / 2) * v (AMCP 706-150, equation 2-5).
The arm type "cannon" selects that term.

The standard's own worked example is reproduced in
tools/validation/validate_recoil.py: a 12 bore shotgun of 3.175 kg firing
38.22 g of ejecta at 388.6 m/s with a 2.165 g charge returns 40.9 J, which
is the 30.22 ft-lb the standard prints.

Arguments:
  0: ejecta mass (NUMBER, kg, the bullet or the shot charge plus wad)
  1: muzzle velocity (NUMBER, m/s)
  2: propellant charge mass (NUMBER, kg, 0 when not held)
  3: firearm mass (NUMBER, kg, 0 when not held)
  4: arm type (STRING, "rifle", "shotgun", "shotgun_long", "pistol" or
     "cannon")

Returns [impulse Ns, recoil velocity m/s, free recoil energy J]. A zero
firearm mass or a zero velocity returns zeros, because free recoil is
undefined without them.
*/

params [
    ["_ejectaKg", 0, [0]],
    ["_mvMs", 0, [0]],
    ["_chargeKg", 0, [0]],
    ["_firearmKg", 0, [0]],
    ["_armType", "rifle", [""]]
];

if (_firearmKg <= 0 || _mvMs <= 0) exitWith { [0, 0, 0] };

private _arm = toLower _armType;

// The cannon branch uses the Lagrange approximation, not the SAAMI
// small-arms gas factors: the propellant gas is treated as half its mass
// moving with the projectile, so the recoiling momentum is
// (m_ejecta + m_charge / 2) * v. Source: AMCP 706-150, Interior
// Ballistics of Guns, US Army Materiel Command 1965, equation 2-5, held at
// data/ballistics/sources/amcp_706_150.pdf. The SAAMI factors are fitted
// to cartridge small arms and do not transfer to a cannon charge.
private _impulse = if (_arm == "cannon") then {
    _mvMs * (_ejectaKg + 0.5 * _chargeKg)
} else {
    private _factor = switch (_arm) do {
        case "shotgun_long": { 1.25 };
        case "shotgun": { 1.50 };
        case "pistol": { 1.50 };
        default { 1.75 };
    };
    _ejectaKg * _mvMs + _chargeKg * _mvMs * _factor
};

private _velocity = _impulse / _firearmKg;
private _energy = 0.5 * _firearmKg * _velocity * _velocity;

[_impulse, _velocity, _energy]
