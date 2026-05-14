from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from services.yelp_service import YelpService

load_dotenv()  # Load .env variables before anything else

from routes import location, restaurants, decision, spin

app = FastAPI(
    title="🎰 Food Roulette API",
    description=(
        "Location-aware restaurant browse and roulette. "
        "OpenStreetMap search is free; optional Yelp photos and listings require YELP_API_KEY (see Yelp developer plans)."
    ),
    version="2.0.0",
)

# Enable CORS for frontend integration
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
app.include_router(spin.router,        prefix="/api/spin",        tags=["🎰 Spin (Full Flow)"])


@app.get("/api/config", tags=["Config"])
async def public_config():
    """Frontend feature flags (no secrets)."""
    yelp = YelpService()
    return {
        "yelp_configured": yelp.is_configured(),
        "yelp_max_radius_m": 40_000,
        "yelp_attribution_url": "https://www.yelp.com/developers",
    }


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", tags=["UI"])
async def root():
    return FileResponse("static/index.html")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
    )
