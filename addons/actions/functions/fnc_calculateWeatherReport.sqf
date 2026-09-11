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

_report
