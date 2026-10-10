/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AEE_CONSTANTS_HPP
#define AEE_CONSTANTS_HPP

// ── Shared physical constants ───────────────────────────────────────────────
// One definition per fact, read from here by every addon.  The source standard
// is named on each define.  Included once, from lib/script_macros.hpp, so no
// addon carries its own copy and the raw literals are gone from the SQF.

// 0 degrees Celsius in kelvin, exactly.  Source: SI base unit (kelvin),
// ISO 80000-3.
#define KELVIN_OFFSET 273.15

// ISA sea-level air density, kg/m3.  Source: ISO 2533 standard atmosphere.
#define AERO_ISA_SEA_LEVEL_DENSITY 1.225

// Standard gravity, m/s2.  Source: ISO 80000-3 / BIPM (CGPM 1901, 9.80665).
#define STANDARD_GRAVITY 9.80665

// Specific gas constant, dry air, J/(kg K).  Source: ISO 2533 standard
// atmosphere (also US Standard Atmosphere 1976).
#define R_DRY_AIR 287.05287

// Specific gas constant, water vapour, J/(kg K).  Source: ISO 2533 standard
// atmosphere (also US Standard Atmosphere 1976).
#define R_WATER_VAPOUR 461.5

// ISA sea-level pressure, Pa.  Source: ISO 2533 standard atmosphere.
#define ISA_SEA_LEVEL_PRESSURE_PA 101325

// ISA sea-level pressure, hPa (mbar).  Source: ISO 2533 standard atmosphere.
#define ISA_SEA_LEVEL_PRESSURE_HPA 1013.25

// ISA temperature lapse rate, K/m.  Source: ICAO standard atmosphere
// (Doc 7488).
#define ISA_LAPSE_RATE 0.0065

// Speed-of-sound coefficient, m/s per sqrt(K): c = 20.05 sqrt(T).  Source:
// ISO 2533 dry-air relation (sqrt(gamma R)).
#define SOUND_SPEED_COEFF 20.05

// Rec. ITU-R BT.709-6 luma coefficients (R, G, B).
#define REC709_LUMA_R 0.2126
#define REC709_LUMA_G 0.7152
#define REC709_LUMA_B 0.0722

// Swinbank (1963) clear-sky emissivity coefficient.
#define SWINBANK_CLEAR_SKY 0.0552

// Division guard for a normalisation or ratio.  Basis: a numeric floor that
// keeps a normalised quantity off zero, not a measured constant.  The
// consuming kernels document it as UNSOURCED for the same reason.
#define EPSILON 0.0001

// Nominal resting human core body temperature, C.  Source: normal core
// temperature 37 C (the physiology kernel's documented baseline).
#define BODY_TEMP_C 37

#endif
