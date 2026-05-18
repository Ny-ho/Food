from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum
from services.decision_service import DecisionService, PreferenceType

router = APIRouter()
decision_service = DecisionService()

class PreferenceEnum(str, Enum):
    FOOD_ONLY = "food_only"
    FOOD_AND_DRINKS = "food_and_drinks"

class DecisionRequest(BaseModel):
    restaurants: List[Dict[str, Any]]
    preference: PreferenceEnum

class DecisionResponse(BaseModel):
    success: bool
    decision: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MenuSuggestionsRequest(BaseModel):
    restaurant: Dict[str, Any]


class MenuSuggestionsResponse(BaseModel):
    success: bool
    items: Optional[List[str]] = None
    error: Optional[str] = None


class SpinOrderRequest(BaseModel):
    restaurant: Dict[str, Any]
    menu_items: List[str]
    preference: PreferenceEnum


class SpinOrderResponse(BaseModel):
    success: bool
    decision: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/menu-suggestions", response_model=MenuSuggestionsResponse)
async def menu_suggestions(request: MenuSuggestionsRequest):
    """Ideas to order — styled from cuisine/Yelp categories (not live restaurant menus)."""
    try:
        items = decision_service.suggest_menu_items(request.restaurant)
        return MenuSuggestionsResponse(success=True, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spin-order", response_model=SpinOrderResponse)
async def spin_order(request: SpinOrderRequest):
    """Roulette picks one item from the shortlist you saw on screen."""
    try:
        pref = (
            PreferenceType.FOOD_AND_DRINKS
            if request.preference == PreferenceEnum.FOOD_AND_DRINKS
            else PreferenceType.FOOD_ONLY
        )
        result = await decision_service.spin_from_menu(request.restaurant, request.menu_items, pref)
        explanation = await decision_service.get_decision_explanation(result)
        decision_data = {
            "restaurant": result.selected_restaurant,
            "menu_item": result.selected_menu_item,
            "drink": result.selected_drink,
            "luck_factor": result.luck_factor,
            "preference": request.preference,
            "method": result.decision_method,
        }
        return SpinOrderResponse(success=True, decision=decision_data, explanation=explanation)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/make")
async def make_food_decision(request: DecisionRequest):
    """Make a Russian roulette style food decision"""
    try:
        if not request.restaurants:
            raise HTTPException(status_code=400, detail="No restaurants provided")

        preference = (
            PreferenceType.FOOD_AND_DRINKS
            if request.preference == PreferenceEnum.FOOD_AND_DRINKS
            else PreferenceType.FOOD_ONLY
        )

        result = await decision_service.make_decision(request.restaurants, preference)

        # Flat response so frontend can access fields directly
        return {
            "success": True,
            "selected_restaurant": result.selected_restaurant,
            "selected_menu_item": result.selected_menu_item,
            "selected_drink": result.selected_drink,
            "luck_factor": round(result.luck_factor, 3),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error making decision: {str(e)}")


@router.get("/preferences")
async def get_available_preferences():
    """Get available preference options"""
    return {
        "preferences": [
            {
                "value": "food_only",
                "description": "Only select food items"
            },
            {
                "value": "food_and_drinks",
                "description": "Select both food and drinks"
            }
        ]
    }

@router.get("/lucky-number")
async def get_lucky_number():
    """Get a lucky number for fun"""
    import random
    return {
        "lucky_number": random.randint(1, 100),
        "lucky_color": random.choice(["red", "blue", "green", "yellow", "purple", "orange"]),
        "fortune": random.choice([
            "You will have a delicious meal today!",
            "Adventure awaits in your food journey!",
            "Today's special will be your new favorite!",
            "Your taste buds will thank you!",
            "A culinary surprise is coming your way!"
        ])
    }
