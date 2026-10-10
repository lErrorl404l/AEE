//! The ballistic drag kernel (Phase E).
//!
//! Mirrors `addons/ballistics/functions/fnc_calculateBallisticDrag.sqf`.  The
//! SQF kernel stays the reference and the fallback.  The standard drag table
//! is generated from the same SQF source by `tools/gen_kernel_drag_tables.py`.
//! Pure: inputs to outputs, no engine read and no engine write.

use super::drag_tables::DRAG_TABLES;

/// 0.5 * rho0 * pi * (0.0254)^2 / (4 * 0.453592) at rho0 = 1.225 kg/m3, which
/// converts the lb/in^2 coefficient convention to SI.  Matches the SQF kernel.
const SI_CONVERSION: f64 = 0.000_684_18;

/// The standard drag table for a model name, or `None` when the name is
/// unknown.  The name is matched upper-case, as the SQF kernel upper-cases it.
#[must_use]
fn standard_table(model: &str) -> Option<&'static [(f64, f64)]> {
    DRAG_TABLES
        .iter()
        .find(|(name, _)| *name == model)
        .map(|(_, points)| *points)
}

/// Linear interpolation of the Cd(Mach) table with clamped ends.  Mirrors the
/// SQF kernel's `linearConversion [m0, m1, mach, c0, c1, true]` lookup.
#[must_use]
fn interpolate(table: &[(f64, f64)], mach: f64) -> f64 {
    let first = table[0];
    let last = table[table.len() - 1];
    if mach <= first.0 {
        return first.1;
    }
    if mach >= last.0 {
        return last.1;
    }
    for window in table.windows(2) {
        let (m0, c0) = window[0];
        let (m1, c1) = window[1];
        if mach >= m0 && mach <= m1 {
            let t = (mach - m0) / (m1 - m0);
            return c0 + t * (c1 - c0);
        }
    }
    last.1
}

/// Drag retardation (m/s^2, positive is deceleration) from the ballistic
/// coefficient, velocity, drag-model name, relative air density and air
/// temperature.  Mirrors the SQF kernel `fnc_calculateBallisticDrag`.
#[must_use]
pub fn calculate_ballistic_drag(
    bc: f64,
    velocity: f64,
    drag_model: &str,
    rho_rel: f64,
    air_temp_c: f64,
) -> f64 {
    if bc <= 0.0 || velocity <= 0.0 {
        return 0.0;
    }
    let model = drag_model.to_uppercase();
    let Some(table) = standard_table(&model) else {
        return 0.0;
    };
    if table.is_empty() {
        return 0.0;
    }
    // The local speed of sound, not a fixed 340 m/s, or the transonic band is
    // misplaced: a = 20.05 * sqrt(T + 273.15).
    let sound = 20.05 * (air_temp_c + 273.15).sqrt();
    let mach = velocity / sound;
    let cd = interpolate(table, mach);
    SI_CONVERSION * (cd / bc) * (velocity * velocity) * rho_rel
}
