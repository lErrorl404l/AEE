//! The eye aperture and adaptation kernels (Phase E).
//!
//! Mirror the SQF kernels under `addons/optics/functions/eye/`.  The SQF
//! kernels stay the reference and the fallback.  Pure: inputs to outputs, no
//! engine read and no engine write.

/// One adaptation step for the two slow pools.  Returns `(cone, rod)`.  Each
/// pool chases the target log-luminance with its own first-order lag and uses
/// the light tau when it must brighten and its dark tau when it must darken.
#[must_use]
pub fn eye_adapt_step(
    state: &[f64],
    target_log_lum: f64,
    dt: f64,
    tau_light: f64,
    tau_dark_cone: f64,
    tau_dark_rod: f64,
    _w: f64,
) -> (f64, f64) {
    let x_cone = state.first().copied().unwrap_or(0.0);
    let x_rod = state.get(1).copied().unwrap_or(0.0);
    let tau_cone = if target_log_lum >= x_cone {
        tau_light
    } else {
        tau_dark_cone
    };
    let tau_rod = if target_log_lum >= x_rod {
        tau_light
    } else {
        tau_dark_rod
    };
    let new_cone = x_cone + (target_log_lum - x_cone) * (1.0 - (-(dt / tau_cone)).exp());
    let new_rod = x_rod + (target_log_lum - x_rod) * (1.0 - (-(dt / tau_rod)).exp());
    (new_cone, new_rod)
}

/// CIE 191:2010 mesopic photopic fraction: 0 is pure scotopic (rods), 1 is
/// pure photopic (cones).  Mirrors `fnc_eyeMesopicWeight`.
#[must_use]
pub fn eye_mesopic_weight(lum: f64, lo: f64, hi: f64) -> f64 {
    if lum <= lo {
        return 0.0;
    }
    if lum >= hi {
        return 1.0;
    }
    let t = (lum.log10() - lo.log10()) / (hi.log10() - lo.log10());
    t * t * (3.0 - 2.0 * t)
}

/// Steady-state pupil diameter (mm) for a scene luminance.  Mirrors the Moon
/// and Spencer tanh `fnc_eyePupilSteady`, clamped to [1.9, 8.0] mm.
#[must_use]
pub fn eye_pupil_steady(lum: f64) -> f64 {
    let b = lum / 3.183;
    let x = 0.4 * (b.log10() + 0.5);
    let e = (2.0 * x).exp();
    let d = 4.9 - 3.0 * ((e - 1.0) / (e + 1.0));
    d.max(1.9).min(8.0)
}

/// First-order lag on the pupil diameter (mm).  The constriction branch is
/// quicker than the redilation branch, so the tau follows the sign of the
/// error.  Mirrors `fnc_eyePupilStep`.
#[must_use]
pub fn eye_pupil_step(d: f64, d_target: f64, dt: f64, tau_constrict: f64, tau_dilate: f64) -> f64 {
    let tau = if d_target < d {
        tau_constrict
    } else {
        tau_dilate
    };
    d + (d_target - d) * (1.0 - (-(dt / tau)).exp())
}

/// True when the world clock moved by more than the threshold in one step.
/// The clock wraps at 24 h, so a delta above 12 h is read the short way round.
/// Mirrors `fnc_eyeTimeSkip`.
#[must_use]
pub fn eye_time_skip(prev_hour: f64, now_hour: f64, threshold_hours: f64) -> bool {
    if prev_hour < 0.0 {
        return false;
    }
    let mut delta = now_hour - prev_hour;
    if delta > 12.0 {
        delta -= 24.0;
    }
    if delta < -12.0 {
        delta += 24.0;
    }
    delta.abs() > threshold_hours
}
