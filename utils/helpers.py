"""
Utility helpers for the Food Decision API
"""
import hashlib
import random
from math import asin, cos, radians, sin, sqrt
from typing import List, Dict, Any


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def stable_restaurant_id(source: str, name: str, lat: float, lon: float) -> str:
    raw = f"{source}|{name}|{lat:.6f}|{lon:.6f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def weighted_random_choice(items: List[Dict[str, Any]], weight_key: str = "distance_km") -> Dict[str, Any]:
    """
    Pick a random item weighted inversely by a numeric key.
    Items with a smaller value (e.g. shorter distance) get a higher chance.
    """
    if not items:
        raise ValueError("Cannot pick from an empty list")

    weights = []
    for item in items:
        val = item.get(weight_key) or 5.0  # Default if missing
        w = 1.0 / (val + 0.1)  # Inverse weight
        w *= random.uniform(0.5, 2.0)  # Roulette chaos factor
        weights.append(w)

    total = sum(weights)
    weights = [w / total for w in weights]
    return random.choices(items, weights=weights, k=1)[0]


def format_distance(km: float) -> str:
    """Return a human-readable distance string."""
    if km is None:
        return "Unknown distance"
    if km < 1:
        return f"{int(km * 1000)} m away"
    return f"{km:.1f} km away"


def luck_emoji(luck_factor: float) -> str:
    """Return an emoji representing the luck level."""
    if luck_factor < 0.2:
        return "🍀 (barely any luck)"
    elif luck_factor < 0.4:
        return "🎲 (so-so luck)"
    elif luck_factor < 0.6:
        return "⭐ (decent luck)"
    elif luck_factor < 0.8:
        return "🌟 (good luck!)"
    else:
        return "🔥 (insane luck!)"
