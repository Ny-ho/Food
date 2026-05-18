import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Restaurant:
    name: str
    lat: float
    lon: float
    address: str
    cuisine: Optional[str] = None
    amenity: Optional[str] = None   # restaurant / cafe / fast_food
    phone: Optional[str] = None
    website: Optional[str] = None
    distance: Optional[float] = None

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

class RestaurantService:
    def __init__(self):
        self.overpass_mirrors = OVERPASS_MIRRORS

    async def find_restaurants_nearby(self, lat: float, lon: float, radius: int = 10000) -> List[Restaurant]:
        query = (
            f"[out:json][timeout:40];"
            f"("
            f"node[\"amenity\"~\"restaurant|cafe|fast_food\"](around:{radius},{lat},{lon});"
            f"way[\"amenity\"~\"restaurant|cafe|fast_food\"](around:{radius},{lat},{lon});"
            f");"
            f"out center;"
        )
        headers = {"User-Agent": "FoodRouletteApp/1.0", "Accept": "application/json"}

        for mirror in self.overpass_mirrors:
            try:
                async with httpx.AsyncClient(timeout=45.0, headers=headers) as client:
                    resp = await client.post(mirror, data={"data": query})
                if resp.status_code == 200:
                    results = self._parse_restaurants(resp.json(), lat, lon)
                    if results:
                        print(f"[OSM] Got {len(results)} results from {mirror}")
                        return results
                else:
                    print(f"[OSM] {mirror} returned {resp.status_code}")
            except Exception as e:
                print(f"[OSM] {mirror} failed: {e}")

        print("[OSM] All mirrors failed.")
        return []

    def _parse_restaurants(self, data: Dict, user_lat: float, user_lon: float) -> List[Restaurant]:
        restaurants = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            if element["type"] == "node":
                lat, lon = element["lat"], element["lon"]
            elif element["type"] in ("way", "relation"):
                center = element.get("center")
                if not center:
                    continue
                lat, lon = center["lat"], center["lon"]
            else:
                continue

            name = tags.get("name", "").strip()
            if not name:
                continue

            r = Restaurant(
                name=name,
                lat=lat,
                lon=lon,
                address=self._build_address(tags),
                cuisine=tags.get("cuisine"),
                amenity=tags.get("amenity", "restaurant"),
                phone=tags.get("phone"),
                website=tags.get("website"),
            )
            r.distance = self._haversine(user_lat, user_lon, lat, lon)
            restaurants.append(r)

        restaurants.sort(key=lambda x: x.distance or 99)
        return restaurants[:30]

    def _build_address(self, tags: Dict) -> str:
        parts = []
        if tags.get("addr:housenumber"):
            parts.append(tags["addr:housenumber"])
        if tags.get("addr:street"):
            parts.append(tags["addr:street"])
        if tags.get("addr:suburb"):
            parts.append(tags["addr:suburb"])
        if tags.get("addr:city"):
            parts.append(tags["addr:city"])
        return ", ".join(parts) if parts else ""

    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        from math import radians, cos, sin, asin, sqrt
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 6371 * 2 * asin(sqrt(a))

    async def get_restaurant_details(self, r: Restaurant) -> Dict[str, Any]:
        # Map amenity type to a readable cuisine label if cuisine tag is missing
        amenity_label = {
            "cafe": "Cafe",
            "fast_food": "Fast Food",
            "restaurant": "Restaurant",
        }.get(r.amenity or "", "Restaurant")

        # Build best possible address
        address = r.address if r.address else await self._reverse_geocode(r.lat, r.lon)

        return {
            "name":        r.name,
            "address":     address or "Pokhara, Nepal",
            "cuisine":     r.cuisine or amenity_label,
            "phone":       r.phone,
            "website":     r.website,
            "coordinates": {"lat": r.lat, "lon": r.lon},
            "distance_km": round(r.distance, 2) if r.distance else None,
            "photo_url":   None,
            "source":      "osm",
        }

    async def _reverse_geocode(self, lat: float, lon: float) -> str:
        """
        Single Nominatim reverse-geocode call — only used when address tags are missing.
        Nominatim ToS: max 1 req/sec, include User-Agent.
        """
        try:
            headers = {"User-Agent": "FoodRouletteApp/1.0"}
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=18"
            async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                d = resp.json()
                addr = d.get("address", {})
                parts = []
                if addr.get("road"):
                    parts.append(addr["road"])
                if addr.get("suburb") or addr.get("neighbourhood"):
                    parts.append(addr.get("suburb") or addr.get("neighbourhood"))
                if addr.get("city") or addr.get("town"):
                    parts.append(addr.get("city") or addr.get("town"))
                return ", ".join(parts) if parts else d.get("display_name", "")[:60]
        except Exception:
            pass
        return ""
