import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from services.restaurant_service import RestaurantService
from services.foursquare_service import FoursquareService
from services.location_service import LocationService

router = APIRouter()
restaurant_service = RestaurantService()
foursquare_service = FoursquareService()
location_service = LocationService()


class RestaurantSearchRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None
    radius: Optional[int] = 10000   # 10 km — covers Pokhara district


class RestaurantResponse(BaseModel):
    success: bool
    restaurants: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    location: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    error: Optional[str] = None


@router.post("/search", response_model=RestaurantResponse,
             summary="Search restaurants — uses Foursquare if key present, else OpenStreetMap")
async def search_restaurants(request: RestaurantSearchRequest):
    """
    Step 1 of the flow: resolve location then find restaurants.
    Priority:
      1. lat/lon provided directly
      2. Address geocoded via Nominatim
      3. IP-based detection (unreliable in Nepal — will say Kathmandu)
    """
    # ── Resolve location ──────────────────────────────────────────────────────
    location_data: Dict[str, Any] = {}

    if request.lat is not None and request.lon is not None:
        location_data = {"lat": request.lat, "lon": request.lon, "source": "manual_coords"}
    elif request.address:
        geo = await location_service.geocode_address(request.address)
        if not geo:
            raise HTTPException(status_code=400, detail=f"Could not find location: '{request.address}'")
        location_data = {**geo, "source": "address"}
    else:
        geo = await location_service.get_location_from_ip()
        if not geo:
            raise HTTPException(
                status_code=503,
                detail="Could not auto-detect location. Type your city (e.g. Pokhara)."
            )
        location_data = {**geo, "source": "ip_detection"}

    lat = location_data["lat"]
    lon = location_data["lon"]
    radius = request.radius or 10000

    # ── Fetch restaurants ─────────────────────────────────────────────────────
    restaurants: List[Dict[str, Any]] = []
    source_used = "osm"

    if foursquare_service.is_configured():
        try:
            restaurants = await foursquare_service.search_restaurants(lat, lon, radius=radius)
            if restaurants:
                source_used = "foursquare"
        except Exception as e:
            print(f"[Restaurants] Foursquare failed ({e}), falling back to OSM")

    # Fallback to OpenStreetMap — run get_restaurant_details concurrently
    if not restaurants:
        raw = await restaurant_service.find_restaurants_nearby(lat=lat, lon=lon, radius=radius)
        restaurants = list(await asyncio.gather(
            *[restaurant_service.get_restaurant_details(r) for r in raw]
        ))
        source_used = "osm"

    return RestaurantResponse(
        success=True,
        restaurants=restaurants,
        count=len(restaurants),
        location=location_data,
        source=source_used,
    )
