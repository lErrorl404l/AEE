#!/usr/bin/env python3
"""
AEE Terrain Deformation Validation
===================================
Pre-validated physics tests for terrain deformation features:
- Explosion crater geometry (Hopkinson-Cranz scaling)
- Frost heave mechanics (ice lens formation)
- Erosion mass transport (conservation of mass)
- Sin^m brush hardness function

No AEE dependencies. Standalone Python validation.
All formulas sourced from published physics literature.

Usage:
    python3 validate_terrain_deformation.py
"""

import math
import sys
from typing import List, Tuple, Optional

# ============================================================================
# Constants
# ============================================================================
GRAVITY = 9.81  # m/s^2
RHO_WATER = 1000.0  # kg/m^3
RHO_ICE = 917.0  # kg/m^3
RHO_SOIL_DRY = 1600.0  # kg/m^3 (typical)
RHO_SOIL_WET = 1900.0  # kg/m^3 (typical)
FUSION_LATENT_HEAT = 334000.0  # J/kg (latent heat of fusion)


# ============================================================================
# Explosion Crater (Hopkinson-Cranz)
# ============================================================================
def crater_radius(mass_tnt_kg: float, k: float = 0.07) -> float:
    """
    Hopkinson-Cranz crater radius.
    R = K * W^(1/3)

    Source: Hopkinson (1915), Cranz (1926)
    k=0.07 for surface bursts, k=0.025 for buried charges

    Args:
        mass_tnt_kg: Charge mass in kg TNT equivalent
        k: Empirical constant (0.07 surface, 0.025 buried)
    Returns:
        Crater radius in metres
    """
    return k * (mass_tnt_kg ** (1.0 / 3.0))


def crater_depth(radius: float, depth_ratio: float = 0.5) -> float:
    """
    Crater depth from radius.
    D = ratio * R (typically 0.4-0.6 for surface bursts)

    Source: Glasstone & Dolan (1977), "Effects of Nuclear Weapons"
    """
    return depth_ratio * radius


def ejecta_rim_height(crater_depth: float, rim_ratio: float = 0.1) -> float:
    """
    Ejecta rim height from crater depth.
    H_rim = ratio * D (typically 0.05-0.15)
    """
    return rim_ratio * crater_depth


def blast_wave_overpressure(mass_tnt_kg: float, distance_m: float) -> float:
    """
    Kingery-Bulmash overpressure estimation.
    Simplified: P = 0.84 * (W^(1/3) / Z)^3
    where Z = distance / W^(1/3)

    Source: Kingery & Bulmash (1964), "Airblast Parameters"
    """
    if distance_m <= 0:
        return float("inf")
    cube_root_mass = mass_tnt_kg ** (1.0 / 3.0)
    z = distance_m / cube_root_mass
    if z < 0.1:
        return 1e6  # Very close, cap at 1 MPa
    return 0.84 * ((cube_root_mass / z) ** 3) * 1e6  # Pa


def test_crater_radius():
    """Test crater radius scales correctly with mass."""
    tests = [
        (1.0, 0.07, 0.07),  # 1 kg TNT
        (10.0, 0.07, 0.15),  # 10 kg TNT
        (100.0, 0.07, 0.32),  # 100 kg TNT
        (1000.0, 0.07, 0.70),  # 1 tonne TNT
        (10000.0, 0.07, 1.51),  # 10 tonnes TNT
        (100000.0, 0.07, 3.24),  # 100 tonnes TNT
    ]

    all_pass = True
    for mass, k, expected in tests:
        result = crater_radius(mass, k)
        error = abs(result - expected) / expected * 100
        if error > 2.0:  # 2% tolerance (empirical constant)
            print(
                f"FAIL: crater_radius({mass}, {k}) = {result:.3f}, expected {expected:.3f} ({error:.1f}% error)"
            )
            all_pass = False

    return all_pass


def test_crater_depth():
    """Test crater depth from radius."""
    r = crater_radius(1000.0)  # 1 tonne TNT
    d = crater_depth(r)
    expected = 0.5 * r
    if abs(d - expected) > 0.001:
        print(f"FAIL: crater_depth({r:.3f}) = {d:.3f}, expected {expected:.3f}")
        return False
    return True


def test_blast_overpressure():
    """Test overpressure decreases with distance."""
    mass = 100.0  # 100 kg TNT
    p1 = blast_wave_overpressure(mass, 10.0)
    p2 = blast_wave_overpressure(mass, 50.0)
    p3 = blast_wave_overpressure(mass, 100.0)

    if p1 <= p2 or p2 <= p3:
        print(f"FAIL: overpressure not decreasing: {p1:.0f} > {p2:.0f} > {p3:.0f}")
        return False

    # Check inverse cube law (approximately)
    ratio_1_2 = p1 / p2
    expected_ratio = (50.0 / 10.0) ** 3  # 125
    error = abs(ratio_1_2 - expected_ratio) / expected_ratio * 100
    if error > 10:
        print(
            f"FAIL: overpressure ratio {ratio_1_2:.1f}, expected ~{expected_ratio:.1f} ({error:.1f}% error)"
        )
        return False

    return True


# ============================================================================
# Frost Heave
# ============================================================================
def frost_susceptibility(soil_type: str) -> float:
    """
    Frost susceptibility coefficient (m/C).
    Source: Penner (1972), " frost heaving in soils"
    """
    values = {
        "gravel": 0.01,
        "sand": 0.02,
        "silt": 0.06,
        "clay": 0.04,
        "peat": 0.08,
        "loam": 0.03,
    }
    return values.get(soil_type.lower(), 0.02)


def frost_heave_amount(susceptibility: float, temp_diff: float, dt: float) -> float:
    """
    Frost heave amount.
    Δh = C_f * ΔT * dt
    where C_f = susceptibility, ΔT = temperature below 0C (positive when cold)
    """
    if temp_diff <= 0:
        return 0.0  # No heave above freezing
    return susceptibility * abs(temp_diff) * dt


def frost_thaw_settlement(heave_amount: float, settlement_ratio: float = 0.3) -> float:
    """
    Thaw settlement: terrain settles below original after thaw.
    Settlement = ratio * heave (typically 30% irreversible)

    Source: Andersland & Ladanyi (2004), "Frozen Ground Engineering"
    """
    return settlement_ratio * heave_amount


def ice_lens_growth_rate(
    temp_diff: float, moisture: float, k_ice: float = 0.001
) -> float:
    """
    Ice lens growth rate.
    Growth = k * ΔT * moisture
    Only forms when temp < 0C AND moisture > field capacity
    temp_diff: temperature below 0C (positive when cold)
    """
    if temp_diff <= 0 or moisture <= 0:
        return 0.0
    return k_ice * abs(temp_diff) * moisture


def test_frost_susceptibility():
    """Test frost susceptibility varies correctly by soil type."""
    # Silt > clay > loam > sand > gravel (as expected)
    silt = frost_susceptibility("silt")
    clay = frost_susceptibility("clay")
    sand = frost_susceptibility("sand")
    gravel = frost_susceptibility("gravel")

    if not (silt > clay > sand > gravel):
        print(
            f"FAIL: frost susceptibility order wrong: silt={silt}, clay={clay}, sand={sand}, gravel={gravel}"
        )
        return False
    return True


def test_frost_heave():
    """Test frost heave amount."""
    # Silt at -5C for 1 day should heave
    # temp_diff is positive when cold (below 0C)
    silt = frost_susceptibility("silt")
    heave_1day = frost_heave_amount(silt, 5.0, 86400)  # 1 day in seconds
    heave_7day = frost_heave_amount(silt, 5.0, 7 * 86400)

    if heave_1day <= 0:
        print(f"FAIL: frost heave should be positive, got {heave_1day}")
        return False

    if heave_7day <= heave_1day:
        print(f"FAIL: 7-day heave should exceed 1-day: {heave_7day} <= {heave_1day}")
        return False

    # Heave should be proportional to time
    ratio = heave_7day / heave_1day
    if abs(ratio - 7.0) > 0.01:
        print(f"FAIL: heave not proportional to time, ratio={ratio:.3f}, expected 7.0")
        return False

    return True


def test_thaw_settlement():
    """Test thaw settlement is partial (irreversible heave)."""
    heave = 0.01  # 10mm heave
    settlement = frost_thaw_settlement(heave, 0.3)

    # Settlement should be 30% of heave
    expected = 0.003
    if abs(settlement - expected) > 0.0001:
        print(f"FAIL: thaw settlement {settlement:.4f}, expected {expected:.4f}")
        return False

    # Net height change: heave - settlement = 0.7 * heave (irreversible)
    net_height = heave - settlement
    if abs(net_height - 0.007) > 0.0001:
        print(f"FAIL: net height change {net_height:.4f}, expected 0.007")
        return False

    return True


def test_ice_lens():
    """Test ice lens growth requires both cold and moisture."""
    # Cold + wet = growth (temp_diff positive = cold)
    rate1 = ice_lens_growth_rate(5.0, 0.5)
    if rate1 <= 0:
        print("FAIL: ice lens should grow with cold+wet conditions")
        return False

    # Warm = no growth (temp_diff negative = warm)
    rate2 = ice_lens_growth_rate(-1.0, 0.5)
    if rate2 != 0:
        print(f"FAIL: ice lens should not grow when warm, got {rate2}")
        return False

    # Dry = no growth
    rate3 = ice_lens_growth_rate(5.0, 0.0)
    if rate3 != 0:
        print(f"FAIL: ice lens should not grow when dry, got {rate3}")
        return False

    return True


# ============================================================================
# Erosion (Mass Transport)
# ============================================================================
def soil_erodibility(soil_type: str) -> float:
    """
    Soil erodibility K factor (kg*s^2/J).
    Source: Wischmeier & Smith (1978), "Predicting Rainfall Erosion Losses"
    """
    values = {
        "gravel": 0.02,
        "sand": 0.04,
        "silt": 0.12,
        "clay": 0.06,
        "loam": 0.08,
    }
    return values.get(soil_type.lower(), 0.05)


def rainfall_erosivity(rainfall_mm_h: float) -> float:
    """
    Rainfall erosivity R factor (MJ*mm/(ha*h)).
    Simplified: R = 0.048 * I^1.61

    Source: Renard & Freimund (1994)
    """
    if rainfall_mm_h <= 0:
        return 0.0
    return 0.048 * (rainfall_mm_h**1.61)


def slope_length_factor(slope_percent: float, length_m: float) -> float:
    """
    Slope length-steepness factor (LS).
    LS = (L/22.13)^m * (65.41*sin^2(s) + 4.56*sin(s) + 0.065)
    where m = 0.5 for steep slopes, s = atan(slope_percent/100)

    Source: Wischmeier & Smith (1978)
    """
    s = math.atan(slope_percent / 100.0)
    m = 0.5 if slope_percent > 5 else 0.3
    l_factor = (length_m / 22.13) ** m
    s_factor = 65.41 * math.sin(s) ** 2 + 4.56 * math.sin(s) + 0.065
    return l_factor * s_factor


def critical_shear_stress(soil_type: str) -> float:
    """
    Critical shear stress for erosion onset (Pa).
    Source: Shields (1936), refined by various authors
    """
    values = {
        "gravel": 2.0,
        "sand": 0.8,
        "silt": 0.3,
        "clay": 1.5,
        "loam": 0.6,
    }
    return values.get(soil_type.lower(), 0.5)


def stream_shear_stress(water_depth: float, slope: float) -> float:
    """
    Stream bed shear stress.
    tau = rho * g * d * S
    """
    return RHO_WATER * GRAVITY * water_depth * slope


def erosion_rate(
    shear_stress: float, critical_stress: float, k_transport: float = 0.01
) -> float:
    """
    Erosion rate from excess shear stress.
    E = k * (tau - tau_c) when tau > tau_c
    """
    if shear_stress <= critical_stress:
        return 0.0
    return k_transport * (shear_stress - critical_stress)


def mass_conservation_check(
    cells: List[Tuple[float, float]], cell_area: float, rho_soil: float
) -> bool:
    """
    Verify mass conservation: total erosion = total deposition.
    cells: list of (old_height, new_height)
    """
    total_erosion = 0.0
    total_deposition = 0.0

    for old_h, new_h in cells:
        delta = new_h - old_h
        if delta < 0:
            total_erosion += abs(delta) * cell_area * rho_soil
        else:
            total_deposition += delta * cell_area * rho_soil

    # Allow 0.1% tolerance for floating point
    if total_erosion == 0 and total_deposition == 0:
        return True

    if total_erosion == 0 or total_deposition == 0:
        return False

    error = abs(total_erosion - total_deposition) / max(total_erosion, total_deposition)
    return error < 0.001


def test_soil_erodibility():
    """Test erodibility varies correctly by soil type."""
    silt = soil_erodibility("silt")
    clay = soil_erodibility("clay")
    sand = soil_erodibility("sand")

    if not (silt > clay and silt > sand):
        print(
            f"FAIL: silt should be most erodible: silt={silt}, clay={clay}, sand={sand}"
        )
        return False
    return True


def test_rainfall_erosivity():
    """Test erosivity increases with rainfall intensity."""
    r1 = rainfall_erosivity(10.0)
    r2 = rainfall_erosivity(50.0)
    r3 = rainfall_erosivity(100.0)

    if not (r1 < r2 < r3):
        print(f"FAIL: erosivity not increasing: {r1:.3f} < {r2:.3f} < {r3:.3f}")
        return False

    # Check power law relationship
    ratio = r3 / r1
    expected = (100.0 / 10.0) ** 1.61
    error = abs(ratio - expected) / expected * 100
    if error > 5:
        print(
            f"FAIL: erosivity ratio {ratio:.1f}, expected ~{expected:.1f} ({error:.1f}% error)"
        )
        return False

    return True


def test_mass_conservation():
    """Test mass is conserved in erosion/deposition."""
    # Simulate: cell A erodes 1m, cell B deposits 1m
    cells = [(10.0, 9.0), (8.0, 9.0)]  # A loses 1m, B gains 1m
    cell_area = 25.0  # 5x5m grid
    rho = RHO_SOIL_DRY

    if not mass_conservation_check(cells, cell_area, rho):
        print("FAIL: mass conservation violated")
        return False

    # Test imbalance detection
    cells_bad = [(10.0, 9.0), (8.0, 9.5)]  # A loses 1m, B gains 0.5m
    if mass_conservation_check(cells_bad, cell_area, rho):
        print("FAIL: mass conservation should fail for imbalanced cells")
        return False

    return True


def test_stream_shear_stress():
    """Test shear stress increases with depth and slope."""
    tau1 = stream_shear_stress(0.1, 0.01)  # shallow, gentle
    tau2 = stream_shear_stress(1.0, 0.01)  # deep, gentle
    tau3 = stream_shear_stress(1.0, 0.1)  # deep, steep

    if not (tau1 < tau2 < tau3):
        print(
            f"FAIL: shear stress not increasing: {tau1:.1f} < {tau2:.1f} < {tau3:.1f}"
        )
        return False

    # Check linearity
    if abs(tau2 / tau1 - 10.0) > 0.01:
        print(f"FAIL: shear stress not proportional to depth: {tau2 / tau1:.3f}")
        return False

    return True


# ============================================================================
# Sin^m Brush Hardness (Deformer Algorithm)
# ============================================================================
def brush_hardness(distance: float, max_distance: float, m: float = 2.0) -> float:
    """
    Sin^m brush hardness function.
    ratio = 1 - (sin(90 * dist/max)) ^ m

    Used by Deformer for smooth terrain deformation edges.
    m=2: standard, m=4: soft, m=1: hard
    """
    if max_distance <= 0:
        return 0.0
    t = min(distance / max_distance, 1.0)
    return 1.0 - (math.sin(math.radians(90 * t)) ** m)


def test_brush_hardness_center():
    """Test hardness is 1.0 at center (distance=0)."""
    h = brush_hardness(0, 10.0)
    if abs(h - 1.0) > 0.001:
        print(f"FAIL: brush hardness at center = {h:.3f}, expected 1.0")
        return False
    return True


def test_brush_hardness_edge():
    """Test hardness is 0.0 at edge (distance=max)."""
    h = brush_hardness(10.0, 10.0)
    if abs(h - 0.0) > 0.001:
        print(f"FAIL: brush hardness at edge = {h:.3f}, expected 0.0")
        return False
    return True


def test_brush_hardness_monotonic():
    """Test hardness decreases monotonically from center to edge."""
    prev = 1.0
    for i in range(1, 100):
        d = i * 0.1
        h = brush_hardness(d, 10.0)
        if h > prev:
            print(
                f"FAIL: brush hardness not monotonic at d={d:.1f}: {h:.3f} > {prev:.3f}"
            )
            return False
        prev = h
    return True


def test_brush_hardness_m_values():
    """Test different m values produce expected shapes."""
    d = 5.0  # midpoint

    h_hard = brush_hardness(d, 10.0, m=1.0)  # hard edge
    h_standard = brush_hardness(d, 10.0, m=2.0)  # standard
    h_soft = brush_hardness(d, 10.0, m=4.0)  # soft edge

    # Higher m = less falloff = more material at midpoint
    if not (h_soft >= h_standard >= h_hard):
        print(
            f"FAIL: m value ordering wrong: soft={h_soft:.3f}, std={h_standard:.3f}, hard={h_hard:.3f}"
        )
        return False

    return True


# ============================================================================
# Main Test Runner
# ============================================================================
def run_tests():
    """Run all terrain deformation tests."""
    tests = [
        ("Crater Radius (Hopkinson-Cranz)", test_crater_radius),
        ("Crater Depth", test_crater_depth),
        ("Blast Overpressure", test_blast_overpressure),
        ("Frost Susceptibility", test_frost_susceptibility),
        ("Frost Heave Amount", test_frost_heave),
        ("Thaw Settlement", test_thaw_settlement),
        ("Ice Lens Growth", test_ice_lens),
        ("Soil Erodibility", test_soil_erodibility),
        ("Rainfall Erosivity", test_rainfall_erosivity),
        ("Mass Conservation", test_mass_conservation),
        ("Stream Shear Stress", test_stream_shear_stress),
        ("Brush Hardness Center", test_brush_hardness_center),
        ("Brush Hardness Edge", test_brush_hardness_edge),
        ("Brush Hardness Monotonic", test_brush_hardness_monotonic),
        ("Brush Hardness M Values", test_brush_hardness_m_values),
    ]

    passed = 0
    failed = 0

    print("=" * 70)
    print("AEE Terrain Deformation Validation")
    print("=" * 70)
    print()

    for name, test_fn in tests:
        try:
            if test_fn():
                print(f"PASS  {name}")
                passed += 1
            else:
                print(f"FAIL  {name}")
                failed += 1
        except Exception as e:
            print(f"ERROR {name}: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
