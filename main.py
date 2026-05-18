from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from routes import location, restaurants, decision, spin
from services.foursquare_service import FoursquareService

app = FastAPI(
    title="🎰 Food Roulette API",
    description="Find nearby restaurants and let roulette decide what you eat. 100% free, no paid APIs.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(location.router,    prefix="/api/location",    tags=["📍 Location"])
app.include_router(restaurants.router, prefix="/api/restaurants", tags=["🍽️ Restaurants"])
app.include_router(decision.router,    prefix="/api/decision",    tags=["🎲 Decision"])
app.include_router(spin.router,        prefix="/api/spin",        tags=["🎰 Spin"])

# ── Static frontend ───────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", tags=["UI"], include_in_schema=False)
async def root():
    return FileResponse("static/index.html")

@app.get("/api/debug/fsq", tags=["Debug"])
async def debug_fsq():
    """Test Foursquare API coverage for Pokhara."""
    import httpx
    fsq = FoursquareService()
    if not fsq.is_configured():
        return {"ok": False, "error": "FSQ_API_KEY not set"}

    headers = {"Authorization": fsq.api_key, "Accept": "application/json"}

    # Test 1: with food category
    async with httpx.AsyncClient(timeout=10.0) as c:
        r1 = await c.get("https://api.foursquare.com/v3/places/search",
            headers=headers,
            params={"ll": "28.2096,83.9856", "radius": 20000,
                    "categories": "13000", "limit": 3,
                    "fields": "fsq_id,name,geocodes"})

    # Test 2: without category filter — any venue
    async with httpx.AsyncClient(timeout=10.0) as c:
        r2 = await c.get("https://api.foursquare.com/v3/places/search",
            headers=headers,
            params={"ll": "28.2096,83.9856", "radius": 20000,
                    "limit": 5, "fields": "fsq_id,name,categories,geocodes"})

    return {
        "key_works": True,
        "with_food_category": {"status": r1.status_code, "count": len(r1.json().get("results",[]))},
        "without_category":  {"status": r2.status_code, "count": len(r2.json().get("results",[])),
                              "samples": [x.get("name") for x in r2.json().get("results",[])]},
        "conclusion": "Foursquare has no Nepal data" if not r2.json().get("results") else "Foursquare has some data!"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host=os.getenv("APP_HOST", "0.0.0.0"), port=int(os.getenv("APP_PORT", 8000)))
