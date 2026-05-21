from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class TowerInput(BaseModel):
    lat: float = Field(..., description="Latitud decimal")
    lon: float = Field(..., description="Longitud decimal")
    height_m: float = Field(..., ge=0, description="Altura de antena sobre el suelo en metros")


class RadioLinkRequest(BaseModel):
    name: str
    tower_a: TowerInput
    tower_b: TowerInput
    frequency_ghz: float = Field(..., gt=0, description="Frecuencia en GHz")
    profile_points: int = Field(50, ge=10, le=200)


class TowerOrientation(BaseModel):
    azimuth_deg: float
    elevation_angle_deg: float
    ground_elevation_m: float


class TerrainPoint(BaseModel):
    distance_m: float
    latitude: float
    longitude: float
    elevation_m: float
    los_height_m: float
    fresnel_radius_m: float
    clearance_m: float
    is_obstructed: bool
    earth_curvature_correction_m: float


class LinkAnalysis(BaseModel):
    has_clear_los: bool
    obstructions_count: int
    max_obstruction_m: float
    additional_height_needed_m: float
    first_fresnel_clearance_pct: float


class RadioLinkResponse(BaseModel):
    link_id: str
    name: str
    tower_a_orientation: TowerOrientation
    tower_b_orientation: TowerOrientation
    terrain_profile: List[TerrainPoint]
    total_distance_m: float
    frequency_ghz: float
    analysis: LinkAnalysis
    created_at: datetime
