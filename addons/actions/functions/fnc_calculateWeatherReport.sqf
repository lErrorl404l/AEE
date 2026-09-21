#include "..\script_component.hpp"

/*
Player-facing weather intel — a structured text string for "check weather"
actions. Reads all current AEE and ACE weather state and formats into a
readable block.

Returns: string (do NOT setVariable — return value only).
*/

// ─── Read inputs with isNil guards ────────────────────────────────────────
private _T      = EGVAR(core,currentTemperature);
private _P      = EGVAR(core,currentPressure);
private _RH     = EGVAR(core,currentHumidity);
private _windDir = missionNamespace getVariable [QEGVAR(core,currentWindDir), 0];

if (isNil "_T")      then { _T = 20; };
if (isNil "_P")      then { _P = 1018; };
if (isNil "_RH")     then { _RH = 50; };
if (isNil "_windDir") then { _windDir = 0; };

private _windSpeed = vectorMagnitude wind;
private _windKMH = round (_windSpeed * 3.6);

// Compass direction
private _dirNames = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                     "S","SSW","SW","WSW","W","WNW","NW","NNW"];
private _dirIdx = round (_windDir / 22.5) % 16;
private _dirStr = _dirNames select _dirIdx;

// AEE state
private _biome = EGVAR(core,biome);
if (isNil "_biome") then { _biome = "Unknown"; };

private _forecast   = missionNamespace getVariable [QEGVAR(core,currentWeatherForecast),  ""];
private _ground     = missionNamespace getVariable [QEGVAR(core,groundState),            "Normal"];
private _fireRisk   = missionNamespace getVariable [QEGVAR(core,currentFireRisk),        0];
private _lightning  = missionNamespace getVariable [QEGVAR(core,currentLightningRisk),   0];
private _uv         = missionNamespace getVariable [QEGVAR(core,currentUVIndex),         0];
private _cropDens   = missionNamespace getVariable [QEGVAR(core,currentCropDensity),     0.3];
private _waterLevel = missionNamespace getVariable [QEGVAR(core,currentWaterLevel),      0];
private _floodRisk  = missionNamespace getVariable [QEGVAR(core,currentFloodRisk),       "None"];

// Cold-weather state (issue #83: wire computed outputs into the report)
private _coldCat    = missionNamespace getVariable [QEGVAR(core,coldDangerCategory),     ""];
private _windChill  = missionNamespace getVariable [QEGVAR(core,windChillTemp),          _T];
private _dext       = missionNamespace getVariable [QEGVAR(core,dexterityPercent),       100];
private _frostbite  = missionNamespace getVariable [QEGVAR(core,frostbiteMinutes),       -1];

// Hazard state
private _avalanche  = missionNamespace getVariable [QEGVAR(core,currentAvalancheRisk),   0];
private _flashFlood = missionNamespace getVariable [QEGVAR(environmental,flashFloodRisk),0];
private _precipPh   = missionNamespace getVariable [QEGVAR(core,precipitationPhase),     ""];
private _snowRate   = missionNamespace getVariable [QEGVAR(core,snowfallRate),           0];
private _icing      = missionNamespace getVariable [QEGVAR(core,currentIcingSeverity),   0];

// Sea state and tide
private _beaufort   = missionNamespace getVariable [QEGVAR(core,seaStateBeaufort),       -1];
private _waveH      = missionNamespace getVariable [QEGVAR(core,waveHeight_m),           0];
private _tideDesc   = missionNamespace getVariable [QEGVAR(core,currentTideDescription), ""];
private _tideOff    = missionNamespace getVariable [QEGVAR(core,currentTideOffset_m),    0];

// Atmosphere
private _qnh        = missionNamespace getVariable [QEGVAR(core,qnh),                    _P];
private _preAlt     = missionNamespace getVariable [QEGVAR(core,pressureAltitude_m),     -1];
private _haze       = missionNamespace getVariable [QEGVAR(core,currentHaze),            0];

// ─── Derived labels ────────────────────────────────────────────────────────
private _fireStr = switch (true) do {
    case (_fireRisk >= 0.8): { "Extreme" };
    case (_fireRisk >= 0.5): { "High" };
    case (_fireRisk >= 0.2): { "Moderate" };
    default                  { "Low" };
};

private _uvStr = switch (true) do {
    case (_uv >= 8): { "Very High" };
    case (_uv >= 6): { "High" };
    case (_uv >= 3): { "Moderate" };
    default          { "Low" };
};

private _lightningStr = switch (true) do {
    case (_lightning >= 0.6): { "Severe" };
    case (_lightning >= 0.3): { "Moderate" };
    case (_lightning > 0):    { "Low" };
    default                   { "None" };
};

private _avalancheStr = switch (true) do {
    case (_avalanche >= 0.7): { "Severe" };
    case (_avalanche >= 0.4): { "Moderate" };
    default                   { "Low" };
};

private _flashFloodStr = switch (true) do {
    case (_flashFlood >= 0.7): { "Severe" };
    case (_flashFlood >= 0.4): { "Moderate" };
    default                    { "Low" };
};

private _icingStr = switch (true) do {
    case (_icing >= 0.7): { "Severe" };
    case (_icing >= 0.4): { "Moderate" };
    default              { "Low" };
};

private _hazeStr = switch (true) do {
    case (_haze >= 0.8): { "Heavy" };
    case (_haze >= 0.5): { "Moderate" };
    default             { "Light" };
};

// ─── Format ────────────────────────────────────────────────────────────────
private _report = "=== Weather Report ===" + "\n";
_report = _report + "Temp: " + str (round _T) + "°C" + "\n";
_report = _report + "Humidity: " + str (round _RH) + "%" + "\n";
_report = _report + "Wind: " + str _windKMH + " km/h from " + _dirStr + "\n";
_report = _report + "Pressure: " + str (round _P) + " hPa";

if (_forecast != "") then {
    _report = _report + " (" + _forecast + ")";
};
_report = _report + "\n";

_report = _report + "UV Index: " + str (round _uv) + " (" + _uvStr + ")" + "\n";
_report = _report + "Lightning: " + _lightningStr + "\n";
_report = _report + "Ground: " + _ground + "\n";
_report = _report + "Fire Risk: " + _fireStr + "\n";
_report = _report + "Crop Density: " + str (round (_cropDens * 100)) + "%" + "\n";
_report = _report + "Water Level: " + str (round (_waterLevel * 1000) / 10) + "%  Risk: " + _floodRisk;

// Cold-weather line (only when the cold model reports a category)
if (_coldCat != "") then {
    _report = _report + "\n";
    _report = _report + "Cold: " + _coldCat + "  Wind Chill: " + str (round _windChill) + "°C";
    if (_dext < 90) then {
        _report = _report + "  Dexterity: " + str (round _dext) + "%";
    };
    if (_frostbite >= 0) then {
        _report = _report + "  Frostbite in ~" + str (round _frostbite) + " min";
    };
};

// Sea state line
if (_beaufort >= 0) then {
    _report = _report + "\n";
    _report = _report + "Sea State: " + str _beaufort + " Beaufort";
    if (_waveH > 0) then { _report = _report + "  Waves: " + str (round (_waveH * 10) / 10) + " m"; };
    if (_tideDesc != "") then {
        _report = _report + "  Tide: " + _tideDesc + " (" + str (round (_tideOff * 100) / 100) + " m)";
    };
};

// Altimetry line
if (_qnh != _P || _preAlt >= 0) then {
    _report = _report + "\n";
    _report = _report + "QNH: " + str (round _qnh) + " hPa";
    if (_preAlt >= 0) then { _report = _report + "  Pressure Alt: " + str (round _preAlt) + " m"; };
};

// Hazard line (avalanche, flash flood, icing, precipitation phase)
private _hazards = [];
if (_avalanche > 0.3)  then { _hazards pushBack (format ["Avalanche %1", _avalancheStr]); };
if (_flashFlood > 0.3) then { _hazards pushBack (format ["Flash Flood %1", _flashFloodStr]); };
if (_icing > 0.3)      then { _hazards pushBack (format ["Icing %1", _icingStr]); };
if (_precipPh != "" && _precipPh != "rain") then { _hazards pushBack _precipPh; };
if (_snowRate > 0)       then { _hazards pushBack (format ["Snowfall %1 mm/h", str (round (_snowRate * 100) / 100)]); };
if (_haze > 0.5)         then { _hazards pushBack (format ["Haze %1", _hazeStr]); };
if (_hazards isNotEqualTo []) then {
    _report = _report + "\n";
    _report = _report + "Hazards: " + (_hazards joinString ", ");
};

_report
