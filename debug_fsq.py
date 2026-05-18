"""Quick debug — run: python debug_fsq.py"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

import httpx

async def main():
    key = os.getenv("FSQ_API_KEY", "")
    print(f"Key loaded: {key[:8]}...{key[-4:]}" if key else "NO KEY FOUND")

    headers = {"Authorization": key, "Accept": "application/json"}
    params  = {
        "ll": "28.2096,83.9856",      # Pokhara center
        "radius": 10000,
        "categories": "13000",        # Food umbrella
        "limit": 5,
        "sort": "DISTANCE",
        "fields": "fsq_id,name,location,geocodes,categories,distance,photos,rating,tel,website",
    }

    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get("https://api.foursquare.com/v3/places/search",
                        headers=headers, params=params)

    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print("Error body:", r.text[:500])
        return

    data = r.json()
    results = data.get("results", [])
    print(f"Results: {len(results)}")
    for res in results:
        gc   = res.get("geocodes", {}).get("main", {})
        loc  = res.get("location", {})
        cats = res.get("categories", [])
        photos = res.get("photos", [])
        print(f"\n  Name    : {res.get('name')}")
        print(f"  Category: {cats[0]['name'] if cats else 'N/A'}")
        print(f"  Geocode : lat={gc.get('latitude')} lon={gc.get('longitude')}")
        print(f"  Address : {loc.get('formatted_address') or loc.get('address') or 'none'}")
        print(f"  Distance: {res.get('distance')}m")
        print(f"  Photos  : {len(photos)} inline")
        if photos:
            p = photos[0]
            print(f"  Photo   : {p.get('prefix')}400x300{p.get('suffix')}")

asyncio.run(main())
