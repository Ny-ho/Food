import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from utils.helpers import stable_restaurant_id

@dataclass
class Restaurant:
    name: str
    lat: float
    lon: float
    address: str
    cuisine: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    distance: Optional[float] = None

# Public Overpass API mirrors (tried in order if one fails/is slow)
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

class RestaurantService:
    def __init__(self):
        self.overpass_mirrors = OVERPASS_MIRRORS

    async def find_restaurants_nearby(
        self, lat: float, lon: float, radius: int = 2000, max_results: int = 80
    ) -> List[Restaurant]:
        """Find restaurants near given coordinates using OpenStreetMap Overpass API.
        Tries multiple free mirrors until one succeeds."""

        # Larger circles need more time on public Overpass instances
        overpass_timeout = max(25, min(90, 20 + radius // 800))
        http_timeout = float(overpass_timeout + 15)

        # Also include cafes and fast_food in addition to restaurants
        query = f"""
        [out:json][timeout:{overpass_timeout}];
        (
          node["amenity"~"restaurant|cafe|fast_food"](around:{radius},{lat},{lon});
          way["amenity"~"restaurant|cafe|fast_food"](around:{radius},{lat},{lon});
        );
        out center;
        """

        headers = {"User-Agent": "FoodRouletteApp/1.0", "Accept": "application/json"}
        for mirror in self.overpass_mirrors:
            try:
                async with httpx.AsyncClient(timeout=http_timeout, headers=headers) as client:
                    response = await client.post(mirror, data={"data": query})
                    if response.status_code == 200:
                        data = response.json()
                        results = self._parse_restaurants(data, lat, lon, max_results)
                        if results:
                            print(f"[RestaurantService] Got {len(results)} results from {mirror}")
                            return results
                    else:
                        print(f"[RestaurantService] Mirror {mirror} returned {response.status_code}")
            except Exception as e:
                print(f"[RestaurantService] Mirror {mirror} failed: {e}")
                continue

        print("[RestaurantService] All mirrors failed or returned empty results.")
        return []

    def _parse_restaurants(
        self, data: Dict, user_lat: float, user_lon: float, max_results: int = 80
    ) -> List[Restaurant]:
        """Parse Overpass API response into Restaurant objects"""
        restaurants = []

        for element in data.get("elements", []):
            tags = element.get("tags", {})

            # Get coordinates
            if element["type"] == "node":
                lat, lon = element["lat"], element["lon"]
            elif element["type"] in ("way", "relation"):
                center = element.get("center")
                if not center:
                    continue
                lat, lon = center["lat"], center["lon"]
            else:
                continue

            # Build restaurant object
            restaurant = Restaurant(
                name=tags.get("name", "Unknown Restaurant"),
                lat=lat,
                lon=lon,
                address=self._build_address(tags),
                cuisine=tags.get("cuisine"),
                phone=tags.get("phone"),
                website=tags.get("website"),
                rating=None,
            )
            restaurant.distance = self._calculate_distance(user_lat, user_lon, lat, lon)
            restaurants.append(restaurant)

        restaurants.sort(key=lambda x: x.distance or float("inf"))
        cap = max(1, min(120, max_results))
        return restaurants[:cap]

    def _build_address(self, tags: Dict) -> str:
        """Build address from OSM tags"""
        parts = []
        if "addr:housenumber" in tags:
            parts.append(tags["addr:housenumber"])
        if "addr:street" in tags:
            parts.append(tags["addr:street"])
        if "addr:city" in tags:
            parts.append(tags["addr:city"])
        return ", ".join(parts) if parts else "Address unknown"

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in km"""
        from math import radians, cos, sin, asin, sqrt
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6371 * 2 * asin(sqrt(a))

    async def get_restaurant_details(self, restaurant: Restaurant) -> Dict[str, Any]:
        """Serialize a Restaurant dataclass to a response dict"""
        lat, lon = restaurant.lat, restaurant.lon
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        categories: List[str] = []
        if restaurant.cuisine:
            for part in restaurant.cuisine.replace(";", ",").split(","):
                p = part.strip()
                if p:
                    categories.append(p)
        if not categories:
            categories = ["Local eats"]

        return {
            "id": stable_restaurant_id("osm", restaurant.name, lat, lon),
            "source": "osm",
            "name": restaurant.name,
            "address": restaurant.address,
            "cuisine": restaurant.cuisine,
            "phone": restaurant.phone,
            "website": restaurant.website,
            "coordinates": {"lat": lat, "lon": lon},
            "distance_km": round(restaurant.distance, 2) if restaurant.distance else None,
            "photo_url": None,
            "url": maps_url,
            "maps_url": maps_url,
            "categories": categories,
        }
