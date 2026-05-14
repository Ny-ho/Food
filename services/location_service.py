import httpx
from typing import Optional, Dict, Any
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

class LocationService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="food_decision_app")
        
    async def get_location_from_ip(self) -> Optional[Dict[str, Any]]:
        """Get location from IP address using free IP geolocation API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://ip-api.com/json/")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        return {
                            "lat": data["lat"],
                            "lon": data["lon"],
                            "city": data.get("city"),
                            "region": data.get("regionName"),
                            "country": data.get("country")
                        }
        except Exception as e:
            print(f"Error getting location from IP: {e}")
        return None
    
    async def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Convert address to coordinates using Nominatim (OpenStreetMap)"""
        try:
            location = self.geolocator.geocode(address)
            if location:
                return {
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "address": location.address,
                    "raw": location.raw
                }
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error geocoding address: {e}")
        return None
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Convert coordinates to address using Nominatim"""
        try:
            location = self.geolocator.reverse((lat, lon))
            if location:
                return {
                    "address": location.address,
                    "raw": location.raw
                }
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error reverse geocoding: {e}")
        return None
