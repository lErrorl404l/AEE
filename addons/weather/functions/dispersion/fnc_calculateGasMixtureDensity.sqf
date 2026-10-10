#include "..\..\script_component.hpp"

/*
Dense/neutral transition from the cloud mixture density (issue #120).

The density of a cloud that holds C kg/m3 of a gas of density rho_g in air
of density rho_a follows from the volume mixing rule (per cubic metre, the
gas volume C/rho_g plus the air volume (rho_mix - C)/rho_a is one):

  rho_mix = rho_a + C * (1 - rho_a / rho_g)

so rho_mix / rho_a = 1 + (C / rho_a) * (1 - rho_a / rho_g).

The cloud behaves as a dense gas while its excess density exceeds the
DEGADIS gravity-spreading cut-off delrhomin = 0.025 (the shipped DEGADIS
default, "DELRHOMIN ... 0.025"): the dense calculation stops when
(rho_mix - rho_a) / rho_a < delrhomin.  The issue's alternative "ratio
< 1.1" threshold is not DEGADIS's and is not sourced; it is exposed here
as the deltaRhoMin argument (0.1 gives the issue's ~204 mg/m3 for
chlorine) so a caller can select it, but the default is the DEGADIS
figure.

Inverting the threshold gives the transition concentration, the gas
concentration at which the cloud becomes passive:

  C_trans = rho_a * delrhomin / (1 - rho_a / rho_g)

For chlorine at 20 C (rho_a = 1.204 kg/m3) the DEGADIS threshold gives
0.051 kg/m3 (51 g/m3); the issue's 1.1 ratio gives 0.204 kg/m3 (204
g/m3).  The issue states this figure as "204 mg/m3", a factor-1000 unit
slip; the value is 204 g/m3 (2.04e5 mg/m3).  Either is a density
transition, not a toxic endpoint.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: NUMBER - gas concentration C, kg/m3
  1: NUMBER - density ratio rho_g/rho_a (1 = neutral)
  2: NUMBER - density-excess threshold delrhomin (default 0.025, DEGADIS)

Returns:
  ARRAY [mixtureRatio rho_mix/rho_a, denseActive BOOL,
         transitionConcentration kg/m3]
*/

params [
    ["_concentration", 0, [0]],
    ["_densityRatio", 1, [0]],
    ["_deltaRhoMin", 0.025, [0]]
];

private _rhoA = 1.204;      // dry air at 20 C, ISO 2533

private _mixRatio = 1;
private _transition = 0;
if (_densityRatio > 1) then {
    _mixRatio = 1 + (_concentration / _rhoA) * (1 - 1 / _densityRatio);
    _transition = _rhoA * _deltaRhoMin / (1 - 1 / _densityRatio);
};

private _denseActive = (_mixRatio - 1) > _deltaRhoMin;

[_mixRatio, _denseActive, _transition]
