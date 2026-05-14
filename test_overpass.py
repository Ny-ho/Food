import httpx
import asyncio

async def test():
    query = (
        "[out:json][timeout:25];\n"
        "(\n"
        "  node[\"amenity\"~\"restaurant|cafe|fast_food\"](around:5000,27.7172,85.3240);\n"
        "  way[\"amenity\"~\"restaurant|cafe|fast_food\"](around:5000,27.7172,85.3240);\n"
        ");\n"
        "out center;\n"
    )
    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    for mirror in mirrors:
        print(f"Trying: {mirror}")
        try:
            headers = {"User-Agent": "FoodRouletteApp/1.0", "Accept": "*/*"}
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as c:
                r = await c.post(mirror, content=query)
                print(f"  Status: {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    elements = data.get("elements", [])
                    print(f"  Elements found: {len(elements)}")
                    for el in elements[:3]:
                        name = el.get("tags", {}).get("name", "Unknown")
                        amenity = el.get("tags", {}).get("amenity", "?")
                        print(f"    - {name} ({amenity})")
                    if elements:
                        break
                else:
                    print(f"  Body: {r.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")

asyncio.run(test())
