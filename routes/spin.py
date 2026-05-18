"""
/api/spin — One-shot endpoint: location → restaurants → roulette pick.
Useful for quick CLI / API testing without going through the UI.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from enum import Enum

from services.location_service import LocationService
from services.restaurant_service import RestaurantService
from services.foursquare_service import FoursquareService
from services.decision_service import DecisionService, PreferenceType
from utils.helpers import format_distance, luck_emoji

router = APIRouter()
location_service    = LocationService()
restaurant_service  = RestaurantService()
foursquare_service  = FoursquareService()
decision_service    = DecisionService()


class PreferenceEnum(str, Enum):
    FOOD_ONLY       = "food_only"
    FOOD_AND_DRINKS = "food_and_drinks"


class SpinRequest(BaseModel):
    lat:        Optional[float] = None
    lon:        Optional[float] = None
    address:    Optional[str]   = None
    radius:     Optional[int]   = 10000   # 10 km default
    preference: PreferenceEnum  = PreferenceEnum.FOOD_ONLY


class SpinResponse(BaseModel):
    success:                 bool
    location:                Optional[dict] = None
    restaurant:              Optional[dict] = None
    food:                    Optional[str]  = None
    drink:                   Optional[str]  = None
    luck_factor:             Optional[float]= None
    luck_label:              Optional[str]  = None
    distance_label:          Optional[str]  = None
    total_restaurants_found: Optional[int]  = None
    message:                 Optional[str]  = None
    error:                   Optional[str]  = None


@router.post("/", response_model=SpinResponse,
             summary="Full roulette spin — one call does everything")
async def spin(request: SpinRequest):
    """
    Resolves location → finds restaurants (Foursquare if key set, else OSM) →
    runs Russian roulette → returns the chosen restaurant + dish (+ drink).
    """

    # ── Step 1: Resolve location ──────────────────────────────────────────────
    if request.lat is not None and request.lon is not None:
        location_data = {"lat": request.lat, "lon": request.lon, "source": "manual_coords"}

    elif request.address:
        location_data = await location_service.geocode_address(request.address)
        if not location_data:
            raise HTTPException(
                status_code=400,
                detail=f"Could not geocode address: '{request.address}'"
            )
        location_data["source"] = "address"

    else:
        location_data = await location_service.get_location_from_ip()
        if not location_data:
            raise HTTPException(
                status_code=503,
                detail="Could not auto-detect location. Provide lat/lon or address."
            )
        location_data["source"] = "ip_detection"

    lat    = location_data["lat"]
    lon    = location_data["lon"]
    radius = request.radius or 10000

    # ── Step 2: Find nearby restaurants ──────────────────────────────────────
    restaurant_dicts = []

    if foursquare_service.is_configured():
        try:
            restaurant_dicts = await foursquare_service.search_restaurants(lat, lon, radius=radius)
        except Exception as e:
            print(f"[Spin] Foursquare failed ({e}), falling back to OSM")

    if not restaurant_dicts:
        raw = await restaurant_service.find_restaurants_nearby(lat=lat, lon=lon, radius=radius)
        restaurant_dicts = [await restaurant_service.get_restaurant_details(r) for r in raw]

    if not restaurant_dicts:
        return SpinResponse(
            success=False,
            location=location_data,
            error="No restaurants found nearby. Try a larger radius.",
        )

    # ── Step 3: Russian roulette decision ─────────────────────────────────────
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
