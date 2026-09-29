#include "..\..\script_component.hpp"
/*
Atmospheric transmission for the 8-14 um LWIR band (issue #196 family).

WHY THIS EXISTS.  The radiance kernel fnc_calculateBandRadiance documents
three terms.  Until now it evaluated tau = 1, so the (1 - tau) * W_atm term
was identically zero and range had no physical effect on the apparent
radiance.  This kernel supplies tau from the path, the weather and the air.

THE FORM.  Minkina and Klecha 2016, J. Sens. Sens. Syst. 5, 17-23, Eq. (1),
give the AGEMA and LOWTRAN long-wave model as

    P_atm(d) = exp[ -alpha * (sqrt(d) - sqrt(d_cal)) - beta * (d - d_cal) ]

with d the camera-object distance in metres, d_cal the calibration distance
in metres (the paper states the calibration value of 1 m), and for the
long-wave band at 15 C and 50 percent relative humidity alpha = 0.008 and
beta = 0, both DECLARED DEFAULTS of that fit.  This kernel implements the
SQUARE-ROOT form, and not a Beer-Lambert form.  REASON: one constant
extinction coefficient cannot meet the three published anchors together.  A
Beer-Lambert fit at the 1 km anchor, beta = 0.245 km^-1, gives 0.9758 at
100 m and 0.2938 at 5000 m, against the published 0.9306 and 0.5724.  The
square-root term means the implied extinction FALLS with range, from about
0.72 km^-1 at 100 m to about 0.11 km^-1 at 5 km, so a constant beta fitted
at 1 km over-predicts attenuation at short range.  The square-root form
reproduces all three anchors to better than 1e-4:

    100 m   : exp(-0.008 * (10 - 1))       = 0.9305
    1000 m  : exp(-0.008 * (31.6228 - 1))  = 0.7827
    5000 m  : exp(-0.008 * (70.7107 - 1))  = 0.5725

HUMIDITY AND TEMPERATURE ENTER THROUGH WATER VAPOUR.  Water vapour is the
dominant absorber in this band (Roberts, Biberman and Selby 1976, IDA
P-1184, also DTIC ADA025377 and Applied Optics 15(9) 2085).  The continuum
is a two-term sum (J. Geophys. Res. 2010JD015505): the self continuum is
proportional to the SQUARE of the water vapour partial pressure e, and the
foreign continuum is proportional to e times the foreign gas pressures, so

    beta_H2O = a * e * (rho / rho0) + b * e^2

with e in torr and rho the air density.  The linear term carries rho/rho0
because the foreign continuum scales with the foreign gas pressure.  The
coefficients are DERIVED from the published Roberts range endpoints, a water
vapour extinction of 0.1 to 0.4 km^-1 over 7.9 to 11.3 um for e of 4 to 14
torr:

    4a  +  16b = 0.1   and   14a + 196b = 0.4
    a = 0.023571 km^-1/torr,  b = 3.5714e-4 km^-1/torr^2

The clean-air total also carries the carbon dioxide extinction, about
0.02 km^-1 over 8 to 12 um (same Roberts source).

TEMPERATURE IS THE SATURATION CURVE, AND THIS IS HOW IT ENTERS.  The kernel
derives e from the air temperature and the relative humidity through the
Magnus saturation curve e_s(T) = 6.112 * exp(17.67 * T / (T + 243.5)) hPa.
At a FIXED relative humidity e rises steeply with temperature, so beta_H2O
rises and transmission falls.  That is the mechanism: temperature does not
appear as a separate correction, it appears because the water vapour partial
pressure at a fixed relative humidity is a steep function of temperature.
Roberts measured a strong temperature dependence, and this kernel reproduces
its direction through the saturation curve rather than a fitted term.

ALPHA SCALES WITH THE MODELLED EXTINCTION.  The published alpha = 0.008 is a
single-condition calibration at 15 C and 50 percent relative humidity.  The
record publishes no humidity-resolved form of that coefficient, so this
kernel scales it by the ratio of the modelled clean-air extinction to the
same model evaluated at the reference condition:

    alpha_eff = alpha_ref * beta_clean(T, RH, rho) / beta_clean(15, 50, rho0)

At the reference condition the ratio is exactly 1, so alpha_eff = 0.008 and
the three published anchors hold.  Away from it the absorber column scales
the exponent.  This scaling is a DECLARED MODEL, because the record gives
the coefficient at one condition only.

FOG.  Fog droplets are about 5 to 15 um, comparable to the band wavelength,
so the extinction is in the Mie regime and is wavelength dependent (Applied
Sciences 2019, 9, 2843).  The visible Koschmieder relation beta = 3.912 / V
does NOT transfer to this band and is NOT used here.  The engine fog density
is a dimensionless 0..1 visual parameter with no published thermal-band
extinction, so the fog coefficient is a DECLARED DEFAULT, and the wavelength
dependence is an ASSUMPTION folded into that default.  It is NOT a
measurement.

RAIN.  Rain drops are 100 to 1000 um, far larger than the wavelength, so
geometric optics applies and the extinction efficiency tends to a constant
near 2.  The extinction is therefore linear in rain rate IN FORM (Radio
Science 1995, doi 10.1029/95RS01117).  The record establishes no thermal-band
coefficient, so the coefficient is a DECLARED DEFAULT and is NOT a
measurement.

FOG AND RAIN ENTER THROUGH BETA, THE PUBLISHED LINEAR TERM.  The long-wave
reference sets beta = 0 for clear air, and the (d - d_cal) term is the
linear-in-distance extinction slot of the published formula.  Fog and rain
are homogeneous extinctions linear in path, so they are the physical content
of that slot.

ISOTHERMAL PATH LIMIT.  The path radiance that a caller adds to the radiance
kernel is the Planck radiance at the air temperature.  That is the solution
of the Schwarzschild transfer equation for a HOMOGENEOUS ISOTHERMAL layer.
It is good on a near-horizontal boundary-layer path below about 1 km and it
BREAKS on a slant path, on a path that crosses a temperature inversion, and
on a multi-kilometre path.  This kernel does NOT integrate a slant path,
because the repository holds no vertical temperature profile to integrate
against, and an invented profile would be worse than a stated limit.

Guards, each explicit:
  - A path length below zero, or any non-finite input, is refused with -1.
    SQF NaN compares false against everything, so max and min cannot clamp
    it out; the refusal must come before the arithmetic.
  - A non-positive air density is refused with -1.  It is a divisor.
  - A zero-length path returns 1: no air, no absorption.
  - Relative humidity is clamped to 0..100, and fog and rain to 0..1.
  - The returned transmission is clamped to 0..1.

Units on every line: _rangeM in metres, _humidityPct in percent, _tAirC in
degrees Celsius, _fogDensity and _rainScalar dimensionless 0..1, _airDensity
in kg/m^3, e in torr, extinctions in km^-1.  The return is dimensionless.

Arguments:
  0: _rangeM      (NUMBER) path length, m, >= 0
  1: _humidityPct (NUMBER) relative humidity, percent, 0..100
  2: _tAirC       (NUMBER) air temperature, C
  3: _fogDensity  (NUMBER) engine fog density, 0..1
  4: _rainScalar  (NUMBER) engine rain scalar, 0..1
  5: _airDensity  (NUMBER) air density, kg/m^3, > 0

Return Value: NUMBER, the path transmission in 0..1, or -1 when an input is
unusable.
Example: [1000, 50, 15, 0, 0, 1.225] call aee_thermal_fnc_calculateAtmosphericTransmission
Public: No
*/

params [
    ["_rangeM", 0, [0]],
    ["_humidityPct", 50, [0]],
    ["_tAirC", 15, [0]],
    ["_fogDensity", 0, [0]],
    ["_rainScalar", 0, [0]],
    ["_airDensity", 1.225, [0]]
];

// A non-Number must not reach the arithmetic.  The typed params entries
// enforce this first, and the explicit checks keep the contract local.
if !(_rangeM isEqualType 0) exitWith { -1 };
if !(_humidityPct isEqualType 0) exitWith { -1 };
if !(_tAirC isEqualType 0) exitWith { -1 };
if !(_fogDensity isEqualType 0) exitWith { -1 };
if !(_rainScalar isEqualType 0) exitWith { -1 };
if !(_airDensity isEqualType 0) exitWith { -1 };

// A non-finite input poisons the exponent.  SQF NaN compares false against
// everything, so max and min cannot clamp it out.  Refuse before the maths.
if !(finite _rangeM) exitWith { -1 };
if !(finite _humidityPct) exitWith { -1 };
if !(finite _tAirC) exitWith { -1 };
if !(finite _fogDensity) exitWith { -1 };
if !(finite _rainScalar) exitWith { -1 };
if !(finite _airDensity) exitWith { -1 };

// A negative path has no meaning, and a non-positive density is not a gas.
if (_rangeM < 0) exitWith { -1 };
if (_airDensity <= 0) exitWith { -1 };

// A zero-length path crosses no air, so it absorbs nothing.
if (_rangeM == 0) exitWith { 1 };

// Physical clamps.  Humidity is a percentage; fog and rain are 0..1 engine
// scalars.  A value above the top is clamped, never extrapolated.
_humidityPct = _humidityPct max 0 min 100;
_fogDensity = _fogDensity max 0 min 1;
_rainScalar = _rainScalar max 0 min 1;

// ─── Published and declared constants ─────────────────────────────────────
// alpha_ref and d_cal are the Minkina and Klecha 2016 long-wave DECLARED
// DEFAULTS at 15 C and 50 percent relative humidity.
private _alphaRef = 0.008;      // per sqrt(m), published declared default
private _dCalM = 1;             // m, the paper's 1 m calibration distance
private _co2Km = 0.02;          // km^-1, Roberts 1976 CO2 over 8-12 um
private _aForeign = 0.023571;   // km^-1/torr, from the Roberts 4..14 torr endpoints
private _bSelf = 3.5714e-4;     // km^-1/torr^2, from the same two endpoints
private _rho0 = 1.225;          // kg/m^3, sea-level reference density
private _fogKm = 5.0;           // km^-1 per unit fog density, DECLARED DEFAULT
private _rainKm = 0.5;          // km^-1 per unit rain scalar, DECLARED DEFAULT
private _hPaToTorr = 0.750062;  // torr per hPa

// ─── Water vapour partial pressure, Magnus saturation curve ───────────────
// e_s(T) = 6.112 * exp(17.67 * T / (T + 243.5)) hPa (Magnus, Bolton 1980).
private _eSatHPa = 6.112 * exp (17.67 * _tAirC / (_tAirC + 243.5));
private _eTorr = _eSatHPa * (_humidityPct / 100) * _hPaToTorr;

// The same curve at the reference condition of the published alpha.
private _eSatRefHPa = 6.112 * exp (17.67 * 15 / (15 + 243.5));
private _eRefTorr = _eSatRefHPa * 0.5 * _hPaToTorr;

// ─── Clean-air extinction: two-term continuum plus carbon dioxide ─────────
private _rhoRel = _airDensity / _rho0;
private _betaClean = _co2Km + _aForeign * _eTorr * _rhoRel + _bSelf * _eTorr * _eTorr;
private _betaRef = _co2Km + _aForeign * _eRefTorr + _bSelf * _eRefTorr * _eRefTorr;

// ─── Effective square-root coefficient and the linear fog/rain extinction ─
private _alphaEff = _alphaRef * (_betaClean / _betaRef);
private _betaExtraKm = _fogKm * _fogDensity + _rainKm * _rainScalar;

// ─── Transmission ─────────────────────────────────────────────────────────
// Both path terms are clamped at the calibration distance, so a path shorter
// than d_cal cannot return a transmission ABOVE 1.
private _sqrtPart = ((sqrt _rangeM) - (sqrt _dCalM)) max 0;
private _linearPart = ((_rangeM - _dCalM) / 1000) max 0;  // m -> km
private _opticalDepth = (_alphaEff * _sqrtPart) + (_betaExtraKm * _linearPart);
private _tau = exp (0 - _opticalDepth);

_tau max 0 min 1
