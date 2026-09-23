#include "..\..\script_component.hpp"

/*
Latitude-driven climate normals (issue #123 — fully dynamic biome).

Derives the 12-month climate normals from LATITUDE PHYSICS alone, with no
map name and no biome input.  This breaks the old circular chain where
temperature depended on biome and biome depended on a hardcoded map-name
table: here the annual temperature curve is driven by the sun's elevation
at the latitude (the same physics as fnc_calculateSolarRadiation), so the
climate is computed from first principles, and the biome is CLASSIFIED
from that climate by the real Köppen rules.

Model (anchored to real climatology):
  T_mean(lat) = (26 - 0.40*|lat|) + 5*maritime + 6.0*hadley + 10.0*heatRidge
  A(lat)      = (7.1 + 0.333 * |lat|) / 2     degC amplitude about the mean
  T_month(m)  = T_mean + A * sin(2*pi*(m - peak)/12)
  peak = 7 (northern hemisphere: July warmest), 1 (southern: January)

  The annual mean is NOT monotonic in latitude. The hottest annual means
  on Earth are the Sahara, Sahel and Arabian landmass at 15-25 deg, not
  the equator: Timbuktu 28.9 C, Agadez 28.1, Kidal 28.9 against about 26
  C at the equator. The heatRidge term is that landmass core, damped by
  (1 - maritime) because the ocean breaks it. Without it the model gave a
  coldest month of 16 C at 17.7 N, below the 18 C Koppen tropical gate, so
  a subtropical classification was forced on a tropical latitude.

  Diurnal range grows toward the dry subtropics and shrinks toward the
  wet tropics and the poles (a proxy for clear-sky vs cloudy/oceanic):
  day - night ~ 8 C at the equator, 13 C at 30 deg, 6 C at 60+ deg.

  Precipitation is a simple wet-season model: the wet season follows the
  warm season (thermal convection), with a dryness factor that grows away
  from the tropics.  RH is derived from precip + temperature capacity.

  Sea-level pressure ~1013 hPa (standard); cloud from humidity.

The output SHAPE matches fnc_getClimateNormals exactly:
  [P_sea, cloud, tDay[12], tNight[12], RH[12], precip[12]]
so all four consumers (temperature, humidity, fog, pressure) work
unchanged.

Input:  [_latDeg] - latitude in degrees (negative = southern)
Output: the 6-element normals array
*/

params [["_latDeg", 40, [0]], ["_waterFrac", 0.3, [0]]];

private _lat = abs _latDeg;
if (_lat > 66.5) then { _lat = 66.5; };  // clamp: poleward = polar night regime

// ─── Annual mean + amplitude from latitude ───────────────────────────────
// The base is the zonal/oceanic annual mean: about 26 C at the equator,
// falling 0.40 C/deg poleward.  It is deliberately monotonic; the landmass
// heat core below supplies the subtropical maximum.
private _tMeanBase = 26 - 0.40 * _lat;

// Maritime correction: an ocean-air mass moderates BOTH the amplitude AND
// the annual mean.  The ocean warms the winter half-year (its heat
// capacity delays cooling), so the effective mean rises with water
// fraction - this is what separates London (Cfb, mean 11) from Winnipeg
// (Dfb, mean 3) at similar latitude.  Maritime = logistic(waterFrac),
// shifting the mean up to +5 C and collapsing the amplitude ~60%.
// The threshold sits low (waterFrac 0.3 ~ fully maritime): a map with a
// third of its area water is dominated by ocean-air masses (warm-current
// climates like the British Isles have modest land fractions but strong
// maritime moderation).  The +5 C coefficient is anchored to the
// Scottish Highlands (Aviemore, 57.2 N): the latitude base 27 - 0.42*lat
// gives 3.2 C, the real annual mean is 7.7 C - a +4.5 C maritime lift at
// waterFrac ~0.35.  The earlier +4 C coefficient left the mean 1.2 C
// low, dropping high-latitude oceanic maps to Cfc instead of Cfb
// (issue #184).
private _maritime = 1 / (1 + exp (-12 * (_waterFrac - 0.22)));
// Subtropical high (Hadley cell descending branch): a sharp belt at
// ~31 N/S brings BOTH warm dry air (adiabatic warming, clear skies) and
// suppressed convection.  Without it the model cannot produce the
// world's desert belt — Cairo/Baghdad/Kandahar classify Csa instead of
// BWh (found by the CUP workshop-map rotation).  The single `hadley`
// factor drives the +6.0 C warming and the precip * (1 - 0.92*hadley)
// aridity.  It is zero at the equator, at the poles, and on maritime
// maps (the ocean breaks the high).  Cairo (30 N): +5.2 C, *0.20
// precip — real 22 C, 25 mm/yr (BWh).
private _hadley = exp (-((_lat - 31) ^ 2) / (2 * 25)) * (1 - _maritime);
// Landmass heat core.  The annual mean peaks at about 19 deg latitude on
// land, not at the equator: the Saharan/Sahel/Arabian belt is the hottest
// land on Earth (Timbuktu 28.9 C, Agadez 28.1, Kidal 28.9, against about
// 26 C at the equator).  A broad Gaussian on the LAND only, scaled by
// (1 - maritime) because the ocean breaks the core, exactly as the Hadley
// factor is.  Peaks at 10.0 C, e-folding width 8 deg: +9.1 C at 17.7 N
// where the real figure needs it, +3.6 C at 30 N, effectively zero by 45 N.
// This is what keeps the 17.7 N coldest month above the 18 C Koppen
// tropical gate.
private _heatRidge = exp (-((_lat - 19) ^ 2) / (2 * 8 ^ 2)) * (1 - _maritime);
private _tMean = _tMeanBase + 5 * _maritime + 6.0 * _hadley + 10.0 * _heatRidge;
// Annual amplitude: A(lat) is the FULL peak-to-trough range, and the sin()
// term below needs HALF that - the amplitude about the mean - so the range
// is halved here.  Feeding the full range in produced a ~2x seasonal swing
// (Enoch min -17 / max 26 vs real Minsk -6.6 / 18.5), pushing mid-latitude
// maps into Dfa instead of Dfb (issue #184).
//
// The coefficients are fitted through two real anchors: 13.0 C at 17.7 N
// (Timbuktu range 13.0, Agadez 14.0) and 25.1 C at 54 N (Minsk).  The
// earlier 1.4 + 0.405*lat gave 8.6 at 17.7 N and 23.3 at 54 N, too small
// at both ends: a tropical latitude then had a seasonality the real
// subtropics do not show.
private _ampFull = (7.1 + 0.333 * _lat) max 2.0;
private _amp = (_ampFull / 2) * (1 - 0.6 * _maritime);

// Hemisphere: peak month is July (7) north, January (1) south.
private _peakMonth = [1, 7] select (_latDeg >= 0);

// Subtropical summer heat: the Mediterranean and subtropical highs bring
// hot dry clear-sky summers.  Peaks at lat 35, fades outside 20-48.
private _summerBoost = 6 * exp (-((_lat - 35) ^ 2) / 90);

// Summer-dry regime (Mediterranean): precipitation is WINTER-peaked under
// the subtropical high.  Peaks at lat 35.
private _summerDry = exp (-((_lat - 35) ^ 2) / 70);

// Diurnal range by latitude (dry subtropics largest).
private _diurnal = 8 + 5 * exp (-((_lat - 30) ^ 2) / 250) * (1 - _lat / 90);
if (_lat < 10) then { _diurnal = 8; };

// ─── Monthly arrays ───────────────────────────────────────────────────────
private _tDay = [];
private _tNight = [];
private _precip = [];
private _RH = [];

for "_m" from 1 to 12 do {
    // Phase peaks AT the peak month: sin((m - peak + 3)/12 * 2pi) is 1
    // when m == peak (July north, January south) and -1 six months later.
    // A naive (m - peak)/12 * 2pi makes the warmest month come 3 months
    // LATE (October north) - a real bug caught by the dynamic biome tests.
    // SQF trig takes DEGREES: the phase is computed in radians (2*pi), so
    // it must be converted before sin — feeding radians straight in made
    // sin(pi/2) = sin(1.57 deg) = 0.027 instead of 1, collapsing the
    // annual cycle to near-flat and classifying high-latitude maps as
    // Tundra (issue #178).
    private _phase = (_m - _peakMonth + 3) / 12 * 2 * pi;
    private _phaseDeg = _phase * 180 / pi;
    private _tMid = _tMean + _amp * (sin _phaseDeg);
    if ((sin _phaseDeg) > 0) then { _tMid = _tMid + _summerBoost; };

    private _tD = _tMid + _diurnal / 2;
    private _tN = _tMid - _diurnal / 2;
    _tDay pushBack (round (_tD * 10) / 10);
    _tNight pushBack (round (_tN * 10) / 10);

    // Wet season: summer convection normally; INVERTED under the
    // subtropical high (Mediterranean winter rains).
    // Dry-season floor: the model's own dryness factor, not a flat 0.1.
    // A flat 10% floor overdried tropical wet seasons (Tanoa -> Am: dry
    // month 36 mm vs real Port Vila ~100 mm; Af needs driest >= 60 mm).
    // exp(-lat/25) keeps wet tropics at ~50% of wet-season rain year-round
    // (Port Vila ~179 mm) and lets genuinely dry latitudes fall low.
    private _dryness = exp (-_lat / 25);
    private _wetness = (0.5 + 0.5 * (sin _phaseDeg)) max _dryness;
    if (_summerDry > 0.3) then { _wetness = 1 - _wetness; };
    // Subtropical-high aridity: the descending branch suppresses
    // convection in the 25-38 N/S belt (Sahara, Arabian, Afghan).
    private _baseP = (60 + 90 * _dryness) * (1 + 2.5 * _maritime) * (1 - 0.92 * _hadley);
    _precip pushBack (round (_baseP * _wetness));

    // RH: high when precip high and temp low (capacity), min 30%.
    private _rhVal = ((_wetness * 70 + (1 - _wetness) * 35) min 90) max 30;
    _RH pushBack (round _rhVal);
};

// Cloud: mirrors humidity (moist = cloudy), 0.1 dry .. 0.8 wet.
private _cloud = round ((_RH select 5) / 90 * 8) / 10;
private _pSea = 1013;

[_pSea, _cloud, _tDay, _tNight, _RH, _precip]
