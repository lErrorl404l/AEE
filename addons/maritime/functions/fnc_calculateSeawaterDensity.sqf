#include "..\script_component.hpp"
/*
Linear seawater equation of state (issue #17).

The two-layer internal-wave model needs the density difference between the
warm upper layer and the cold lower layer.  The full UNESCO/IAPSO equation
of state is too heavy for the tick, so this uses the standard linear EOS
about a reference state:

    rho(T, S) = rho0 * (1 - alpha * (T - T0) + beta * (S - S0))

  rho0  reference density at (T0, S0)
  alpha thermal expansion coefficient, per degC
  beta  haline contraction coefficient, per psu
  T0, S0 reference temperature and salinity

Sources:
  Gill (1982) Atmosphere-Ocean Dynamics, Academic Press, section 3.7 (the
    linear equation of state).
  UNESCO EOS-80 (Millero and Poisson 1981, Deep-Sea Research 28:625;
    UNESCO 1983) for the coefficients at S = 35: thermal expansion 1.0e-4
    per degC at 4 degC and 1.7e-4 at 10 degC, haline contraction 7.6e-4 per
    psu at 10 degC.
  Reference state rho0 = 1027.8 kg/m3 at T0 = 4 degC, S0 = 35 psu, the
    EOS-80 seawater density at the deep-ocean temperature.

The linear form is an approximation: the true thermal expansion coefficient
is temperature-dependent, 1.0e-4 per degC at 4 degC and 2.6e-4 at 20 degC,
so a single alpha is a stated simplification.  The value 1.7e-4 is the
mid-range figure at about 10 degC.  The density DIFFERENCE it produces is
what the internal-wave model uses, and that difference is what the
two-layer speed depends on.

Input:  [_tempC, _salinityPsu, _rho0, _alpha, _beta, _t0, _s0]
Output: density in kg/m3
*/

params [
    ["_tempC", 15, [0]],
    ["_salinityPsu", 35, [0]],
    ["_rho0", 1027.8, [0]],
    ["_alpha", 1.7e-4, [0]],
    ["_beta", 7.6e-4, [0]],
    ["_t0", 4, [0]],
    ["_s0", 35, [0]]
];

_rho0 * (1 - _alpha * (_tempC - _t0) + _beta * (_salinityPsu - _s0))
