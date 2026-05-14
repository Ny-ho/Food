"""
Yelp Fusion (Places) API — optional. Set YELP_API_KEY in .env.
See https://docs.developer.yelp.com/docs/resources-faq for plans and attribution.
"""
import os
from typing import Any, Dict, List, Optional

import httpx

from utils.helpers import haversine_km, stable_restaurant_id

YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"


class YelpService:
    def __init__(self) -> None:
        self._api_key: Optional[str] = os.getenv("YELP_API_KEY", "").strip() or None

    def is_configured(self) -> bool:
        return self._api_key is not None

    async def search_restaurants(
        self,
        lat: float,
        lon: float,
        radius_m: int,
        term: Optional[str] = None,
        limit: int = 40,
    ) -> List[Dict[str, Any]]:
        """Search Yelp for food businesses. Radius is capped at 40_000 m (Yelp max)."""
        if not self._api_key:
            return []

        radius = max(100, min(40_000, int(radius_m)))
        limit = max(1, min(50, int(limit)))

        params: Dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "radius": radius,
            "categories": "restaurants,food",
            "limit": limit,
            "sort_by": "distance",
        }
        if term:
            params["term"] = term

        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(YELP_SEARCH_URL, params=params, headers=headers)

        if response.status_code == 401:
            raise RuntimeError("Yelp API rejected the key (401). Check YELP_API_KEY in .env.")
        if response.status_code != 200:
            raise RuntimeError(f"Yelp API error {response.status_code}: {response.text[:200]}")

        payload = response.json()
        businesses = payload.get("businesses") or []

        out: List[Dict[str, Any]] = []
        for b in businesses:
            coords = b.get("coordinates") or {}
            blat = coords.get("latitude")
            blon = coords.get("longitude")
            if blat is None or blon is None:
                continue

            loc = b.get("location") or {}
            display = loc.get("display_address") or []
            address = ", ".join(display) if isinstance(display, list) else str(display)

            cats_raw = b.get("categories") or []
            cat_titles = [c.get("title", "") for c in cats_raw if isinstance(c, dict)]
            cat_titles = [t for t in cat_titles if t]

            distance_km = round(haversine_km(lat, lon, float(blat), float(blon)), 2)

            out.append(
                {
                    "id": b.get("id") or stable_restaurant_id("yelp", b.get("name", ""), float(blat), float(blon)),
                    "source": "yelp",
                    "name": b.get("name", "Unknown"),
                    "address": address or "Address unknown",
                    "coordinates": {"lat": float(blat), "lon": float(blon)},
                    "distance_km": distance_km,
                    "photo_url": b.get("image_url") or None,
                    "url": b.get("url"),
                    "rating": b.get("rating"),
                    "review_count": b.get("review_count"),
                    "price": b.get("price"),
                    "cuisine": ", ".join(cat_titles) if cat_titles else None,
                    "categories": cat_titles,
                    "phone": b.get("display_phone") or b.get("phone"),
                }
            )

        out.sort(key=lambda x: x.get("distance_km") or 1e9)
        return out
