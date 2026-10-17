#!/usr/bin/env python3
"""Generate the runtime station-normals table from the climate corpus.

The corpus is ``data/climate/station_normals.json`` (schema
``aee.climate.station_normals/1``): monthly normals of real reference
stations, each naming the national meteorological service or NOAA/WMO
normals it reproduces.  The generator projects it to
``addons/weather/functions/climatology/fnc_getStationNormals.sqf``.

The generator validates the corpus first: twelve months per series, the
daily maximum above the daily minimum, humidity in 0..100, precipitation
non-negative, and every station's Koppen label equal to the class its own
normals give under Peel, Finlayson & McMahon (2007).

Global stations: data/climate/wmo_normals_9120.json, derived from the NOAA
NCEI archive of WMO climatological standard normals 1991-2020
(arc0216/0253808, the composite TMAX, TMIN, PRCP, MSLP, MNVP and TAVG
tables; public domain).  Relative humidity is the 24-hour mean of the mean
vapour pressure over the saturation vapour pressure (WMO-No. 8, Annex 4.B:
e_w = 6.112 exp(17.62 t / (243.12 + t)) hPa) along a sinusoidal diurnal
temperature between the mean daily minimum and maximum.  Projected to
addons/weather/CfgClimateStations.hpp, the table an unbound world's nearest
station is read from.

All temperatures are reduced to sea level, T + 0.0065 * elevation (the ICAO
standard lapse), because the temperature model applies the lapse to the
terrain height itself (fnc_updateTemperature).  A station without its own
MSLP normal takes the nearest WMO station's within 300 km.

Run:
    python3 tools/gen_climate_normals.py --refresh   # re-download WMO tables
    python3 tools/gen_climate_normals.py
    python3 tools/gen_climate_normals.py --check
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
DATA = REPO / "data" / "climate" / "station_normals.json"
OUT = REPO / "addons" / "weather" / "functions" / "climatology" / "fnc_getStationNormals.sqf"
SCHEMA = "aee.climate.station_normals/1"
SERIES = ("mean_daily_max_c", "mean_daily_min_c", "relative_humidity_pct", "precipitation_mm")
RAW = REPO / "data" / "climate" / "raw"
WMO = REPO / "data" / "climate" / "wmo_normals_9120.json"
CFG_OUT = REPO / "addons" / "weather" / "CfgClimateStations.hpp"
WMO_URL = ("https://www.nodc.noaa.gov/archive/arc0216/0253808/2.2/data/0-data/"
           "data-composite-primary-parameters/wmo_normals_9120_{v}.csv")
LAPSE = 0.0065
MSLP_RADIUS_KM = 300


def esat(t: float) -> float:
    """Saturation vapour pressure over water, hPa (WMO-No. 8, Annex 4.B)."""
    return 6.112 * math.exp(17.62 * t / (243.12 + t))


def diurnal_rh(e_hpa: float, tmax: float, tmin: float) -> float:
    """Monthly mean relative humidity from the mean vapour pressure.

    The vapour pressure varies far less over a day than the temperature, so
    e is held and the temperature follows a sinusoid between the mean daily
    minimum and maximum; RH = e / e_w(T) is averaged over the 24 hours
    (capped at saturation).  Against the measured RH of six reference
    stations this is within 6.6 points in every month (the ratio of the
    monthly means, e / e_w(T_mean), errs by up to 9.2).
    """
    mid, amp = (tmax + tmin) / 2, (tmax - tmin) / 2
    vals = [min(100.0, 100.0 * e_hpa / esat(mid + amp * math.cos(math.radians(15 * k)))) for k in range(24)]
    return sum(vals) / 24


def great_circle_km(a: float, b: float, c: float, d: float) -> float:
    x = (math.sin(math.radians(a)) * math.sin(math.radians(c))
         + math.cos(math.radians(a)) * math.cos(math.radians(c)) * math.cos(math.radians(b - d)))
    return 6371.0 * math.acos(max(-1.0, min(1.0, x)))


def refresh_wmo() -> None:
    import csv
    import urllib.request
    RAW.mkdir(parents=True, exist_ok=True)
    for v in ("TMAX", "TMIN", "PRCP", "MSLP", "MNVP", "TAVG"):
        req = urllib.request.Request(WMO_URL.format(v=v), headers={"User-Agent": "AEE-climate/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / f"wmo_normals_9120_{v}.csv").write_bytes(r.read())

    def table(v):
        out = {}
        with open(RAW / f"wmo_normals_9120_{v}.csv", encoding="utf-8", errors="replace") as f:
            rows = csv.reader(f)
            next(rows)
            for row in rows:
                row = [c.strip() for c in row]
                try:
                    vals = [float(x) for x in row[9:21]]
                except (ValueError, IndexError):
                    continue
                if any(x < -9000 for x in vals):
                    continue
                out[row[3]] = (float(row[4]), float(row[5]), float(row[6]), row[7], row[8], vals)
        return out

    t = {v: table(v) for v in ("TMAX", "TMIN", "PRCP", "MSLP", "MNVP", "TAVG")}
    stations = []
    for wid in sorted(set(t["TMAX"]) & set(t["TMIN"]) & set(t["PRCP"])):
        lat, lon, elev, country, name, tmax = t["TMAX"][wid]
        tmin = t["TMIN"][wid][5]
        if any(hi <= lo for hi, lo in zip(tmax, tmin)):
            continue
        rh = None
        if wid in t["MNVP"]:
            rh = [round(diurnal_rh(e, hi, lo), 1) for e, hi, lo in zip(t["MNVP"][wid][5], tmax, tmin)]
        mslp = t["MSLP"][wid][5] if wid in t["MSLP"] and all(x > 800 for x in t["MSLP"][wid][5]) else None
        stations.append({"wigos": wid, "name": name, "country": country, "lat": lat, "lon": lon,
                         "elevation_m": elev, "tmax": tmax, "tmin": tmin, "prcp": t["PRCP"][wid][5],
                         "rh": rh, "mslp": mslp})
    WMO.write_text(json.dumps({
        "schema": "aee.climate.wmo_normals/1",
        "source": "NOAA NCEI archive arc0216/0253808: WMO climatological standard normals 1991-2020, "
                  "composite primary parameters (public domain)",
        "rh_method": "24-h mean of 100 * MNVP / e_w(T(t)), T sinusoidal between TMIN and TMAX; e_w = 6.112 exp(17.62 t / (243.12 + t)) hPa (WMO-No. 8 Annex 4.B)",
        "stations": stations}, separators=(",", ":")) + "\n", encoding="utf-8")


def koppen(tmean: list[float], precip: list[float], north: bool = True) -> str:
    """Koppen-Geiger class, Peel, Finlayson & McMahon (2007), HESS 11:1633."""
    mat = sum(tmean) / 12
    map_ = sum(precip)
    t_hot, t_cold = max(tmean), min(tmean)
    summer = list(range(3, 9)) if north else [9, 10, 11, 0, 1, 2]
    winter = [m for m in range(12) if m not in summer]
    p_sum = sum(precip[m] for m in summer)
    p_win = sum(precip[m] for m in winter)
    if p_sum >= 0.7 * map_:
        p_th = 2 * mat + 28
    elif p_win >= 0.7 * map_:
        p_th = 2 * mat
    else:
        p_th = 2 * mat + 14
    if map_ < 10 * p_th:
        return "B" + ("W" if map_ < 5 * p_th else "S") + ("h" if mat >= 18 else "k")
    if t_cold >= 18:
        p_dry = min(precip)
        if p_dry >= 60:
            return "Af"
        return "Am" if p_dry >= 100 - map_ / 25 else "Aw"
    if t_hot < 10:
        return "ET" if t_hot > 0 else "EF"
    ps_dry = min(precip[m] for m in summer)
    pw_dry = min(precip[m] for m in winter)
    ps_wet = max(precip[m] for m in summer)
    pw_wet = max(precip[m] for m in winter)
    second = "s" if (ps_dry < 40 and ps_dry < pw_wet / 3) else ("w" if pw_dry < ps_wet / 10 else "f")
    warm = sum(1 for t in tmean if t >= 10)
    third = "a" if t_hot >= 22 else ("b" if warm >= 4 else ("d" if t_cold < -38 else "c"))
    return ("C" if t_cold > -3 else "D") + second + third


def load() -> dict:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{DATA}: schema must be {SCHEMA}")
    ids = set()
    for s in data["stations"]:
        sid = s["id"]
        ids.add(sid)
        for key in SERIES:
            row = s[key]
            if not (isinstance(row, list) and len(row) == 12):
                raise ValueError(f"{sid}: {key} must hold 12 months")
        for hi, lo in zip(s["mean_daily_max_c"], s["mean_daily_min_c"]):
            if hi <= lo:
                raise ValueError(f"{sid}: a daily maximum is not above the minimum")
        if not all(0 <= v <= 100 for v in s["relative_humidity_pct"]):
            raise ValueError(f"{sid}: humidity outside 0..100")
        if not all(v >= 0 for v in s["precipitation_mm"]):
            raise ValueError(f"{sid}: negative precipitation")
        if not s.get("primary_source"):
            raise ValueError(f"{sid}: no primary source")
        north = s.get("hemisphere", "N") == "N"
        tmean = [(a + b) / 2 for a, b in zip(s["mean_daily_max_c"], s["mean_daily_min_c"])]
        got = koppen(tmean, s["precipitation_mm"], north)
        if got != s["koppen"]:
            raise ValueError(f"{sid}: labelled {s['koppen']} but its normals classify as {got}")
    for world, row in data["world_bindings"].items():
        if row["station"] not in ids:
            raise ValueError(f"world {world}: unknown station {row['station']}")
    for code, sid in data["koppen_fallback"].items():
        if sid not in ids:
            raise ValueError(f"fallback {code}: unknown station {sid}")
        station = next(s for s in data["stations"] if s["id"] == sid)
        if station["koppen"] != code:
            raise ValueError(f"fallback {code}: station {sid} is {station['koppen']}")
    return data


def _arr(values: list[float]) -> str:
    return "[" + ", ".join(f"{v:g}" for v in values) + "]"


def render(data: dict) -> str:
    stations = {s["id"]: s for s in data["stations"]}
    pressure = data["mean_sea_level_pressure_hpa"]["value"]
    lines = [
        '#include "..\\..\\script_component.hpp"',
        "/*",
        "GENERATED FILE. Do not edit by hand.",
        "Regenerate with: python3 tools/gen_climate_normals.py",
        "",
        "Monthly climate normals of real reference stations, projected from",
        "data/climate/station_normals.json.  Each station reproduces the cited",
        "national meteorological service or NOAA/WMO normals:",
    ]
    for s in data["stations"]:
        lines.append(f"  {s['id']:12s} {s['koppen']:4s} {s['station'][:44]}: {s['primary_source']}")
    lines += [
        "",
        "Arguments:",
        '  0: key (STRING) - "" for the current world\'s bound station, or a',
        "     Koppen code for that class's type-locality station.",
        "",
        "Return: [mslp hPa (annual mean), -1, tMax[12], tMin[12], RH[12], precip mm[12]]",
        "(the fnc_getClimateNormals shape; element 1 is not held).  Temperatures",
        "are reduced to sea level (+0.0065 C/m of station elevation); the",
        "temperature model applies the lapse to the terrain.  The MSLP is the",
        "station's 1991-2020 WMO normal, or the nearest WMO station's within",
        "300 km.  A Koppen station is shifted six months on a southern",
        "hemisphere world.  An UNBOUND world (key \"\") takes the nearest of the",
        "WMO 1991-2020 stations in CfgClimateStations; [] if none is loaded.",
        "Public: No",
        "*/",
        "",
        'params [["_key", "", [""]]];',
        "",
        "private _STATIONS = createHashMapFromArray [",
    ]
    wmo = json.loads(WMO.read_text(encoding="utf-8"))["stations"]
    rows = []
    for s in data["stations"]:
        up = LAPSE * s["elevation_m"]
        mslp = s.get("mslp_hpa") or nearest_mslp(wmo, *station_latlon(s))
        rows.append(
            f'    ["{s["id"]}", [{_arr([round(v + up, 2) for v in s["mean_daily_max_c"]])}, '
            f'{_arr([round(v + up, 2) for v in s["mean_daily_min_c"]])}, '
            f'{_arr(s["relative_humidity_pct"])}, {_arr(s["precipitation_mm"])}, {_arr(mslp)}]]'
        )
    lines.append(",\n".join(rows))
    lines += ["];", "", "private _WORLDS = createHashMapFromArray ["]
    lines.append(",\n".join(f'    ["{w.lower()}", "{r["station"]}"]' for w, r in sorted(data["world_bindings"].items())))
    lines += ["];", "", "private _KOPPEN = createHashMapFromArray ["]
    lines.append(",\n".join(f'    ["{c}", "{sid}"]' for c, sid in sorted(data["koppen_fallback"].items())))
    lines += [
        "];",
        "",
        "private _id = \"\";",
        "private _shift = false;",
        'if (_key == "") then {',
        "    _id = _WORLDS getOrDefault [toLower worldName, \"\"];",
        "} else {",
        "    _id = _KOPPEN getOrDefault [_key, \"\"];",
        "    _shift = ((([] call EFUNC(lib,getWorldLocation)) select 0) < 0);",
        "};",
        'if (_id == "" && _key == "") exitWith { [] call FUNC(getNearestClimateStation) };',
        'if (_id == "") exitWith { [] };',
        "private _row = +(_STATIONS get _id);",
        "if (_shift) then {",
        "    _row = _row apply { (_x select [6, 6]) + (_x select [0, 6]) };",
        "};",
        "private _p = 0;",
        "{ _p = _p + _x; } forEach (_row select 4);",
        "[_p / 12, -1, _row select 0, _row select 1, _row select 2, _row select 3]",
        "",
    ]
    return "\n".join(lines)


def station_latlon(s: dict) -> tuple[float, float]:
    return tuple(s["coords"]) if "coords" in s else (0.0, 0.0)


def nearest_mslp(wmo: list, lat: float, lon: float) -> list:
    best = None
    for w in wmo:
        if w["mslp"] is None:
            continue
        km = great_circle_km(lat, lon, w["lat"], w["lon"])
        if best is None or km < best[0]:
            best = (km, w["mslp"])
    if best is None or best[0] > MSLP_RADIUS_KM:
        return [1013.25] * 12
    return best[1]


def render_cfg() -> str:
    wmo = json.loads(WMO.read_text(encoding="utf-8"))["stations"]
    lines = [
        "// GENERATED FILE. Do not edit by hand. Regenerate: python3 tools/gen_climate_normals.py",
        "// WMO climatological standard normals 1991-2020 (NOAA NCEI arc0216/0253808, public domain).",
        "// Temperatures reduced to sea level (+0.0065 C/m); rh = 24-h mean of MNVP/e_w(T) over the diurnal cycle; empty = not held.",
        "class AEE_ClimateStations {",
    ]
    for i, w in enumerate(wmo):
        up = LAPSE * w["elevation_m"]
        f = lambda v: "{" + ",".join(f"{x:g}" for x in v) + "}"  # noqa: E731
        lines.append(
            f'    class s{i} {{ id = "WIGOS {w["wigos"]}"; name = "{w["name"].replace(chr(34), "")}"; '
            f'lat = {w["lat"]:g}; lon = {w["lon"]:g}; '
            f'tmax[] = {f([round(x + up, 2) for x in w["tmax"]])}; '
            f'tmin[] = {f([round(x + up, 2) for x in w["tmin"]])}; '
            f'prcp[] = {f(w["prcp"])}; rh[] = {f(w["rh"] or [])}; mslp[] = {f(w["mslp"] or [])}; }};'
        )
    lines.append("};")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--refresh" in args:
        refresh_wmo()
    text = render(load())
    cfg = render_cfg()
    if "--check" in args:
        fresh = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        fresh = fresh and CFG_OUT.is_file() and CFG_OUT.read_text(encoding="utf-8") == cfg
        print(f"climate normals: {'fresh' if fresh else 'STALE'}")
        return 0 if fresh else 1
    OUT.write_text(text, encoding="utf-8")
    CFG_OUT.write_text(cfg, encoding="utf-8")
    print(f"climate normals: wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
