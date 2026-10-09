//! The pure native kernels (Phase E).
//!
//! Dev-only acceleration of the AEE pure kernels.  Every function here mirrors
//! its SQF reference in `addons/`, and the coefficient table is generated from
//! that reference by `tools/gen_kernel_coefficients.py` so the two cannot
//! drift.  The SQF kernel stays the reference and the fallback: the dispatcher
//! selects the native path only when the extension was proven ready at preInit
//! and the native return is non-empty with errorCode 0.

mod coefficients;

pub use coefficients::*;

/// Station pressure (hPa) from sea-level pressure, elevation and lapse rate.
///
/// `lapse_rate` is degrees Celsius per 1000 m.  Mirrors the SQF kernel
/// `fnc_calculateStationPressure`.
#[must_use]
pub fn station_pressure(p_sea: f64, elevation: f64, lapse_rate: f64) -> f64 {
    let lapse_per_m = lapse_rate / 1000.0;
    let ratio = (1.0 - lapse_per_m * elevation / PRESSURE_T_STD).max(PRESSURE_RATIO_FLOOR);
    p_sea * ratio.powf(PRESSURE_EXPONENT)
}

/// Relative humidity (%) after the surface modifier, the diurnal coupling and
/// the overcast-or-rain saturation constraint.  Mirrors the SQF kernel
/// `fnc_calculateRelativeHumidity`.
#[must_use]
pub fn relative_humidity(
    rh_base: f64,
    surface_mod: f64,
    t_ref: f64,
    t_now: f64,
    overcast: f64,
    rain: f64,
) -> f64 {
    let mut rh = (rh_base + surface_mod).max(0.0).min(HUMIDITY_SATURATION);
    rh *= 1.0 + (t_ref - t_now) * HUMIDITY_DIURNAL_COEF;
    rh = rh.max(0.0).min(HUMIDITY_SATURATION);
    if overcast > HUMIDITY_OVERCAST_GATE || rain > 0.0 {
        rh = HUMIDITY_SATURATION;
    }
    rh.round()
}

/// Air density (kg/m3) from temperature, pressure and relative humidity.
/// Mirrors the SQF kernel `fnc_calculateAirDensityKernel`.
#[must_use]
pub fn air_density(t_c: f64, p_hpa: f64, rh: f64) -> f64 {
    let e_s = BUCK_A * ((BUCK_B - t_c / BUCK_C) * t_c / (BUCK_D + t_c)).exp();
    let e = e_s * rh / 100.0;
    let t_k = t_c + KELVIN_OFFSET;
    let t_v = t_k / (1.0 - VIRTUAL_TEMP_COEF * e / p_hpa);
    let p_pa = p_hpa * PA_PER_HPA;
    p_pa / (SPECIFIC_GAS_DRY * t_v)
}
