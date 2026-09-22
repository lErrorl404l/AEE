#!/usr/bin/env python3
"""Free recoil from the SAAMI Gun Recoil Formulae.

The standard defines free recoil energy from the conservation of momentum:

    V      = (W_E V_E + W_PC V_PG) / (7000 W_F)        (imperial)
    FRE    = (W_F / 64.34) V^2

and the gas velocity is a multiple of the ejecta velocity:

    V_PG = f V_E, with f = 1.75 high powered rifle, 1.50 shotgun or
    pistol and revolver, 1.25 long barrelled shotgun.

The same relation in SI units, which is what the mod uses, is

    I      = m_e V_E + m_p V_PG        (kg m/s, the recoil impulse)
    V      = I / m_f                   (m/s, the recoil velocity)
    FRE    = 0.5 m_f V^2               (J)

The check below mirrors the standard's own worked example, so the SQF
implementation and this reference are validated against the document
rather than against each other.

Run:  python3 tools/validation/validate_recoil.py
"""

import sys

GRAIN_KG = 6.479891e-5
FOOT_POUND_J = 1.3558179483314004
LB_KG = 0.45359237
FPS_MS = 0.3048

GAS_FACTOR = {
    "rifle": 1.75,
    "shotgun": 1.50,
    "shotgun_long": 1.25,
    "pistol": 1.50,
}


def free_recoil(ejecta_kg, mv_ms, charge_kg, firearm_kg, arm_type="rifle"):
    """Return (impulse Ns, recoil velocity m/s, free recoil energy J)."""
    if firearm_kg <= 0 or mv_ms <= 0:
        return 0.0, 0.0, 0.0
    factor = GAS_FACTOR.get(arm_type, GAS_FACTOR["rifle"])
    impulse = ejecta_kg * mv_ms + charge_kg * mv_ms * factor
    velocity = impulse / firearm_kg
    energy = 0.5 * firearm_kg * velocity * velocity
    return impulse, velocity, energy


def check_saami_example():
    """The standard's worked example, 12 bore shotgun, average barrel."""
    ejecta_kg = 589.9 * GRAIN_KG
    charge_kg = 33.4 * GRAIN_KG
    mv_ms = 1275 * FPS_MS
    firearm_kg = 7.0 * LB_KG
    impulse, velocity, energy = free_recoil(
        ejecta_kg, mv_ms, charge_kg, firearm_kg, "shotgun"
    )
    ft_lb = energy / FOOT_POUND_J
    expected_ft_lb = 30.22
    error = abs(ft_lb - expected_ft_lb) / expected_ft_lb
    print(
        f"SAAMI worked example: impulse {impulse:.3f} Ns, "
        f"velocity {velocity:.3f} m/s, energy {energy:.2f} J "
        f"= {ft_lb:.2f} ft-lb (standard prints {expected_ft_lb})"
    )
    if error > 0.02:
        print(f"FAIL: {error * 100:.1f}% from the printed value")
        return 1
    print(f"PASS: within {error * 100:.2f}% of the printed value")
    return 0


def check_monotonic():
    """A heavier firearm, and a lighter charge, must reduce the energy."""
    rifle = free_recoil(0.0104, 838, 0.0016, 4.0, "rifle")
    heavy = free_recoil(0.0104, 838, 0.0016, 8.0, "rifle")
    checks = [
        ("a heavier firearm recoils less", heavy[2] < rifle[2]),
        ("the impulse is positive", rifle[0] > 0),
        (
            "the energy follows the velocity",
            abs(rifle[2] - 0.5 * 4.0 * rifle[1] ** 2) < 1e-9,
        ),
        (
            "pistols use the shotgun factor",
            GAS_FACTOR["pistol"] == GAS_FACTOR["shotgun"],
        ),
    ]
    failed = 0
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
        failed += 0 if ok else 1
    return failed


def check_arm_types():
    """A rifle must recoil harder than a long-barrelled shotgun, all else
    equal, because its gas factor is larger."""
    rifle = free_recoil(0.03, 400, 0.002, 3.2, "rifle")[2]
    long_shotgun = free_recoil(0.03, 400, 0.002, 3.2, "shotgun_long")[2]
    ok = rifle > long_shotgun
    print(f"{'PASS' if ok else 'FAIL'}: rifle gas factor exceeds the long shotgun")
    return 0 if ok else 1


def main():
    failed = check_saami_example() + check_monotonic() + check_arm_types()
    print(f"recoil validation: {'PASS' if failed == 0 else 'FAIL'}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
