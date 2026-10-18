#include "..\..\script_component.hpp"

/*
Vegetation / foliage density (0-1), the canopy cover a concealment, sound or
shading consumer sees.

    foliage = coverMax(biome) * phenology(biome, month, station normals)

COVER MAX.  The measured mean leaf area index of the biome, turned into a
cover fraction by the Beer-Lambert canopy law, cover = 1 - exp(-k * LAI),
with the extinction coefficient k = 0.5 of a spherical leaf-angle
distribution (Monsi & Saeki 1953).  The LAI values are the post-outlier
means of Table 6 of Scurlock, Asner & Gower (2001), "Worldwide Historical
Estimates of Leaf Area Index, 1932-2000", ORNL/TM-2001/268: about 1000
published field estimates from nearly 400 sites.

    Koppen          ORNL class                 LAI    cover
    Af, Am          tropical evergreen broad   4.78   0.908
    Aw              tropical deciduous broad   3.92   0.859
    BSh, BSk        grassland                  1.71   0.575
    Csa, Csb        shrub                      2.08   0.646
    Cfa,Cfb,Cwa,
    Dfa, Dfb        temperate deciduous broad  5.06   0.920
    Dfc             boreal evergreen needle    2.65   0.734
    ET              tundra                     1.88   0.609
    EF              ice, no vegetation         -      0

    BWh, BWk        desert                     -      0.01

The desert row does NOT use the ORNL desert LAI (1.31): that figure is the
canopy of the vegetated patch and rests on six observations the report
itself flags as under-represented, so at landscape scale it would read far
too green.  It takes instead the measured landscape cover of hyper-arid
desert, under 1 per cent (NatureServe, Hyper-arid Desert Ecobiome).

PHENOLOGY.  Three published phenologies, each driven by the map's own
station normals (fnc_getClimateNormals), never by a hard-coded month row:

  - EVERGREEN (Af, Am, Dfc, ET): leaf cover does not cycle, phenology 1.

  - SUMMERGREEN (Cfa, Cfb, Cwa, Dfa, Dfb), two published halves:

    Leaf-out is the LPJ model (Sitch and others 2003, Global Change Biology
    9:161; LPJ-GUESS and CLM-DGVM technical descriptions): leaf cover rises
    linearly with the growing degree days accumulated on a 5 C base,
    reaching the year's maximum at GDD5 = 200 for a woody summergreen type.
    The degree days run from the month after the station's own coldest one,
    so the accumulator resets on the station's winter and carries no
    calendar month or hemisphere.

    Leaf-off is the White, Thornton & Running (1997) continental phenology
    model, Global Biogeochemical Cycles 11(2):217-234, eq. 6, fitted to
    satellite-observed offset at eight deciduous broadleaf sites: offset
    when daylength <= 655 min AND temperature <= 11.15 C, or whenever
    temperature <= 2.0 C.  The paper's temperature is a daily soil
    temperature; this kernel passes the station's monthly mean air
    temperature, which a monthly mean soil temperature tracks closely.
    The daylength is the sunrise equation at the map's latitude with the
    Cooper (1969) declination, so it needs no table either.

  - RAINGREEN (Aw, BSh, BSk, Csa, Csb): green in the wet months, brown in
    the dry ones.  A month is dry in the Bagnouls & Gaussen (1957) sense
    when P (mm) < 2 T (C).  The canopy is the mean of this month and the
    previous one, because green-up and browning take weeks.  A fully dry
    station month still keeps the standing dry-season canopy, the LPJ
    raingreen minimum leaf cover.

The station is local, so its hemisphere and its wet season are its own, and
no month row needs a hemisphere shift.

Stored in GVAR(currentFoliageDensity) for use by concealment
modifiers, sound-propagation, and visual-seasonal systems.
*/

private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
if (isNil "_biome" || _biome == "") then { _biome = "Cfb"; };

private _calMonthIdx = ((date select 1) - 1) max 0 min 11; // 0-based

// ─── Cover maximum: Beer-Lambert on the measured biome LAI (see header) ────
private _coverMax = switch (_biome) do {
    case "Af";
    case "Am":  { 0.908 };
    case "Aw":  { 0.859 };
    case "BWh";
    case "BWk": { 0.01 };
    case "BSh";
    case "BSk": { 0.575 };
    case "Csa";
    case "Csb": { 0.646 };
    case "Cfa";
    case "Cfb";
    case "Cwa";
    case "Dfa";
    case "Dfb": { 0.920 };
    case "Dfc": { 0.734 };
    case "ET":  { 0.609 };
    case "EF":  { 0 };
    default     { 0.920 };
};

// ─── Phenology class ───────────────────────────────────────────────────────
private _raingreen = _biome in ["Aw", "BSh", "BSk", "Csa", "Csb"];
private _summergreen = _biome in ["Cfa", "Cfb", "Cwa", "Dfa", "Dfb"];

private _phenology = 1;

if (_raingreen || _summergreen) then {
    private _normals = [_biome] call FUNC(getClimateNormals);
    private _haveNormals = (count _normals) >= 6
        && {(count (_normals select 2)) == 12}
        && {(count (_normals select 3)) == 12}
        && {(count (_normals select 5)) == 12};

    if (_haveNormals) then {
        // Monthly mean air temperature from the station's own normals.
        private _meanT = {
            params ["_m"];
            (((_normals select 2) select _m) + ((_normals select 3) select _m)) / 2
        };

        if (_summergreen) then {
            private _tNow = [_calMonthIdx] call _meanT;

            // Daylength at the middle of this month: the sunrise equation
            // with the Cooper (1969) declination, in minutes.
            private _lat = ([] call EFUNC(lib,getWorldLocation)) select 0;
            if !(_lat isEqualType 0) then { _lat = 45; };
            private _doy = (([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334] select _calMonthIdx)
                + ([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] select _calMonthIdx) / 2);
            private _dec = 23.44 * (sin (360 * (284 + _doy) / 365));
            private _cosH = -((tan _lat) * (tan _dec));
            private _daylMin = switch (true) do {
                case (_cosH <= -1): { 1440 };
                case (_cosH >= 1):  { 0 };
                default             { 8 * (acos _cosH) };   // (2/15) h = 8 min per deg
            };

            // White, Thornton & Running (1997) eq. 6: the leaves are off.
            private _off = ((_daylMin <= 655) && (_tNow <= 11.15)) || (_tNow <= 2.0);

            if (_off) then {
                _phenology = 0;
            } else {
                // LPJ leaf-out: degree days on a 5 C base from the month
                // after the station's coldest, full cover at GDD5 = 200.
                private _coldest = 0;
                for "_m" from 1 to 11 do {
                    if (([_m] call _meanT) < ([_coldest] call _meanT)) then { _coldest = _m; };
                };
                private _gdd5 = 0;
                private _m = (_coldest + 1) mod 12;
                private _guard = 0;
                while { _guard < 12 } do {
                    private _days = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] select _m;
                    _gdd5 = _gdd5 + ((([_m] call _meanT) - 5) max 0) * _days;
                    if (_m == _calMonthIdx) exitWith {};
                    _m = (_m + 1) mod 12;
                    _guard = _guard + 1;
                };
                _phenology = (_gdd5 / 200) min 1;
            };
        } else {
            // Raingreen: Bagnouls & Gaussen wet months, smoothed over the
            // present month and the one before it.
            private _wet = {
                params ["_m"];
                parseNumber (((_normals select 5) select _m) >= (2 * ([_m] call _meanT)))
            };
            _phenology = (([_calMonthIdx] call _wet) + ([(_calMonthIdx + 11) mod 12] call _wet)) / 2;
            // LPJ raingreen keeps a minimum leaf cover through the dry season.
            _phenology = _phenology max 0.1;
        };
    };
};

private _foliage = ((_coverMax * _phenology) max 0) min 1;
missionNamespace setVariable [QGVAR(currentFoliageDensity), _foliage];
