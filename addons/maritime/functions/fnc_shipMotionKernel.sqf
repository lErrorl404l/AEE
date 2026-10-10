#include "..\script_component.hpp"

/*
Ship motion kernel: significant pitch, roll and heave from the sea state
(issue #33).

Pure function.  Reads no engine state and writes none.  The driver
(fnc_calculateShipMotion) supplies the sea state and the vessel data; this
kernel returns the three significant amplitudes.

Method: the seakeeping response-amplitude-operator (RAO) method for a
single-degree-of-freedom oscillator, the simplified seakeeping model of
SNAME Principles of Naval Architecture Vol III (Motions in Waves) and
Bhattacharyya, Dynamics of Marine Vehicles.

  1. Wave frequency        omega = 2*pi / Tp
  2. Encounter frequency   omega_e = omega - (omega^2 / g) * U * cos(beta)
       beta is the angle from the ship heading to the direction the waves
       TRAVEL.  0 deg is a following sea, 180 deg a head sea.
       Source: PNA Vol III Ch.3; USNA EN400 Ch.8.
  3. Natural roll          omega_n = sqrt(g * GM / k_xx^2)
       k_xx = 0.35 * B, the roll radius of gyration.  The documented band
       for a loaded cargo ship is 0.35-0.42 * B; 0.35 is the lower edge.
       Source: PNA Vol III Ch.3; IMO IS Code 2008 2.3.4.
  4. Natural pitch         omega_n = sqrt(g * GM_L / k_yy^2)
       GM_L = I_L / V, the longitudinal metacentric height from the box
       waterplane; k_yy = 0.25 * L (UNSOURCED).
       Source: PNA Vol III Ch.3.
  5. Natural heave         omega_n = sqrt(rho * g * A_wp / (m + a33))
       A_wp = L * B box waterplane; a33 ~= m, the heave added mass
       (UNSOURCED).
       Source: Faltinsen, Sea Loads on Ships and Offshore Structures.
  6. RAO                   |H| = 1 / sqrt((1 - r^2)^2 + (2*zeta*r)^2)
       r = omega_e / omega_n.
       Source: PNA Vol III Ch.3; USNA EN455 Ch.4.
  7. Roll and pitch follow the effective wave slope s = (omega^2/g) * (Hs/2),
     resolved by heading: roll by |sin(beta)| (the beam component), pitch
     by |cos(beta)| (the head component).  Heave follows the wave
     amplitude Hs/2.  Hs/2 is the characteristic single amplitude
     (Longuet-Higgins 1952; Stewart, Introduction to Physical Oceanography
     Ch.16.4).
       Source: PNA Vol III Ch.3.

UNSOURCED values (no primary source found; also recorded in the ADR):
  k_yy = 0.25 * L    pitch radius of gyration ratio
  a33 ~= m           heave added-mass ratio
  zeta               damping ratio, supplied by the caller (0.10 typical)

Arguments:
  0: waveHeightM (NUMBER) significant wave height Hs, m
  1: wavePeriodS (NUMBER) peak wave period Tp, s
  2: shipSpeedMs (NUMBER) ship speed U, m/s
  3: waveRelDeg  (NUMBER) ship heading to wave travel direction, deg
  4: beamM       (NUMBER) vessel beam B, m
  5: lengthM     (NUMBER) vessel length L, m
  6: massKg      (NUMBER) vessel mass m, kg
  7: gmM         (NUMBER) metacentric height GM, m
  8: zeta        (NUMBER) damping ratio

Returns:
  ARRAY [pitchDeg, rollDeg, heaveM].
*/

params [
    ["_waveHeightM", 0, [0]],
    ["_wavePeriodS", 8, [0]],
    ["_shipSpeedMs", 0, [0]],
    ["_waveRelDeg", 0, [0]],
    ["_beamM", 10, [0]],
    ["_lengthM", 30, [0]],
    ["_massKg", 100000, [0]],
    ["_gmM", 1.5, [0]],
    ["_zeta", 0.10, [0]]
];

if ((_waveHeightM <= 0) || (_wavePeriodS <= 0) || (_beamM <= 0) || (_lengthM <= 0) || (_massKg <= 0) || (_gmM <= 0)) exitWith {
    [0, 0, 0]
};

private _g = 9.81;
private _rho = 1025;

// ─── Wave and encounter frequency ─────────────────────────────────────────
private _omega = (2 * pi) / _wavePeriodS;
private _omegaE = _omega - (((_omega ^ 2) / _g) * _shipSpeedMs * cos _waveRelDeg);

// ─── Natural frequencies ──────────────────────────────────────────────────
private _kxx = 0.35 * _beamM;
private _omegaNroll = sqrt ((_g * _gmM) / (_kxx ^ 2));

private _kyy = 0.25 * _lengthM;
private _gmLong = ((_beamM * (_lengthM ^ 3)) / 12) / (_massKg / _rho);
private _omegaNpitch = sqrt ((_g * _gmLong) / (_kyy ^ 2));

private _omegaNheave = sqrt ((_rho * _g * _lengthM * _beamM) / (_massKg * 2));

// ─── Response amplitude operators ─────────────────────────────────────────
private _rRoll = _omegaE / _omegaNroll;
private _rPitch = _omegaE / _omegaNpitch;
private _rHeave = _omegaE / _omegaNheave;
private _raoRoll = 1 / sqrt (((1 - (_rRoll ^ 2)) ^ 2) + ((2 * _zeta * _rRoll) ^ 2));
private _raoPitch = 1 / sqrt (((1 - (_rPitch ^ 2)) ^ 2) + ((2 * _zeta * _rPitch) ^ 2));
private _raoHeave = 1 / sqrt (((1 - (_rHeave ^ 2)) ^ 2) + ((2 * _zeta * _rHeave) ^ 2));

// ─── Significant amplitudes ───────────────────────────────────────────────
private _amp = _waveHeightM / 2;
private _slope = ((_omega ^ 2) / _g) * _amp;
private _rollRad = _slope * (abs (sin _waveRelDeg)) * _raoRoll;
private _pitchRad = _slope * (abs (cos _waveRelDeg)) * _raoPitch;
private _heaveM = _amp * _raoHeave;

private _degPerRad = 180 / pi;
[_pitchRad * _degPerRad, _rollRad * _degPerRad, _heaveM]
