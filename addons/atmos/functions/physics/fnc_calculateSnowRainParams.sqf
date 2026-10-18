#include "..\..\script_component.hpp"

/*
The RainParticles parameter array that draws snow (pure).

Element order and meaning are the `rainParams` order the command DB lists
(acemod/arma3-wiki v2.22, commands/rainParams.yml):

   0  rainDropTexture      9  dropHeight
   1  texDropCount        10  dropColor
   2  minRainDensity      11  lumSunFront
   3  effectRadius        12  lumSunBack
   4  windCoef            13  refractCoef
   5  dropSpeed           14  refractSaturation
   6  rndSpeed            15  snow
   7  rndDir              16  dropColorStrong
   8  dropWidth

The values are the snow example the setRain page carries (commands/setRain.yml,
the `BIS_fnc_setRain` example, Arma 3 2.10): the shipped 4-flake snowflake
atlas, a slow fall and the snow flag set.  The DB names three textures and the
matching drop counts (`snowflake4_ca.paa` with 4, `snowflake8_ca.paa` with 8,
`snowflake16_ca.paa` with 16).  This kernel uses the 4-flake atlas.

Arguments: None
Return Value: ARRAY - the 17-element RainParticles parameter array
Example: private _params = call aee_atmos_fnc_calculateSnowRainParams;
Public: No
*/

[
    "a3\data_f\snowflake4_ca.paa",   //  0 rainDropTexture (4 flakes per sprite)
    4,                               //  1 texDropCount
    0.01,                            //  2 minRainDensity
    25,                              //  3 effectRadius
    0.05,                            //  4 windCoef
    2.5,                             //  5 dropSpeed
    0.5,                             //  6 rndSpeed
    0.5,                             //  7 rndDir
    0.07,                            //  8 dropWidth
    0.07,                            //  9 dropHeight
    [1, 1, 1, 0.5],                  // 10 dropColor
    0.0,                             // 11 lumSunFront
    0.2,                             // 12 lumSunBack
    0.5,                             // 13 refractCoef
    0.5,                             // 14 refractSaturation
    true,                            // 15 snow
    false                            // 16 dropColorStrong
]
