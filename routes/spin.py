"""
/api/spin — One-shot endpoint that:
1. Detects or accepts location
2. Finds nearby restaurants
3. Runs Russian roulette to pick restaurant + food (+ drink)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from enum import Enum

from services.location_service import LocationService
from services.restaurant_service import RestaurantService
from services.decision_service import DecisionService, PreferenceType
from utils.helpers import format_distance, luck_emoji

router = APIRouter()
location_service = LocationService()
restaurant_service = RestaurantService()
decision_service = DecisionService()


class PreferenceEnum(str, Enum):
    FOOD_ONLY = "food_only"
    FOOD_AND_DRINKS = "food_and_drinks"


class SpinRequest(BaseModel):
    # Provide lat/lon manually OR leave blank to auto-detect from IP
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None          # Alternative: provide a city/address
    radius: Optional[int] = 2000           # Search radius in meters
    preference: PreferenceEnum = PreferenceEnum.FOOD_ONLY


class SpinResponse(BaseModel):
    success: bool
    location: Optional[dict] = None
    restaurant: Optional[dict] = None
    food: Optional[str] = None
    drink: Optional[str] = None
    luck_factor: Optional[float] = None
    luck_label: Optional[str] = None
    distance_label: Optional[str] = None
    total_restaurants_found: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/", response_model=SpinResponse, summary="Full roulette spin — one call does it all")
async def spin(request: SpinRequest):
    """
    The main roulette endpoint. Provide a location (or nothing for auto-detect),
    your preference (food only / food + drinks), and we pick everything for you.
    """

    # ── Step 1: Resolve location ──────────────────────────────────────────────
    location_data = None

    if request.lat is not None and request.lon is not None:
        # Manually provided coordinates
        location_data = {"lat": request.lat, "lon": request.lon, "source": "manual_coords"}

    elif request.address:
        # Geocode the address string
        location_data = await location_service.geocode_address(request.address)
        if not location_data:
            raise HTTPException(status_code=400, detail=f"Could not geocode address: '{request.address}'")
        location_data["source"] = "address"

    else:
        # Auto-detect from IP
        location_data = await location_service.get_location_from_ip()
        if not location_data:
            raise HTTPException(
                status_code=503,
                detail="Could not auto-detect location from IP. Please provide lat/lon or address."
            )
        location_data["source"] = "ip_detection"

    lat = location_data["lat"]
    lon = location_data["lon"]

    # ── Step 2: Find nearby restaurants ──────────────────────────────────────
    restaurants_raw = await restaurant_service.find_restaurants_nearby(
        lat=lat, lon=lon, radius=request.radius
    )

    if not restaurants_raw:
        return SpinResponse(
            success=False,
            location=location_data,
            error="No restaurants found in this area. Try a larger search radius or a different location.",
        )

    # Convert to dicts
    restaurant_dicts = []
    for r in restaurants_raw:
        restaurant_dicts.append(await restaurant_service.get_restaurant_details(r))

    # ── Step 3: Russian roulette decision ────────────────────────────────────
    preference = (
        PreferenceType.FOOD_AND_DRINKS
        if request.preference == PreferenceEnum.FOOD_AND_DRINKS
        else PreferenceType.FOOD_ONLY
    )

    result = await decision_service.make_decision(restaurant_dicts, preference)

    # ── Step 4: Build response ────────────────────────────────────────────────
    dist_km = result.selected_restaurant.get("distance_km")

    return SpinResponse(
        success=True,
        location=location_data,
        restaurant=result.selected_restaurant,
        food=result.selected_menu_item,
        drink=result.selected_drink,
        luck_factor=round(result.luck_factor, 3),
        luck_label=luck_emoji(result.luck_factor),
        distance_label=format_distance(dist_km),
        total_restaurants_found=len(restaurant_dicts),
        message=(
            f"🎰 The roulette chose: {result.selected_restaurant.get('name')} — "
            f"order the {result.selected_menu_item}"
            + (f" with a {result.selected_drink}!" if result.selected_drink else "!")
        ),
    )
