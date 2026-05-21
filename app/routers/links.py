from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime

from app.models import RadioLinkRequest, RadioLinkResponse
from app.database import RadioLinkDB, get_session
from app.calculations import (
    haversine, calculate_azimuth, calculate_elevation_angle,
    interpolate_latlng, generate_profile_points, analyze_link,
)
from app.elevation import get_elevations

router = APIRouter()


@router.post("/analyze", response_model=RadioLinkResponse)
async def analyze_radio_link(req: RadioLinkRequest):
    """Analiza un radioenlace: calcula perfil del terreno, zonas de Fresnel y orientaciones."""
    n = req.profile_points
    total_samples = n + 2

    points_latlng = [
        interpolate_latlng(
            req.tower_a.lat, req.tower_a.lon,
            req.tower_b.lat, req.tower_b.lon,
            i / (total_samples - 1),
        )
        for i in range(total_samples)
    ]

    elevations = await get_elevations(points_latlng)
    elev_a, elev_b = elevations[0], elevations[-1]

    profile = generate_profile_points(
        req.tower_a.lat, req.tower_a.lon, req.tower_a.height_m, elev_a,
        req.tower_b.lat, req.tower_b.lon, req.tower_b.height_m, elev_b,
        elevations, req.frequency_ghz, n,
    )

    analysis = analyze_link(profile)
    total_dist = haversine(req.tower_a.lat, req.tower_a.lon, req.tower_b.lat, req.tower_b.lon)

    az_a_to_b = calculate_azimuth(req.tower_a.lat, req.tower_a.lon, req.tower_b.lat, req.tower_b.lon)
    az_b_to_a = calculate_azimuth(req.tower_b.lat, req.tower_b.lon, req.tower_a.lat, req.tower_a.lon)
    el_a_to_b = calculate_elevation_angle(total_dist, elev_a, req.tower_a.height_m, elev_b, req.tower_b.height_m)

    return RadioLinkResponse(
        link_id=str(uuid4()),
        name=req.name,
        tower_a_orientation={
            "azimuth_deg": round(az_a_to_b, 2),
            "elevation_angle_deg": round(el_a_to_b, 2),
            "ground_elevation_m": round(elev_a, 1),
        },
        tower_b_orientation={
            "azimuth_deg": round(az_b_to_a, 2),
            "elevation_angle_deg": round(-el_a_to_b, 2),
            "ground_elevation_m": round(elev_b, 1),
        },
        terrain_profile=profile,
        total_distance_m=round(total_dist, 1),
        frequency_ghz=req.frequency_ghz,
        analysis=analysis,
        created_at=datetime.utcnow(),
    )


@router.post("/save")
async def save_link(req: RadioLinkRequest, db: AsyncSession = Depends(get_session)):
    """Guarda un radioenlace en la base de datos local."""
    link = RadioLinkDB(
        id=str(uuid4()), name=req.name,
        lat_a=req.tower_a.lat, lon_a=req.tower_a.lon, height_a=req.tower_a.height_m,
        lat_b=req.tower_b.lat, lon_b=req.tower_b.lon, height_b=req.tower_b.height_m,
        frequency_ghz=req.frequency_ghz,
    )
    db.add(link)
    await db.commit()
    return {"id": link.id, "name": link.name}


@router.get("/list")
async def list_links(db: AsyncSession = Depends(get_session)):
    """Lista los radioenlaces guardados."""
    result = await db.execute(select(RadioLinkDB).order_by(RadioLinkDB.created_at.desc()))
    links = result.scalars().all()
    return [
        {
            "id": l.id, "name": l.name,
            "lat_a": l.lat_a, "lon_a": l.lon_a,
            "lat_b": l.lat_b, "lon_b": l.lon_b,
            "frequency_ghz": l.frequency_ghz,
            "created_at": l.created_at,
        }
        for l in links
    ]
