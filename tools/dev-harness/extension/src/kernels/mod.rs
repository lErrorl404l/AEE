//! The pure native kernels (Phase E).
//!
//! Dev-only acceleration of the AEE pure kernels.  Every function here mirrors
//! its SQF reference in `addons/`, and the coefficient table is generated from
//! that reference by `tools/gen_kernel_coefficients.py` so the two cannot
//! drift.  The SQF kernel stays the reference and the fallback: the dispatcher
//! selects the native path only when the extension was proven ready at preInit
//! and the native return is non-empty with errorCode 0.

mod coefficients;
mod drag;
mod drag_tables;
mod eye;
mod thermal;

pub use coefficients::*;
pub use drag::*;
pub use eye::*;
pub use thermal::*;

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

/// Relative humidity (%) at the current temperature from the day's vapour
/// pressure, e = RH_mean/100 * e_w(T_mean), RH = 100 e / e_w(T_now) (WMO-No. 8
/// Magnus). Mirrors the SQF kernel `fnc_calculateRelativeHumidity`.
#[must_use]
pub fn relative_humidity(rh_mean: f64, t_mean: f64, t_now: f64) -> f64 {
    let e = rh_mean.max(0.0).min(HUMIDITY_SATURATION) / 100.0
        * HUMIDITY_MAGNUS_A
        * (HUMIDITY_MAGNUS_B * t_mean / (HUMIDITY_MAGNUS_C + t_mean)).exp();
    let ew = HUMIDITY_MAGNUS_A * (HUMIDITY_MAGNUS_B * t_now / (HUMIDITY_MAGNUS_C + t_now)).exp();
    (100.0 * e / ew).max(0.0).min(HUMIDITY_SATURATION).round()
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
