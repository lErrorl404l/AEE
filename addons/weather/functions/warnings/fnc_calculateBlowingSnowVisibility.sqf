#include "..\..\script_component.hpp"

/*
Blowing-snow transport and eye-level visibility (issue #106).

The model follows the published chain for a snow surface: the threshold
wind speed, the friction velocity, the saltation flux, the suspended
fraction of that flux, and finally the visibility the suspension causes.

THRESHOLD WIND SPEED (Li and Pomeroy 1997a).  The threshold at 10 m is a
function of air temperature alone:

  U_t10 = 6.9 + 0.0033 * (T_a + 27.27)^2       T_a in Celsius

Cold dry snow is mobile and warm wet snow is not, so the threshold rises
with temperature.  The paper gives 6.9 m/s at -27.3 C and 9.4 m/s at 0 C.

FRICTION VELOCITY.  The logarithmic wind profile relates the 10 m wind to
the friction velocity:

  u* = U_10 * kappa / ln(10 / z0)              kappa = 0.4

The roughness length z0 for snow lies in 0.0001 to 0.01 m.  This function
takes z0 as an argument and defaults to 0.001 m, the middle of that band.
At the 6.9 m/s threshold and z0 = 0.001 m the profile gives u*_t = 0.30
m/s, the Clifton et al. (2006) value the issue quotes, so the default is
the value that reproduces the issue's own friction-velocity anchor.

SALTATION FLUX (Pomeroy and Gray 1990).  The saltation stream carries most
of the mass and feeds the suspension:

  Q_salt = 0.68 * (rho_a / g) * u*_t * (u*^2 - u*_t^2)     kg/m/s

The flux is zero unless u* exceeds u*_t.  The saltation layer height is

  h_salt = 0.8 * u*^2 / g

which is 2 cm at u* = 0.5 m/s.

SUSPENSION.  The issue divides the transport into creep, saltation (75 to
80 per cent of the mass) and suspension, and the suspension alone controls
eye-level visibility.  This function takes the suspended share of the
saltation flux as its last argument and defaults to 0.20, the lower bound
of the 0.20 to 0.25 range the issue states.  The share is a MODELLING
CHOICE, not a measured constant, and it is exposed so a caller can test
the range.

VISIBILITY (Li and Pomeroy 1997b):

  V_km = 0.027 / Q_susp                        Q_susp in kg/m/s

The result is turned into the 0 to 1 intensity the FX layer consumes.  The
mapping is a MODELLING CHOICE anchored on the issue's visibility states:
10 km light onset, 1 km, 0.5 km, and 0.1 km whiteout.

Koschmieder 1924 relates the visibility to the extinction coefficient,
sigma = 3.912 / V_km, and that value is returned for the optical layer.

Args:
  0: wind speed at 10 m (NUMBER, m/s, default 0)
  1: air temperature (NUMBER, Celsius, default -5)
  2: roughness length z0 (NUMBER, metres, default 0.001)
  3: air density (NUMBER, kg/m3, default 1.225)
  4: suspended share of the saltation flux (NUMBER, 0..1, default 0.20)

Returns a HashMap with the keys:
  thresholdWind    U_t10, m/s
  uStar            friction velocity, m/s
  uStarThreshold   u*_t, m/s
  saltationFlux    Q_salt, kg/m/s
  suspensionFlux   Q_susp, kg/m/s
  saltationHeight  h_salt, m
  visibilityKm     V, km (300 when there is no transport)
  extinctionPerKm  sigma, km^-1 (Koschmieder)
  state            "none" / "light" / "moderate" / "heavy" / "whiteout"
  intensity        0..1, for the FX layer
*/

params [
    ["_wind", 0, [0]],
    ["_temp", -5, [0]],
    ["_z0", 0.001, [0]],
    ["_rhoA", 1.225, [0]],
    ["_suspShare", 0.20, [0]]
];

private _kappa = 0.4;
private _g = 9.81;

// The logarithmic profile denominator.  A zero or negative z0 would make
// the logarithm undefined, so the ends of the snow band are the bounds.
private _profile = ln (10 / ((_z0 max 0.0001) min 0.01));

private _uStar = _wind * _kappa / _profile;

// Li and Pomeroy 1997a.
private _thresholdWind = 6.9 + 0.0033 * ((_temp + 27.27) ^ 2);
private _uStarThreshold = _thresholdWind * _kappa / _profile;

// Pomeroy and Gray 1990.  No transport below the threshold.
private _qSalt = 0;
if (_uStar > _uStarThreshold) then {
    _qSalt = 0.68 * (_rhoA / _g) * _uStarThreshold * ((_uStar ^ 2) - (_uStarThreshold ^ 2));
};

private _qSusp = _qSalt * (_suspShare max 0 min 1);

// The saltation layer height, 2 cm at u* = 0.5 m/s.
private _hSalt = 0.8 * (_uStar ^ 2) / _g;

// Li and Pomeroy 1997b.  With no transport the air is clear, and the mod's
// other visibility code uses 300 km as its clear-air ceiling.
private _visKm = 300;
if (_qSusp > 0) then { _visKm = 0.027 / _qSusp; };

// The issue's states.  Whiteout is a sub-state of heavy, so it is tested
// last and overrides.
private _state = "none";
if (_visKm < 10) then { _state = "light"; };
if (_visKm < 1) then { _state = "moderate"; };
if (_visKm < 0.5) then { _state = "heavy"; };
if (_visKm < 0.1) then { _state = "whiteout"; };

// Intensity for the FX layer, anchored on the state boundaries above.
// The branches are mutually exclusive and their endpoints meet, so the
// curve is continuous: a jump here would show as a flicker in the weather
// FX as visibility crossed a band. Each band maps to its own slice of
// 0..1, and the slices are contiguous by construction.
private _intensity = 0;
private _heavyTop = 0.7;    // intensity where the heavy band begins
if (_visKm < 10 && _visKm >= 1) then {
    // light: 10 km -> 0.0, 1 km -> 0.4
    _intensity = 0.4 * (10 - _visKm) / 9;
} else {
    if (_visKm < 1 && _visKm >= 0.5) then {
        // moderate: 1 km -> 0.4, 0.5 km -> 0.7
        _intensity = 0.4 + (0.3 * (1 - _visKm) / 0.5);
    } else {
        if (_visKm < 0.5 && _visKm >= 0.1) then {
            // heavy: 0.5 km -> 0.7, 0.1 km -> 1.0
            _intensity = _heavyTop + (0.3 * (0.5 - _visKm) / 0.4);
        } else {
            if (_visKm < 0.1) then {
                // whiteout: nothing visible, full intensity
                _intensity = 1.0;
            };
        };
    };
};
_intensity = _intensity max 0 min 1;

// Koschmieder 1924.
private _extinction = 3.912 / _visKm;

createHashMapFromArray [
    ["thresholdWind", _thresholdWind],
    ["uStar", _uStar],
    ["uStarThreshold", _uStarThreshold],
    ["saltationFlux", _qSalt],
    ["suspensionFlux", _qSusp],
    ["saltationHeight", _hSalt],
    ["visibilityKm", _visKm],
    ["extinctionPerKm", _extinction],
    ["state", _state],
    ["intensity", _intensity]
]
