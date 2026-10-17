#!/usr/bin/env python3
"""Build the space-weather corpus and its runtime tables from real records.

Inputs (fetched with --refresh into data/space_weather/raw/, which is not
committed; the derived corpus data/space_weather/space_weather.json is):
  * SILSO (Royal Observatory of Belgium) monthly mean and 13-month smoothed
    total sunspot number V2.0 (SN_m_tot_V2.0.csv, SN_ms_tot_V2.0.csv).
  * NOAA SWPC predicted solar cycle (predicted-solar-cycle.json).
  * GFZ Potsdam Kp index since 1932 (Kp_ap_since_1932.txt, CC BY 4.0;
    Matzka et al. 2021, Space Weather, doi:10.1029/2020SW002641).
  * NOAA NCEI GOES XRS flare reports 1976-2016 (goes-xrs-report_YYYY.txt).

Derived:
  * monthly sunspot number 1749-2149: SILSO smoothed where held, then the
    NOAA prediction, then cycles of the Hathaway, Wilson & Reichmann (1994,
    Sol. Phys. 151:177) form R(t) = a t^3 / (exp(t^2/b^2) - c), c = 0.71,
    b = 27.12 + 25.15 / (a 10^3)^(1/4) months, with the MEAN cycle length
    and MEAN maximum of the SILSO record;
  * Kp 3-hour transition matrices (28 thirds-levels) in four sunspot bins,
    counted from the GFZ record with each interval binned by that month's
    smoothed sunspot number;
  * M- and X-class flare rates per year as a * SSN^b, the Poisson maximum
    likelihood fit to the annual GOES counts against SILSO annual means
    (1975 and 2017 excluded: partial GOES coverage), and the empirical
    quantiles of class magnitude, rise and decay time.

Writes addons/weather/functions/climatology/fnc_getSpaceWeatherData.sqf.

Run:
    python3 tools/gen_space_weather.py --refresh   # fetch, derive, write
    python3 tools/gen_space_weather.py             # write from the corpus
    python3 tools/gen_space_weather.py --check
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).parents[1]
DATA = REPO / "data" / "space_weather"
RAW = DATA / "raw"
CORPUS = DATA / "space_weather.json"
OUT = REPO / "addons" / "weather" / "functions" / "climatology" / "fnc_getSpaceWeatherData.sqf"

URLS = {
    "SN_m_tot_V2.0.csv": "https://www.sidc.be/SILSO/INFO/snmtotcsv.php",
    "SN_ms_tot_V2.0.csv": "https://www.sidc.be/SILSO/INFO/snmstotcsv.php",
    "predicted-solar-cycle.json": "https://services.swpc.noaa.gov/json/solar-cycle/predicted-solar-cycle.json",
    "Kp_ap_since_1932.txt": "https://kp.gfz-potsdam.de/app/files/Kp_ap_since_1932.txt",
}
XRS = "https://www.ngdc.noaa.gov/stp/space-weather/solar-data/solar-features/solar-flares/x-rays/goes/xrs/goes-xrs-report_{y}.txt"
FIRST_YEAR, LAST_YEAR = 1749, 2149
SSN_BINS = [25, 75, 150]          # bin edges: <25, 25-75, 75-150, >=150
QUANTS = [i / 20 for i in range(21)]


def fetch(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "AEE-space-weather/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        path.write_bytes(r.read())


def refresh() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        fetch(url, RAW / name)
    for y in range(1975, 2018):
        fetch(XRS.format(y=y), RAW / f"goes-xrs-report_{y}.txt")


def silso(name: str) -> dict[tuple[int, int], float]:
    out = {}
    for row in csv.reader(open(RAW / name, encoding="utf-8"), delimiter=";"):
        v = float(row[3])
        if v >= 0:
            out[int(row[0]), int(row[1])] = v
    return out


def hathaway(t: float, a: float) -> float:
    if t <= 0:
        return 0.0
    b = 27.12 + 25.15 / (a * 1e3) ** 0.25
    x = t * t / (b * b)
    if x > 700:
        return 0.0
    return a * t ** 3 / (math.exp(x) - 0.71)


def amplitude_for_peak(peak: float) -> float:
    lo, hi = 1e-6, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        top = max(hathaway(t, mid) for t in range(1, 200))
        lo, hi = (mid, hi) if top < peak else (lo, mid)
    return (lo + hi) / 2


def cycle_stats(smoothed: dict) -> tuple[float, float, list]:
    """Mean cycle length (months) and mean maximum from the SILSO record."""
    keys = sorted(smoothed)
    vals = [smoothed[k] for k in keys]
    minima, maxima = [], []
    w = 60  # a minimum/maximum is the extreme within +/-5 years
    for i in range(w, len(vals) - w):
        win = vals[i - w:i + w + 1]
        if vals[i] == min(win) and (not minima or i - minima[-1] > 60):
            minima.append(i)
        if vals[i] == max(win) and (not maxima or i - maxima[-1] > 60):
            maxima.append(i)
    lengths = [b - a for a, b in zip(minima, minima[1:])]
    return statistics.mean(lengths), statistics.mean(vals[i] for i in maxima), [keys[i] for i in minima]


def build() -> dict:
    smoothed = silso("SN_ms_tot_V2.0.csv")
    monthly = silso("SN_m_tot_V2.0.csv")
    pred = json.loads((RAW / "predicted-solar-cycle.json").read_text(encoding="utf-8"))
    mean_len, mean_max, minima = cycle_stats(smoothed)
    series: dict[tuple[int, int], float] = dict(smoothed)
    for row in pred:
        y, m = map(int, row["time-tag"].split("-"))
        series.setdefault((y, m), float(row["predicted_ssn"]))
    last = max(series)
    # Chain mean cycles from the end of the prediction (the SC25/26 minimum).
    a = amplitude_for_peak(mean_max)
    starts = [last[0] * 12 + last[1] - 1 + k * mean_len for k in range(0, 15)]
    for y in range(FIRST_YEAR, LAST_YEAR + 1):
        for m in range(1, 13):
            if (y, m) in series:
                continue
            idx = y * 12 + m - 1
            series[y, m] = sum(hathaway(idx - s, a) for s in starts if idx > s)
    ssn_months = [round(series.get((y, m), 0.0), 1) for y in range(FIRST_YEAR, LAST_YEAR + 1) for m in range(1, 13)]

    # Kp transition counts, binned by the month's smoothed (else monthly) SSN.
    def ssn_bin(v: float) -> int:
        return sum(v >= e for e in SSN_BINS)

    counts = [[[0] * 28 for _ in range(28)] for _ in range(len(SSN_BINS) + 1)]
    prev = None
    for line in open(RAW / "Kp_ap_since_1932.txt", encoding="utf-8"):
        if line.startswith("#"):
            continue
        p = line.split()
        y, m, kp = int(p[0]), int(p[1]), float(p[7])
        if kp < 0:
            prev = None
            continue
        k = min(27, round(kp * 3))
        s = smoothed.get((y, m), monthly.get((y, m)))
        if prev is not None and s is not None:
            counts[ssn_bin(s)][prev][k] += 1
        prev = k
    kp_cum = []
    for b in counts:
        rows = []
        for i, row in enumerate(b):
            tot = sum(row)
            if tot == 0:
                row = [1 if j == i else 0 for j in range(28)]
                tot = 1
            acc, cum = 0, []
            for c in row:
                acc += c
                cum.append(round(acc / tot, 5))
            rows.append(cum)
        kp_cum.append(rows)

    # Flares.
    annual = {}
    for (y, m), v in monthly.items():
        annual.setdefault(y, []).append(v)
    per_year, mags, rise, decay = {}, {"M": [], "X": []}, {"M": [], "X": []}, {"M": [], "X": []}
    for y in range(1975, 2018):
        if y in (1975, 2017):
            continue
        cm = cx = 0
        for line in open(RAW / f"goes-xrs-report_{y}.txt", encoding="utf-8", errors="ignore"):
            mm = re.search(r"\s([BCMX])\s?(\d{1,3})\s", line[50:70])
            if not mm or mm.group(1) not in "MX":
                continue
            cls = mm.group(1)
            cm += cls == "M"
            cx += cls == "X"
            mags[cls].append(int(mm.group(2)) / 10)
            try:
                s, e, x = (int(line[13:17]), int(line[18:22]), int(line[23:27]))
                tm = lambda v: v // 100 * 60 + v % 100  # noqa: E731
                rise[cls].append((tm(x) - tm(s)) % 1440)
                decay[cls].append((tm(e) - tm(x)) % 1440)
            except ValueError:
                pass
        per_year[y] = (statistics.mean(annual[y]), cm, cx)

    def poisson_fit(idx: int) -> tuple[float, float]:
        best = None
        for bi in range(50, 300):
            b = bi / 100
            pts = [(s, v[idx]) for s, *v in [(r[0], r[1], r[2]) for r in per_year.values()]]
            S = sum(s ** b for s, _ in pts)
            K = sum(k for _, k in pts)
            a_ = K / S
            ll = sum(k * math.log(a_ * s ** b) for s, k in pts if k > 0) - a_ * S
            if best is None or ll > best[0]:
                best = (ll, a_, b)
        return best[1], best[2]

    def quantiles(vals: list[float]) -> list[float]:
        vals = sorted(vals)
        return [round(vals[min(len(vals) - 1, int(q * (len(vals) - 1)))], 2) for q in QUANTS]

    flare = {}
    for i, cls in ((0, "M"), (1, "X")):
        a_, b_ = poisson_fit(i)
        flare[cls] = {"rate_a": round(a_, 6), "rate_b": round(b_, 4), "events": len(mags[cls]),
                      "magnitude_quantiles": quantiles(mags[cls]),
                      "rise_min_quantiles": quantiles(rise[cls]),
                      "decay_min_quantiles": quantiles(decay[cls])}

    return {
        "schema": "aee.space_weather/1",
        "sources": {
            "silso": "SILSO, Royal Observatory of Belgium: total sunspot number V2.0, monthly and 13-month smoothed (CC BY-NC 4.0)",
            "noaa_prediction": "NOAA SWPC predicted solar cycle (public domain)",
            "gfz_kp": "GFZ Potsdam Kp since 1932 (CC BY 4.0; Matzka et al. 2021, doi:10.1029/2020SW002641)",
            "goes_xrs": "NOAA NCEI GOES XRS flare reports 1976-2016 (public domain)",
            "hathaway": "Hathaway, Wilson & Reichmann 1994, Sol. Phys. 151:177",
        },
        "ssn_first_year": FIRST_YEAR,
        "ssn_last_observed": "%04d-%02d" % max(smoothed),
        "ssn_last_predicted": "%04d-%02d" % last,
        "mean_cycle_months": round(mean_len, 2),
        "mean_cycle_max": round(mean_max, 1),
        "ssn_monthly": ssn_months,
        "kp_ssn_bins": SSN_BINS,
        "kp_transition_cumulative": kp_cum,
        "flares": flare,
    }


def render(c: dict) -> str:
    def arr(v) -> str:
        if isinstance(v, list):
            return "[" + ",".join(arr(x) for x in v) + "]"
        return f"{v:g}"

    f = c["flares"]
    return f'''#include "..\\..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_space_weather.py

Space-weather data from real records (data/space_weather/space_weather.json):
  sunspot number  SILSO smoothed to {c["ssn_last_observed"]}, NOAA prediction to
                  {c["ssn_last_predicted"]}, then mean Hathaway cycles (length
                  {c["mean_cycle_months"]} months, maximum {c["mean_cycle_max"]})
  Kp              GFZ 1932- transition statistics, by sunspot bin
  flares          GOES XRS 1976-2016: M {f["M"]["events"]} events, X {f["X"]["events"]}

Return: HASHMAP
  "ssnFirstYear"  first year of ssnMonthly
  "ssnMonthly"    monthly sunspot number, one per month from ssnFirstYear
  "kpBins"        sunspot bin edges
  "kpCum"         [bin][fromLevel][toLevel] cumulative transition probability,
                  levels are Kp thirds 0..27
  "flareM"/"flareX"  [rate_a, rate_b, magnitudeQ[21], riseMinQ[21], decayMinQ[21]],
                  rate per year = rate_a * SSN ^ rate_b; Q are quantiles 0..1/20
Public: No
*/

private _cached = missionNamespace getVariable [QGVAR(spaceWeatherData), nil];
if (!isNil "_cached") exitWith {{ _cached }};

private _data = createHashMapFromArray [
    ["ssnFirstYear", {c["ssn_first_year"]}],
    ["ssnMonthly", {arr(c["ssn_monthly"])}],
    ["kpBins", {arr(c["kp_ssn_bins"])}],
    ["kpCum", {arr(c["kp_transition_cumulative"])}],
    ["flareM", [{f["M"]["rate_a"]:g}, {f["M"]["rate_b"]:g}, {arr(f["M"]["magnitude_quantiles"])}, {arr(f["M"]["rise_min_quantiles"])}, {arr(f["M"]["decay_min_quantiles"])}]],
    ["flareX", [{f["X"]["rate_a"]:g}, {f["X"]["rate_b"]:g}, {arr(f["X"]["magnitude_quantiles"])}, {arr(f["X"]["rise_min_quantiles"])}, {arr(f["X"]["decay_min_quantiles"])}]]
];
missionNamespace setVariable [QGVAR(spaceWeatherData), _data];
_data
'''


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--refresh" in args:
        refresh()
        corpus = build()
        CORPUS.write_text(json.dumps(corpus, indent=1) + "\n", encoding="utf-8")
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    text = render(corpus)
    if "--check" in args:
        fresh = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        print(f"space weather: {'fresh' if fresh else 'STALE'}")
        return 0 if fresh else 1
    OUT.write_text(text, encoding="utf-8")
    f = corpus["flares"]
    print(f"space weather: wrote {OUT.relative_to(REPO)}; cycle {corpus['mean_cycle_months']} mo, "
          f"max {corpus['mean_cycle_max']}; M {f['M']['rate_a']}*SSN^{f['M']['rate_b']}, "
          f"X {f['X']['rate_a']}*SSN^{f['X']['rate_b']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
