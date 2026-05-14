import asyncio
import httpx

async def test_spin():
    # Use direct FastAPI app instead of requests to start server, or just use a TestClient
    from main import app
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        print("Testing spin with lat/lon...")
        response = await ac.post("/api/spin/", json={
            "lat": 40.7128,
            "lon": -74.0060,
            "radius": 1000,
            "preference": "food_and_drinks"
        }, timeout=30.0)
        
        print("Status Code:", response.status_code)
        if response.status_code == 200:
            data = response.json()
            print("Success:", data["success"])
            print("Restaurant:", data.get("restaurant", {}).get("name"))
            print("Food:", data.get("food"))
            print("Drink:", data.get("drink"))
        else:
            print("Error:", response.text)

if __name__ == "__main__":
    asyncio.run(test_spin())
