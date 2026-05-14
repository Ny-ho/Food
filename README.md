# Food Decision API

A FastAPI backend system that finds restaurants near you and decides what to eat using Russian roulette logic.

## Features

- 📍 **Location Detection**: Auto-detect location from IP or manual address input
- 🍽️ **Restaurant Discovery**: Find nearby restaurants using OpenStreetMap (FREE)
- 🎰 **Russian Roulette Decision**: Random food selection with weighted probabilities
- 🍺 **Preference Options**: Choose food only or food + drinks
- 🌍 **Completely Free**: Uses only free APIs and services

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### 3. View API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Location Endpoints

#### Auto-detect Location
```http
GET /api/location/detect
```

#### Geocode Address
```http
POST /api/location/geocode
{
  "address": "123 Main St, New York, NY"
}
```

#### Reverse Geocode
```http
POST /api/location/reverse-geocode
{
  "lat": 40.7128,
  "lon": -74.0060
}
```

### Restaurant Endpoints

#### Find Nearby Restaurants (POST)
```http
POST /api/restaurants/nearby
{
  "lat": 40.7128,
  "lon": -74.0060,
  "radius": 2000
}
```

#### Find Nearby Restaurants (GET)
```http
GET /api/restaurants/nearby?lat=40.7128&lon=-74.0060&radius=2000
```

### Decision Endpoints

#### Make Food Decision
```http
POST /api/decision/make
{
  "restaurants": [
    {
      "name": "Restaurant Name",
      "address": "123 Main St",
      "cuisine": "italian",
      "distance_km": 1.5,
      "coordinates": {
        "lat": 40.7128,
        "lon": -74.0060
      }
    }
  ],
  "preference": "food_only"  // or "food_and_drinks"
}
```

#### Get Preferences
```http
GET /api/decision/preferences
```

#### Get Lucky Number (Fun endpoint)
```http
GET /api/decision/lucky-number
```

## Example Usage

### Complete Workflow

1. **Detect your location:**
```bash
curl http://localhost:8000/api/location/detect
```

2. **Find nearby restaurants:**
```bash
curl "http://localhost:8000/api/restaurants/nearby?lat=40.7128&lon=-74.0060"
```

3. **Make a decision:**
```bash
curl -X POST http://localhost:8000/api/decision/make \
  -H "Content-Type: application/json" \
  -d '{
    "restaurants": [
      {
        "name": "Pizza Place",
        "address": "123 Main St",
        "cuisine": "italian",
        "distance_km": 1.2,
        "coordinates": {"lat": 40.7128, "lon": -74.0060}
      }
    ],
    "preference": "food_and_drinks"
  }'
```

## How It Works

### Location Detection
- Uses free IP geolocation API (ip-api.com)
- Supports manual address geocoding with OpenStreetMap Nominatim

### Restaurant Discovery
- Uses OpenStreetMap Overpass API (completely free)
- Finds restaurants within specified radius
- Returns sorted by distance

### Russian Roulette Logic
- Weighted random selection based on distance
- Closer restaurants have higher probability
- Adds random factor for "roulette" effect
- Selects menu items based on cuisine type
- Includes luck factor for fun

## Technologies Used

- **FastAPI**: Modern Python web framework
- **OpenStreetMap**: Free mapping and location data
- **Nominatim**: Free geocoding service
- **Overpass API**: Free OSM data querying
- **IP-API**: Free IP geolocation

## Project Structure

```
Food/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── routes/                # API route handlers
│   ├── location.py        # Location endpoints
│   ├── restaurants.py     # Restaurant endpoints
│   └── decision.py        # Decision endpoints
├── services/              # Business logic
│   ├── location_service.py
│   ├── restaurant_service.py
│   └── decision_service.py
└── utils/                 # Utility functions
```

## Notes

- All APIs used are completely free with no API keys required
- Rate limiting may apply to some free services
- Restaurant data quality depends on OpenStreetMap contributions
- The "Russian roulette" is just for fun - no actual gambling involved
