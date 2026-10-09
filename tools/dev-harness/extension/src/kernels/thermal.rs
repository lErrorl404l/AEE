//! The two-node thermal kernel (Phase E).
//!
//! Mirrors `addons/thermal/functions/solver/fnc_solveTwoNodeKernel.sqf`.  The
//! SQF kernel stays the reference and the fallback.  Pure: inputs to outputs,
//! no engine read and no engine write.  The driver resolves the material
//! properties and passes the inert conductance, the skin emissivity and the
//! skin solar absorptance as numbers.

/// The two-node core/skin solve.  Returns `(core_c, skin_c, human_core_c)`.
/// The human core temperature is zero for an inert object.
#[must_use]
#[allow(clippy::too_many_arguments)]
pub fn solve_two_node(
    t_air: f64,
    wind: f64,
    solar: f64,
    exposure: f64,
    m_core: f64,
    m_skin: f64,
    area: f64,
    l_char: f64,
    t_core0: f64,
    t_skin0: f64,
    q_gen: f64,
    orientation: &str,
    rh: f64,
    mrt_c: f64,
    is_human: bool,
    evap_on: bool,
    dt: f64,
    water_speed: f64,
    t_water: f64,
    rain: f64,
    skin_perfusion: f64,
    clo: f64,
    cond: f64,
    skin_eps: f64,
    skin_alpha: f64,
) -> (f64, f64, f64) {
    // Saturation vapour pressure (Bolton 1980), Pa.
    let psat = |t: f64| 611.2 * (17.67 * t / (t + 243.5)).exp();

    let immersed = t_water > -100.0;
    let h = if immersed {
        let shivering = is_human && (t_skin0 < 33.7) && (t_core0 < 36.8);
        if water_speed > 0.0 {
            if shivering {
                497.1 * water_speed.powf(0.65)
            } else {
                272.9 * water_speed.powf(0.5)
            }
        } else if shivering {
            54.0
        } else {
            43.0
        }
    } else if is_human {
        3.0_f64.max(8.6 * wind.max(0.1).powf(0.53))
    } else {
        let h_f = 5.7 + 3.8 * wind.max(0.0);
        let d_t = t_skin0 - t_air;
        let mut h_n = 0.0;
        if d_t > 0.0 {
            let nu: f64 = 15.89e-6;
            let pr = 0.707;
            let k_air = 0.02624;
            let beta = 1.0 / 300.0;
            let gr = 9.81 * beta * d_t.max(0.0) * l_char.powf(3.0) / nu.powf(2.0);
            let ra = gr * pr;
            let nu_c = if ra < 1000.0 {
                0.0
            } else if orientation == "vertical" {
                let den = (1.0 + (0.492 / pr).powf(9.0 / 16.0)).powf(8.0 / 27.0);
                (0.825 + 0.387 * ra.powf(1.0 / 6.0) / den).powf(2.0)
            } else if orientation == "up" {
                if ra < 1e7 {
                    0.54 * ra.powf(0.25)
                } else {
                    0.15 * ra.powf(1.0 / 3.0)
                }
            } else {
                0.27 * ra.powf(0.25)
            };
            h_n = nu_c * k_air / l_char.max(0.05);
        }
        (h_f.powf(3.0) + h_n.powf(3.0)).powf(1.0 / 3.0)
    };

    let cond_const = cond;
    let mut k_coupling = if is_human { 0.0 } else { cond };

    let t_air_k = t_air + 273.15;
    let mrt_k = mrt_c + 273.15;
    let exch_k = if immersed { t_water + 273.15 } else { t_air_k };
    let exch_mrt_k = if immersed { t_water + 273.15 } else { mrt_k };
    let sigma = 5.670_374_419e-8;
    let f_rad_area = if is_human { 0.73 } else { 1.0 };
    let q_solar = skin_alpha * solar.max(0.0) * exposure.max(0.0).min(1.0);

    let r_clo = 0.155 * clo;
    let f_a_cl = 1.0 + 0.15 * clo;
    let r_ecl = if clo > 0.0 {
        r_clo / (16.5 * 0.45)
    } else {
        0.0
    };
    let h_e = 1.0 / (1.0 / (16.5 * f_a_cl * h.max(1e-6)) + r_ecl);
    let p_a_k = psat(t_air) * rh / 1000.0;

    let mut t_cr = t_core0;
    let mut t_sk = t_skin0;
    let mut w = 0.0;
    let mut f_cl = 1.0;
    let mut alpha_c = 0.1;
    let mut t_body = 0.0;
    for _ in 1..=12 {
        if is_human {
            let warm_c = (t_cr - 36.8).max(0.0);
            let c_sig = (33.7 - t_sk).max(0.0);
            let mut m_bl = (6.3 + 200.0 * warm_c) / (1.0 + 0.5 * c_sig);
            m_bl = m_bl.min(90.0).max(0.5);
            m_bl *= skin_perfusion.max(0.0).min(1.0);
            alpha_c = 0.041_773_7 + 0.745_183_3 / (m_bl + 0.585_417);
            k_coupling = (5.28 + 4186.0 * m_bl / 3600.0) * area;
        } else {
            k_coupling = cond_const;
        }
        let p_a = psat(t_air) * rh / 133.322;
        let q_resp = if is_human {
            let m_rate = if area > 0.0 { q_gen / area } else { 0.0 };
            0.0014 * m_rate * (34.0 - t_air) + 0.0023 * m_rate * (44.0 - p_a)
        } else {
            0.0
        };
        let q_shiv = if is_human {
            let c_sig2 = (33.7 - t_sk).max(0.0);
            let c_core_sig = (36.8 - t_core0).max(0.0);
            19.4 * c_sig2 * c_core_sig
        } else {
            0.0
        };
        t_cr = t_sk + (q_gen + q_shiv * area - q_resp * area) / (k_coupling + 1e-6);
        let ts_abs = t_sk + 273.15;
        let h_r = 4.0 * f_rad_area * skin_eps * sigma * (((ts_abs + exch_mrt_k) * 0.5).powf(3.0));
        f_cl = 1.0 / (1.0 + r_clo * f_a_cl * (h + h_r));
        let conv = h * (ts_abs - exch_k) * f_cl;
        let rad = f_rad_area * skin_eps * sigma * (ts_abs.powf(4.0) - exch_mrt_k.powf(4.0)) * f_cl;
        w = 0.0;
        if is_human && evap_on {
            let t_body_now = 0.1 * t_sk + 0.9 * t_cr;
            t_body = t_body_now;
            let m_rsw =
                170.0 * (t_body_now - 36.49).max(0.0) * (((t_sk - 33.7).max(0.0)) / 10.7).exp();
            let e_rsw = 0.68 * m_rsw;
            let p_sk_k = psat(t_sk) / 1000.0;
            let e_max = (p_sk_k - p_a_k).max(0.0) * h_e;
            w = if e_max > 0.0 {
                0.06 + 0.94 * (e_rsw / e_max).min(1.0)
            } else {
                0.06
            };
            w = w.min(1.0);
        }
        if rain > 0.0 {
            w = w.max((rain / 0.3).min(1.0)).min(1.0);
        }
        let p_sk_k = psat(t_sk) / 1000.0;
        let evap = w * h_e * (p_sk_k - p_a_k).max(0.0);
        let r_sk = q_solar + k_coupling * (t_cr - t_sk) - conv - rad - evap;
        let den = f_cl * (h + 4.0 * f_rad_area * skin_eps * sigma * ts_abs.powf(3.0))
            + w * h_e * (psat(t_sk) * 4302.645 / (t_sk + 243.5).powf(2.0)) / 1000.0
            + 1e-6;
        t_sk += r_sk / den;
        t_sk = t_sk.max(t_air - 60.0).min(t_air + 500.0);
    }
    let t_core_eq = t_cr;
    let t_skin_eq = t_sk;

    // Two-node transient: two capacities, two time constants (Gagge 1986).
    let m_body = m_core + m_skin;
    let c_skin = 0.97 * alpha_c * m_body * 1000.0;
    let c_core = 0.97 * (1.0 - alpha_c) * m_body * 1000.0;
    let mut tau_sk = c_skin / ((h * area * f_cl).max(1e-6) + k_coupling);
    let mut tau_cr = c_core / k_coupling.max(1e-6);
    tau_sk = tau_sk.max(30.0).min(3600.0);
    tau_cr = tau_cr.max(30.0).min(3600.0);
    if w > 0.06 {
        tau_sk *= 1.5;
    }
    let t_skin_new = t_skin0 + (t_skin_eq - t_skin0) * (1.0 - (-dt / tau_sk).exp());
    let t_core_new = t_core0 + (t_core_eq - t_core0) * (1.0 - (-dt / tau_cr).exp());

    (t_core_new, t_skin_new, t_body)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn solve_two_node_matches_the_interpreter_vectors() {
        let (core, skin, body) = solve_two_node(
            15.0, 1.0, 500.0, 1.0, 63.0, 7.0, 1.8258, 0.15, 36.8, 33.7, 120.0, "vertical", 0.5,
            15.0, true, true, 5.0, 0.0, -273.0, 0.0, 1.0, 0.0, 1.0, 0.95, 0.7,
        );
        assert!((core - 36.723_707_531_045_07).abs() < 1e-6, "core {core}");
        assert!((skin - 35.522_571_160_031_916).abs() < 1e-6, "skin {skin}");
        assert!((body - 31.804_896_905_819_156).abs() < 1e-6, "body {body}");
    }
}
