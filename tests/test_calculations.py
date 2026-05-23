"""
Tests para app/calculations.py — funciones puras, sin I/O.
Todos los valores esperados se derivan analíticamente o se verifican
contra referencias geoespaciales conocidas.
"""
import math
import pytest
from app.calculations import (
    haversine,
    calculate_azimuth,
    calculate_elevation_angle,
    earth_curvature_correction,
    fresnel_radius_1st,
    interpolate_latlng,
    generate_profile_points,
    analyze_link,
)

# ── haversine ────────────────────────────────────────────────────────────────

def test_haversine_same_point():
    assert haversine(0, 0, 0, 0) == pytest.approx(0.0)

def test_haversine_equator_1deg():
    # 1 grado de longitud en el ecuador ≈ 111.320 km
    d = haversine(0, 0, 0, 1)
    assert d == pytest.approx(111_320, rel=0.01)

def test_haversine_meridian_1deg():
    # 1 grado de latitud a lo largo de un meridiano ≈ 111.195 km
    d = haversine(0, 0, 1, 0)
    assert d == pytest.approx(111_195, rel=0.01)

def test_haversine_symmetric():
    d1 = haversine(-30.5, -57.9, -31.2, -58.4)
    d2 = haversine(-31.2, -58.4, -30.5, -57.9)
    assert d1 == pytest.approx(d2, rel=1e-9)

def test_haversine_positive():
    assert haversine(10, 20, 11, 21) > 0

# ── calculate_azimuth ────────────────────────────────────────────────────────

def test_azimuth_due_north():
    az = calculate_azimuth(0, 0, 1, 0)
    assert az == pytest.approx(0.0, abs=0.01)

def test_azimuth_due_south():
    az = calculate_azimuth(0, 0, -1, 0)
    assert az == pytest.approx(180.0, abs=0.01)

def test_azimuth_due_east():
    az = calculate_azimuth(0, 0, 0, 1)
    assert az == pytest.approx(90.0, abs=0.01)

def test_azimuth_due_west():
    az = calculate_azimuth(0, 0, 0, -1)
    assert az == pytest.approx(270.0, abs=0.01)

def test_azimuth_in_range():
    az = calculate_azimuth(-30.5, -57.9, -31.0, -58.2)
    assert 0.0 <= az < 360.0

def test_azimuth_northeast():
    az = calculate_azimuth(0, 0, 1, 1)
    assert 0 < az < 90

# ── calculate_elevation_angle ────────────────────────────────────────────────

def test_elevation_angle_flat_same_height():
    # Torres al mismo nivel y misma elevación del terreno → ≈ 0°
    angle = calculate_elevation_angle(1000, 100, 10, 100, 10)
    assert angle == pytest.approx(0.0, abs=0.1)

def test_elevation_angle_uphill():
    # Torre B 100 m más alta → ángulo positivo
    angle = calculate_elevation_angle(1000, 100, 10, 200, 10)
    assert angle > 0

def test_elevation_angle_downhill():
    angle = calculate_elevation_angle(1000, 200, 10, 100, 10)
    assert angle < 0

def test_elevation_angle_zero_distance():
    angle = calculate_elevation_angle(0, 100, 10, 100, 10)
    assert angle == 0.0

def test_elevation_angle_curvature_lowers_far_tower():
    # A gran distancia la curvatura terrestre hace que B parezca más bajo
    d = 50_000  # 50 km
    # Torres idénticas, sin curvatura el ángulo sería 0; con curvatura < 0
    angle = calculate_elevation_angle(d, 100, 10, 100, 10)
    assert angle < 0

# ── earth_curvature_correction ───────────────────────────────────────────────

def test_curvature_midpoint_symmetry():
    # En el punto medio d1 == d2, el valor es máximo
    c = earth_curvature_correction(500, 500)
    assert c == pytest.approx(500 * 500 / (2 * 6_371_000), rel=1e-6)

def test_curvature_zero_at_endpoints():
    assert earth_curvature_correction(0, 1000) == 0.0
    assert earth_curvature_correction(1000, 0) == 0.0

def test_curvature_increases_with_distance():
    c1 = earth_curvature_correction(500, 500)
    c2 = earth_curvature_correction(5000, 5000)
    assert c2 > c1

def test_curvature_10km_midpoint():
    # A 10 km de distancia total, punto medio: ≈ 1.96 m
    c = earth_curvature_correction(5000, 5000)
    assert c == pytest.approx(1.96, abs=0.05)

# ── fresnel_radius_1st ───────────────────────────────────────────────────────

def test_fresnel_zero_when_endpoint():
    assert fresnel_radius_1st(0.06, 0, 1000) == 0.0
    assert fresnel_radius_1st(0.06, 1000, 0) == 0.0

def test_fresnel_positive():
    # 5 GHz → λ ≈ 0.06 m, d1=d2=500 m
    r = fresnel_radius_1st(0.06, 500, 500)
    assert r > 0

def test_fresnel_5ghz_1km_midpoint():
    # λ = c/f = 3e8 / 5e9 = 0.06 m; d1=d2=500 m
    # F1 = sqrt(0.06 * 500 * 500 / 1000) = sqrt(15) ≈ 3.87 m
    r = fresnel_radius_1st(0.06, 500, 500)
    assert r == pytest.approx(math.sqrt(15), rel=0.001)

def test_fresnel_larger_at_midpoint_than_off_center():
    # El radio de Fresnel es máximo en el punto medio
    r_mid = fresnel_radius_1st(0.06, 500, 500)
    r_off = fresnel_radius_1st(0.06, 200, 800)
    assert r_mid > r_off

def test_fresnel_higher_freq_smaller_radius():
    # Mayor frecuencia → menor longitud de onda → menor radio de Fresnel
    lam_5ghz  = 3e8 / 5e9
    lam_10ghz = 3e8 / 10e9
    r5  = fresnel_radius_1st(lam_5ghz, 500, 500)
    r10 = fresnel_radius_1st(lam_10ghz, 500, 500)
    assert r5 > r10

# ── interpolate_latlng ───────────────────────────────────────────────────────

def test_interpolate_fraction_0():
    lat, lon = interpolate_latlng(1, 2, 3, 4, 0.0)
    assert lat == pytest.approx(1.0)
    assert lon == pytest.approx(2.0)

def test_interpolate_fraction_1():
    lat, lon = interpolate_latlng(1, 2, 3, 4, 1.0)
    assert lat == pytest.approx(3.0)
    assert lon == pytest.approx(4.0)

def test_interpolate_fraction_half():
    lat, lon = interpolate_latlng(0, 0, 10, 10, 0.5)
    assert lat == pytest.approx(5.0)
    assert lon == pytest.approx(5.0)

# ── generate_profile_points ──────────────────────────────────────────────────

def _flat_elevations(n):
    return [100.0] * n

def test_generate_profile_count():
    elev = _flat_elevations(12)  # num_points=10 → total_samples=12
    pts = generate_profile_points(
        -30.5, -57.9, 10, 100,
        -30.6, -58.0, 10, 100,
        elev, 5.0, 10,
    )
    assert len(pts) == 12

def test_generate_profile_first_point_distance_zero():
    elev = _flat_elevations(12)
    pts = generate_profile_points(
        -30.5, -57.9, 10, 100,
        -30.6, -58.0, 10, 100,
        elev, 5.0, 10,
    )
    assert pts[0]["distance_m"] == pytest.approx(0.0)

def test_generate_profile_keys():
    elev = _flat_elevations(12)
    pts = generate_profile_points(
        -30.5, -57.9, 10, 100,
        -30.6, -58.0, 10, 100,
        elev, 5.0, 10,
    )
    expected_keys = {
        "distance_m", "latitude", "longitude", "elevation_m",
        "los_height_m", "fresnel_radius_m", "clearance_m",
        "is_obstructed", "earth_curvature_correction_m",
    }
    assert expected_keys.issubset(pts[0].keys())

def test_generate_profile_no_obstruction_flat_terrain():
    # Terreno plano, antenas altas → sin obstrucción
    elev = _flat_elevations(12)
    pts = generate_profile_points(
        0, 0, 50, 100,
        0, 0.01, 50, 100,
        elev, 5.0, 10,
    )
    assert all(not p["is_obstructed"] for p in pts)

# ── analyze_link ─────────────────────────────────────────────────────────────

def test_analyze_link_clear():
    # Todos los puntos con clearance positivo → enlace libre
    pts = [
        {"distance_m": 0,    "clearance_m": 10, "is_obstructed": False},
        {"distance_m": 500,  "clearance_m": 5,  "is_obstructed": False},
        {"distance_m": 1000, "clearance_m": 10, "is_obstructed": False},
    ]
    result = analyze_link(pts)
    assert result["has_clear_los"] is True
    assert result["obstructions_count"] == 0
    assert result["max_obstruction_m"] == pytest.approx(0.0)

def test_analyze_link_obstructed():
    pts = [
        {"distance_m": 0,    "clearance_m": 10,  "is_obstructed": False},
        {"distance_m": 500,  "clearance_m": -3.5, "is_obstructed": True},
        {"distance_m": 1000, "clearance_m": 10,  "is_obstructed": False},
    ]
    result = analyze_link(pts)
    assert result["has_clear_los"] is False
    assert result["obstructions_count"] == 1
    assert result["max_obstruction_m"] == pytest.approx(3.5)

def test_analyze_link_empty():
    result = analyze_link([])
    assert result["has_clear_los"] is True
    assert result["obstructions_count"] == 0

def test_analyze_link_single_point():
    pts = [{"distance_m": 0, "clearance_m": 5, "is_obstructed": False}]
    result = analyze_link(pts)
    assert result["has_clear_los"] is True

def test_analyze_link_fresnel_pct_all_clear():
    pts = [
        {"distance_m": 0,    "clearance_m": 10, "is_obstructed": False},
        {"distance_m": 250,  "clearance_m": 8,  "is_obstructed": False},
        {"distance_m": 500,  "clearance_m": 6,  "is_obstructed": False},
        {"distance_m": 750,  "clearance_m": 8,  "is_obstructed": False},
        {"distance_m": 1000, "clearance_m": 10, "is_obstructed": False},
    ]
    result = analyze_link(pts)
    assert result["first_fresnel_clearance_pct"] == pytest.approx(100.0)
