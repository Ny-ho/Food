"""
Foursquare Places API v3 service.
Docs: https://docs.foursquare.com/developer/reference/place-search
Free tier: 1,000 calls/day.

Key note: Foursquare v3 puts lat/lon in geocodes.main, NOT location.
"""
import os
import httpx
from typing import List, Dict, Any, Optional

FSQ_BASE = "https://api.foursquare.com/v3"
FOOD_CATEGORIES = "13000"   # All food & dining


class FoursquareService:
    def __init__(self):
        self.api_key = os.getenv("FSQ_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search_restaurants(
        self,
        lat: float,
        lon: float,
        radius: int = 10000,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("FSQ_API_KEY not set in .env")

        headers = {"Authorization": self.api_key, "Accept": "application/json"}
        params = {
            "ll": f"{lat},{lon}",
            "radius": min(radius, 100000),
            "categories": FOOD_CATEGORIES,
            "limit": limit,
            "sort": "DISTANCE",
            # geocodes is REQUIRED — location object has no coords in v3
            "fields": "fsq_id,name,location,geocodes,categories,distance,photos,rating,website,tel",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{FSQ_BASE}/places/search", headers=headers, params=params
            )

        if resp.status_code == 401:
            print("[Foursquare] 401 Unauthorized — check FSQ_API_KEY in .env")
            return []
        if resp.status_code == 429:
            print("[Foursquare] 429 Rate limited")
            return []
        if resp.status_code != 200:
            print(f"[Foursquare] Error {resp.status_code}: {resp.text[:300]}")
            return []

        results = resp.json().get("results", [])
        print(f"[Foursquare] Got {len(results)} results")
        return [self._normalize(r) for r in results]

    async def get_photos(self, fsq_id: str, limit: int = 1) -> List[str]:
        if not self.is_configured():
            return []
        headers = {"Authorization": self.api_key, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{FSQ_BASE}/places/{fsq_id}/photos",
                headers=headers,
                params={"limit": limit},
            )
        if resp.status_code != 200:
            return []
        photos = resp.json()
        return [
            f"{p['prefix']}400x300{p['suffix']}"
            for p in photos
            if "prefix" in p and "suffix" in p
        ]

    def _normalize(self, r: Dict[str, Any]) -> Dict[str, Any]:
        loc  = r.get("location", {})
        cats = r.get("categories", [])
        gc   = r.get("geocodes", {}).get("main", {})   # Real coordinates

        cuisine = cats[0]["name"] if cats else "Restaurant"

        # Use formatted_address when available — it's the full readable string
        address = (
            loc.get("formatted_address")
            or loc.get("address")
            or self._build_address(loc)
            or "Address unknown"
        )

        # Inline photo from search response
        photo_url = None
        photos = r.get("photos", [])
        if photos and isinstance(photos, list):
            p = photos[0]
            if "prefix" in p and "suffix" in p:
                photo_url = f"{p['prefix']}400x300{p['suffix']}"

        return {
            "fsq_id":      r.get("fsq_id"),
            "name":        r.get("name", "Unknown"),
            "address":     address,
            "cuisine":     cuisine,
            "phone":       r.get("tel"),
            "website":     r.get("website"),
            "coordinates": {
                "lat": gc.get("latitude"),
                "lon": gc.get("longitude"),
            },
            "distance_km": round(r.get("distance", 0) / 1000, 2),
            "rating":      r.get("rating"),
            "photo_url":   photo_url,
            "source":      "foursquare",
        }

    def _build_address(self, loc: Dict) -> str:
        parts = []
        if loc.get("address"):
            parts.append(loc["address"])
        if loc.get("cross_street"):
            parts.append(f"({loc['cross_street']})")
        if loc.get("locality"):
            parts.append(loc["locality"])
        if loc.get("region"):
            parts.append(loc["region"])
        return ", ".join(parts)
