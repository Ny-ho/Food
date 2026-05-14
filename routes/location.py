from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.location_service import LocationService

router = APIRouter()
location_service = LocationService()

class LocationRequest(BaseModel):
    address: Optional[str] = None

class CoordinatesRequest(BaseModel):
    lat: float
    lon: float

class LocationResponse(BaseModel):
    success: bool
    location: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.get("/detect", response_model=LocationResponse)
async def detect_location():
    """Auto-detect user's location from IP address"""
    try:
        location = await location_service.get_location_from_ip()
        if location:
            return LocationResponse(
                success=True,
                location=location
            )
        else:
            return LocationResponse(
                success=False,
                error="Could not detect location from IP"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting location: {str(e)}")

@router.post("/geocode", response_model=LocationResponse)
async def geocode_address(request: LocationRequest):
    """Convert address to coordinates"""
    if not request.address:
        raise HTTPException(status_code=400, detail="Address is required")
    
    try:
        location = await location_service.geocode_address(request.address)
        if location:
            return LocationResponse(
                success=True,
                location=location
            )
        else:
            return LocationResponse(
                success=False,
                error="Could not geocode address"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error geocoding address: {str(e)}")

@router.post("/reverse-geocode", response_model=LocationResponse)
async def reverse_geocode(request: CoordinatesRequest):
    """Convert coordinates to address"""
    try:
        address_info = await location_service.reverse_geocode(request.lat, request.lon)
        if address_info:
            return LocationResponse(
                success=True,
                location=address_info
            )
        else:
            return LocationResponse(
                success=False,
                error="Could not reverse geocode coordinates"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reverse geocoding: {str(e)}")
