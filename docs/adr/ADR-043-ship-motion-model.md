# ADR-043: Ship motion from the sea state

Status: Accepted
Date: 2026-10-10

Decision: Model ship pitch, roll and heave with the seakeeping
response-amplitude-operator (RAO) method for a single-degree-of-freedom
oscillator, driven by the maritime module's Pierson-Moskowitz sea state.
The kernel is pure. The driver publishes the significant amplitudes as
state for the weapon-accuracy, helicopter-deck and crew-fatigue consumers.

## Context

Issue #33 asks for ship pitch, roll and heave from the sea state and the
vessel characteristics, to affect weapon accuracy, helicopter operations
and crew fatigue. The maritime module already publishes the Beaufort sea
state and the Pierson-Moskowitz significant wave height
(fnc_calculateSeaState). The engine publishes no hydrostatics for a vessel.

## Decision

1. The model is the linear seakeeping RAO method (SNAME Principles of Naval
   Architecture Vol III; Bhattacharyya, Dynamics of Marine Vehicles). Each
   degree of freedom is a single-degree-of-freedom oscillator with response
   `|H| = 1 / sqrt((1 - r^2)^2 + (2*zeta*r)^2)` and `r = omega_e / omega_n`.
2. The encounter frequency is `omega_e = omega - (omega^2/g)*U*cos(beta)`,
   the standard advancing-ship relation. `beta` is the angle from the ship
   heading to the direction the waves travel.
3. The natural roll frequency is `sqrt(g*GM / k_xx^2)` with
   `k_xx = 0.35*B` (documented band 0.35-0.42*B). The natural pitch and
   heave frequencies use the box-waterplane hydrostatics (`GM_L = I_L/V`,
   `A_wp = L*B`).
4. Roll and pitch follow the effective wave slope `(omega^2/g)*(Hs/2)`,
   resolved by heading. Heave follows the amplitude `Hs/2`.
5. The metacentric height GM and the damping ratio zeta are CBA settings,
   because the engine publishes neither. The defaults are 1.5 m and 0.10.
6. The model runs client-side (hasInterface) for the vessels near the
   player, once per second, and publishes per-vessel and module state.
7. The kernel is pure: `addons/maritime/functions/fnc_shipMotionKernel.sqf`.
   The driver is `fnc_calculateShipMotion.sqf`.

## Consequences

- The significant motion is set by the encounter-frequency resonance, not
  by linear growth with the sea state. For a fully-developed
  Pierson-Moskowitz sea the characteristic wave slope is nearly constant,
  so the issue's illustrative monotonic ranges do not hold. The model is
  the physical one.
- The engine gives no GM, pitch radius of gyration or added mass, so three
  coefficients are UNSOURCED: `k_yy = 0.25*L`, `a33 ~= m` and `zeta`. They
  are marked in the kernel and are operator-tunable (zeta) or documented
  constants (k_yy, a33).
- Issue #33 cites NATO STANAG 4569 for helicopter landing conditions. That
  is a defect. STANAG 4569 covers vehicle armour. The governing document is
  STANAG 4154 (seakeeping), and a deck-motion limit is a per-type SHOL
  envelope, not one standard, so no universal angle threshold is published.
- The published state is the integration contract. A consumer sets its own
  weapon-accuracy and helicopter thresholds.

## References

- SNAME, Principles of Naval Architecture Vol III (Motions in Waves and
  Controllability), Lewis (ed.), 1988.
- Bhattacharyya, Dynamics of Marine Vehicles, 1978.
- Faltinsen, Sea Loads on Ships and Offshore Structures, 1990.
- IMO, International Code on Intact Stability 2008, Part A 2.3.4.
- Pierson and Moskowitz 1964. Stewart, Introduction to Physical
  Oceanography, Ch.16.4.
- Longuet-Higgins 1952.
- NATO STANAG 4154, Common Procedures for Seakeeping in Ship Design.
