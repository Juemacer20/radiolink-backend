# RadioLink Backend

Backend Python/FastAPI para orientación de radioenlaces de microondas. Calcula perfil del terreno, zona de Fresnel, azimut y ángulo de elevación entre dos torres, y permite comunicación en tiempo real entre técnicos vía WebSocket.

## Funcionalidad

- **Perfil del terreno**: consulta elevaciones reales vía Open-Elevation API (gratuita)
- **Zona de Fresnel**: calcula el radio en cada punto del perfil y detecta obstrucciones
- **Corrección de curvatura terrestre**: compensa la curvatura de la Tierra para enlaces largos
- **Azimut**: cálculo preciso Norte=0° con fórmula de rumbo geodésico
- **Ángulo de elevación**: incluyendo corrección por curvatura terrestre
- **WebSocket**: sala de comunicación entre los dos técnicos del enlace

## Stack

- Python 3.11+
- FastAPI + uvicorn
- SQLAlchemy async + SQLite (aiosqlite)
- httpx (cliente async para Open-Elevation)
- Pydantic v2

## Instalación y ejecución

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Documentación interactiva: `http://localhost:8000/docs`

## Estructura del proyecto

```
radiolink-backend/
├── main.py                  # FastAPI app, CORS, startup
├── requirements.txt
└── app/
    ├── models.py            # Pydantic models
    ├── database.py          # SQLite async
    ├── calculations.py      # Cálculos geoespaciales y de Fresnel
    ├── elevation.py         # Integración Open-Elevation API
    └── routers/
        ├── links.py         # REST endpoints
        └── ws.py            # WebSocket
```

## Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/links/analyze` | Analiza un enlace y devuelve perfil + orientaciones |
| POST | `/api/v1/links/save` | Guarda el enlace en SQLite |
| GET | `/api/v1/links/list` | Lista los enlaces guardados |
| WS | `/ws/link/{link_id}` | Comunicación en tiempo real entre técnicos |
| GET | `/health` | Healthcheck |

## Ejemplo de request

```json
POST /api/v1/links/analyze
{
  "name": "Enlace Centro-Norte",
  "tower_a": { "lat": -34.6037, "lon": -58.3816, "height_m": 25 },
  "tower_b": { "lat": -34.5500, "lon": -58.4500, "height_m": 30 },
  "frequency_ghz": 5.8,
  "profile_points": 50
}
```

## Producción — Open-Elevation local

Para no depender de la API pública (puede ser lenta):

```bash
docker run -p 8080:8080 openelevation/open-elevation
```

Luego cambiar en `app/elevation.py`:
```python
OPEN_ELEVATION_URL = "http://localhost:8080/api/v1/lookup"
```

## Parte del sistema RadioLink

Este backend es consumido por la app Android: [Juemacer20/RadioLink](https://github.com/Juemacer20/RadioLink)
