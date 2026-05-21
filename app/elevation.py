import httpx
from typing import List, Tuple

OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"
# Para produccion: docker run -p 8080:8080 openelevation/open-elevation
# y cambiar la URL a http://localhost:8080/api/v1/lookup


async def get_elevations(points: List[Tuple[float, float]]) -> List[float]:
    """
    Obtiene elevaciones SNMM para una lista de (lat, lon) via Open-Elevation API.
    Fallback a 0m si la API no responde (permite calcular igual con terreno plano).
    """
    locations = [{"latitude": lat, "longitude": lon} for lat, lon in points]

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                OPEN_ELEVATION_URL,
                json={"locations": locations},
            )
            response.raise_for_status()
            data = response.json()
        return [float(r["elevation"]) for r in data["results"]]
    except Exception:
        return [0.0] * len(points)
