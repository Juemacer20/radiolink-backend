import math
from typing import List, Tuple

EARTH_RADIUS_M = 6_371_000
SPEED_OF_LIGHT = 3e8


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos coordenadas GPS."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_azimuth(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Azimut de punto 1 hacia punto 2 en grados (0-360, Norte=0)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def calculate_elevation_angle(
    total_dist_m: float,
    elev_a: float, ant_h_a: float,
    elev_b: float, ant_h_b: float,
) -> float:
    """Angulo de elevacion en grados desde Torre A a Torre B con correccion de curvatura."""
    if total_dist_m == 0:
        return 0.0
    top_a = elev_a + ant_h_a
    top_b = elev_b + ant_h_b
    # La curvatura terrestre hace que B se vea aparentemente mas bajo
    earth_curvature = (total_dist_m ** 2) / (2 * EARTH_RADIUS_M)
    apparent_top_b = top_b - earth_curvature
    return math.degrees(math.atan2(apparent_top_b - top_a, total_dist_m))


def interpolate_latlng(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    fraction: float,
) -> Tuple[float, float]:
    """Interpolacion lineal entre dos coordenadas GPS."""
    return (lat1 + (lat2 - lat1) * fraction, lon1 + (lon2 - lon1) * fraction)


def earth_curvature_correction(d1: float, d2: float) -> float:
    """Correccion de curvatura terrestre en metros en un punto intermedio."""
    return (d1 * d2) / (2 * EARTH_RADIUS_M)


def fresnel_radius_1st(wavelength: float, d1: float, d2: float) -> float:
    """Radio de la primera zona de Fresnel en metros."""
    total = d1 + d2
    if total == 0:
        return 0.0
    return math.sqrt(wavelength * d1 * d2 / total)


def generate_profile_points(
    lat_a: float, lon_a: float, ant_h_a: float, elev_a: float,
    lat_b: float, lon_b: float, ant_h_b: float, elev_b: float,
    elevations: List[float],
    frequency_ghz: float,
    num_points: int,
) -> List[dict]:
    """
    Genera el perfil completo del terreno entre las dos torres.
    Incluye analisis de zona de Fresnel y curvatura terrestre.
    """
    total_dist = haversine(lat_a, lon_a, lat_b, lon_b)
    wavelength = SPEED_OF_LIGHT / (frequency_ghz * 1e9)

    top_a = elev_a + ant_h_a
    top_b = elev_b + ant_h_b

    points = []
    total_samples = num_points + 2

    for i in range(total_samples):
        fraction = i / (total_samples - 1)
        d1 = total_dist * fraction
        d2 = total_dist - d1

        lat, lon = interpolate_latlng(lat_a, lon_a, lat_b, lon_b, fraction)
        terrain_elev = elevations[i]

        los_h = top_a + (top_b - top_a) * fraction
        f_radius = fresnel_radius_1st(wavelength, d1, d2) if (d1 > 0 and d2 > 0) else 0.0
        curv = earth_curvature_correction(d1, d2)

        # Margen libre: 60% de Fresnel libre es el minimo aceptable
        clearance = (los_h - 0.6 * f_radius) - (terrain_elev + curv)
        is_obstructed = (clearance < 0) and (0 < fraction < 1)

        points.append({
            "distance_m": round(d1, 1),
            "latitude": round(lat, 7),
            "longitude": round(lon, 7),
            "elevation_m": round(terrain_elev, 1),
            "los_height_m": round(los_h, 1),
            "fresnel_radius_m": round(f_radius, 1),
            "clearance_m": round(clearance, 1),
            "is_obstructed": is_obstructed,
            "earth_curvature_correction_m": round(curv, 2),
        })

    return points


def analyze_link(profile_points: List[dict]) -> dict:
    """Sintetiza el analisis de obstrucciones del perfil."""
    if len(profile_points) < 2:
        return {
            "has_clear_los": True, "obstructions_count": 0,
            "max_obstruction_m": 0.0, "additional_height_needed_m": 0.0,
            "first_fresnel_clearance_pct": 100.0,
        }

    total_dist = profile_points[-1]["distance_m"]
    interior = [p for p in profile_points if 0 < p["distance_m"] < total_dist]
    obstructed = [p for p in interior if p["is_obstructed"]]
    max_obs = max((abs(p["clearance_m"]) for p in obstructed), default=0.0)

    if interior:
        clear_count = sum(1 for p in interior if p["clearance_m"] >= 0)
        fresnel_pct = (clear_count / len(interior)) * 100
    else:
        fresnel_pct = 100.0

    return {
        "has_clear_los": len(obstructed) == 0,
        "obstructions_count": len(obstructed),
        "max_obstruction_m": round(max_obs, 1),
        "additional_height_needed_m": round(max_obs, 1),
        "first_fresnel_clearance_pct": round(fresnel_pct, 1),
    }
