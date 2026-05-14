from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from services.restaurant_service import RestaurantService
from services.yelp_service import YelpService

router = APIRouter()
restaurant_service = RestaurantService()
yelp_service = YelpService()

class RestaurantSearchRequest(BaseModel):
    lat: float
    lon: float
    radius: Optional[int] = 2000  # Default 2km radius


class DiscoverSource(str, Enum):
    auto = "auto"
    osm = "osm"
    yelp = "yelp"


class DiscoverRequest(BaseModel):
    lat: float
    lon: float
    radius: Optional[int] = 15000
    source: DiscoverSource = DiscoverSource.auto
    yelp_term: Optional[str] = None

class RestaurantResponse(BaseModel):
    success: bool
    restaurants: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    error: Optional[str] = None

class RestaurantDetailsResponse(BaseModel):
    success: bool
    restaurant: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/discover", response_model=RestaurantResponse)
async def discover_restaurants(request: DiscoverRequest):
    """
    Unified search: OpenStreetMap (free) or Yelp (needs YELP_API_KEY).
    `source=auto` uses Yelp when a key is configured, otherwise OSM.
    """
    use_yelp = False
    if request.source == DiscoverSource.yelp:
        use_yelp = True
    elif request.source == DiscoverSource.osm:
        use_yelp = False
    else:
        use_yelp = yelp_service.is_configured()

    radius = int(request.radius or 15000)

    if use_yelp:
        if not yelp_service.is_configured():
            raise HTTPException(
                status_code=503,
                detail="Yelp is not configured. Add YELP_API_KEY to your .env file or choose OpenStreetMap.",
            )
        try:
            rows = await yelp_service.search_restaurants(
                request.lat,
                request.lon,
                radius,
                term=request.yelp_term,
                limit=50,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return RestaurantResponse(success=True, restaurants=rows, count=len(rows))

    restaurants = await restaurant_service.find_restaurants_nearby(
        lat=request.lat,
        lon=request.lon,
        radius=radius,
    )
    restaurant_dicts: List[Dict[str, Any]] = []
    for restaurant in restaurants:
        details = await restaurant_service.get_restaurant_details(restaurant)
        restaurant_dicts.append(details)

    return RestaurantResponse(
        success=True,
        restaurants=restaurant_dicts,
        count=len(restaurant_dicts),
    )


@router.post("/nearby", response_model=RestaurantResponse)
async def find_nearby_restaurants(request: RestaurantSearchRequest):
    """Find restaurants near given coordinates"""
    try:
        restaurants = await restaurant_service.find_restaurants_nearby(
            lat=request.lat,
            lon=request.lon,
            radius=request.radius
        )

        restaurant_dicts = []
        for restaurant in restaurants:
            details = await restaurant_service.get_restaurant_details(restaurant)
            restaurant_dicts.append(details)

        return RestaurantResponse(
            success=True,
            restaurants=restaurant_dicts,
            count=len(restaurant_dicts)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding restaurants: {str(e)}")

@router.get("/nearby", response_model=RestaurantResponse)
async def find_nearby_restaurants_get(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(2000, description="Search radius in meters")
):
    """Find restaurants near given coordinates (GET method)"""
    try:
        restaurants = await restaurant_service.find_restaurants_nearby(
            lat=lat,
            lon=lon,
            radius=radius
        )

        restaurant_dicts = []
        for restaurant in restaurants:
            details = await restaurant_service.get_restaurant_details(restaurant)
            restaurant_dicts.append(details)

        return RestaurantResponse(
            success=True,
            restaurants=restaurant_dicts,
            count=len(restaurant_dicts)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding restaurants: {str(e)}")

@router.get("/details/{restaurant_name}", response_model=RestaurantDetailsResponse)
async def get_restaurant_details_by_name(restaurant_name: str):
    """Get details for a specific restaurant by name"""
    try:
        return RestaurantDetailsResponse(
            success=False,
            error="Restaurant lookup by name not implemented. Use nearby search instead."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting restaurant details: {str(e)}")
