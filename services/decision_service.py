import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PreferenceType(Enum):
    FOOD_ONLY = "food_only"
    FOOD_AND_DRINKS = "food_and_drinks"

@dataclass
class DecisionResult:
    selected_restaurant: Dict[str, Any]
    selected_menu_item: Optional[str] = None
    selected_drink: Optional[str] = None
    decision_method: str = "russian_roulette"
    luck_factor: float = 0.0  # 0.0 to 1.0, higher is "luckier"

class DecisionService:
    def __init__(self):
        # Sample menu items for different cuisines
        self.menu_items = {
            "italian": ["Pizza Margherita", "Spaghetti Carbonara", "Lasagna", "Risotto", "Fettuccine Alfredo"],
            "chinese": ["Kung Pao Chicken", "Sweet and Sour Pork", "Fried Rice", "Dumplings", "Hot and Sour Soup"],
            "mexican": ["Tacos al Pastor", "Enchiladas", "Quesadillas", "Burrito Bowl", "Chiles Rellenos"],
            "american": ["Burger and Fries", "BBQ Ribs", "Mac and Cheese", "Chicken Wings", "Grilled Cheese"],
            "japanese": ["Sushi Roll", "Ramen", "Tempura", "Teriyaki Chicken", "Miso Soup"],
            "indian": ["Chicken Tikka Masala", "Biryani", "Palak Paneer", "Naan", "Samosas", "Dal Makhani", "Momos"],
            "thai": ["Pad Thai", "Tom Yum Soup", "Green Curry", "Massaman Curry", "Som Tum"],
            "korean": ["Bibimbap", "Korean Fried Chicken", "Bulgogi", "Kimchi Jjigae", "Japchae"],
            "vietnamese": ["Pho", "Banh Mi", "Spring Rolls", "Bun Cha", "Com Tam"],
            "mediterranean": ["Falafel Bowl", "Shawarma Plate", "Greek Salad", "Hummus Mezze", "Grilled Kebab"],
            "default": ["House Special", "Chef's Recommendation", "Daily Special", "Signature Dish", "Popular Choice"]
        }
        
        # Sample drink items
        self.drinks = {
            "alcoholic": ["Beer", "Wine", "Cocktail", "Whiskey", "Vodka", "Rum", "Gin and Tonic"],
            "non_alcoholic": ["Soda", "Juice", "Iced Tea", "Lemonade", "Water", "Coffee", "Smoothie"],
            "mixed": ["Soda", "Juice", "Beer", "Wine", "Cocktail", "Iced Tea", "Coffee"]
        }
    
    async def make_decision(self, restaurants: List[Dict[str, Any]], preference: PreferenceType) -> DecisionResult:
        """Make a Russian roulette style decision about what to eat"""
        
        if not restaurants:
            raise ValueError("No restaurants provided for decision")
        
        # Russian roulette restaurant selection
        selected_restaurant = self._russian_roulette_selection(restaurants)
        
        # Determine cuisine type from restaurant info
        cuisine = self._extract_cuisine(selected_restaurant)
        
        # Select food item
        selected_food = self._select_menu_item(cuisine)
        
        # Select drink if preference includes drinks
        selected_drink = None
        if preference == PreferenceType.FOOD_AND_DRINKS:
            selected_drink = self._select_drink()
        
        # Calculate luck factor (random for fun)
        luck_factor = random.random()
        
        return DecisionResult(
            selected_restaurant=selected_restaurant,
            selected_menu_item=selected_food,
            selected_drink=selected_drink,
            decision_method="russian_roulette",
            luck_factor=luck_factor
        )

    async def spin_from_menu(
        self,
        restaurant: Dict[str, Any],
        menu_items: List[str],
        preference: PreferenceType,
    ) -> DecisionResult:
        """Pick one item from the visible shortlist (true roulette on your choices)."""
        pool = [m for m in (menu_items or []) if isinstance(m, str) and m.strip()]
        if not pool:
            pool = self.suggest_menu_items(restaurant)

        selected_food = random.choice(pool)
        selected_drink = None
        if preference == PreferenceType.FOOD_AND_DRINKS:
            selected_drink = self._select_drink()
        luck_factor = random.random()

        return DecisionResult(
            selected_restaurant=restaurant,
            selected_menu_item=selected_food,
            selected_drink=selected_drink,
            decision_method="menu_roulette",
            luck_factor=luck_factor,
        )

    def suggest_menu_items(self, restaurant: Dict[str, Any], max_items: int = 8) -> List[str]:
        """Build a short fun shortlist from cuisine / Yelp categories (not live Yelp menus)."""
        cuisine_bucket = self._extract_cuisine(restaurant)
        base = list(self.menu_items.get(cuisine_bucket, self.menu_items["default"]))

        extras: List[str] = []
        cats = restaurant.get("categories") or []
        if isinstance(cats, str):
            cats = [cats]
        for c in cats[:5]:
            if not isinstance(c, str):
                continue
            c = c.strip()
            if len(c) < 2:
                continue
            extras.append(f"{c} - house favorite")
            extras.append(f"Chef's {c} combo")

        merged = base + extras
        random.shuffle(merged)
        seen: set[str] = set()
        out: List[str] = []
        for item in merged:
            if item not in seen:
                seen.add(item)
                out.append(item)
            if len(out) >= max_items:
                break

        fallback = list(self.menu_items["default"])
        random.shuffle(fallback)
        guard = 0
        while len(out) < max_items and guard < max_items * 4:
            guard += 1
            pick = fallback[(len(out) + guard) % len(fallback)]
            if pick not in seen:
                seen.add(pick)
                out.append(pick)
            else:
                w = f"Wildcard #{guard}"
                if w not in seen:
                    seen.add(w)
                    out.append(w)
        return out[:max_items]
    
    def _russian_roulette_selection(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate Russian roulette selection - weighted random with higher chance for closer/better options"""
        
        # Create weights based on distance (closer = higher weight) and add some randomness
        weights = []
        for item in items:
            distance = item.get("distance_km", 5.0)  # Default to 5km if no distance
            # Inverse distance weight (closer is better)
            distance_weight = 1.0 / (distance + 0.1)  # Add 0.1 to avoid division by zero
            # Add random factor for the "roulette" effect
            random_factor = random.uniform(0.5, 2.0)
            weight = distance_weight * random_factor
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(items)] * len(items)
        
        # Weighted random selection
        selected_index = random.choices(range(len(items)), weights=weights)[0]
        return items[selected_index]
    
    def _extract_cuisine(self, restaurant: Dict[str, Any]) -> str:
        """Extract cuisine type from restaurant data"""
        cuisine_raw = restaurant.get("cuisine")
        cuisine = cuisine_raw.lower() if cuisine_raw else ""

        cats = restaurant.get("categories") or []
        if isinstance(cats, str):
            cat_blob = cats.lower()
        else:
            cat_blob = " ".join(str(c).lower() for c in cats if c)

        name = restaurant.get("name", "").lower()
        combined = f"{cuisine} {cat_blob} {name}"

        cuisine_mapping = {
            "pizza": "italian",
            "pasta": "italian",
            "italian": "italian",
            "burger": "american",
            "steak": "american",
            "american": "american",
            "newamerican": "american",
            "tradamerican": "american",
            "sushi": "japanese",
            "ramen": "japanese",
            "japanese": "japanese",
            "japan": "japanese",
            "curry": "indian",
            "indian": "indian",
            "nepalese": "indian",
            "himalayan": "indian",
            "thai": "thai",
            "mexican": "mexican",
            "taco": "mexican",
            "chinese": "chinese",
            "dim sum": "chinese",
            "asian": "chinese",
            "korean": "korean",
            "vietnamese": "vietnamese",
            "pho": "vietnamese",
            "mediterranean": "mediterranean",
            "middle eastern": "mediterranean",
            "falafel": "mediterranean",
        }

        for key, mapped_cuisine in cuisine_mapping.items():
            if key in combined:
                return mapped_cuisine

        return "default"
    
    def _select_menu_item(self, cuisine: str) -> str:
        """Select a menu item based on cuisine type"""
        items = self.menu_items.get(cuisine, self.menu_items["default"])
        return random.choice(items)
    
    def _select_drink(self) -> str:
        """Select a random drink"""
        all_drinks = self.drinks["mixed"]
        return random.choice(all_drinks)
    
    async def get_decision_explanation(self, result: DecisionResult) -> Dict[str, Any]:
        """Generate an explanation of how the decision was made"""
        
        explanation = {
            "method": "Russian Roulette Selection",
            "restaurant": result.selected_restaurant.get("name", "Unknown"),
            "distance": result.selected_restaurant.get("distance_km"),
            "food_choice": result.selected_menu_item,
            "drink_choice": result.selected_drink,
            "luck_factor": result.luck_factor,
            "luck_description": self._get_luck_description(result.luck_factor)
        }
        
        return explanation
    
    def _get_luck_description(self, luck_factor: float) -> str:
        """Get a fun description based on luck factor"""
        if luck_factor < 0.2:
            return "Feeling unlucky today! But sometimes the best meals come from bad luck!"
        elif luck_factor < 0.4:
            return "Your luck is moderate. Could be worse, could be better!"
        elif luck_factor < 0.6:
            return "Average luck today. Safe choice!"
        elif luck_factor < 0.8:
            return "Feeling lucky! This might turn out great!"
        else:
            return "Extremely lucky! This could be the best meal ever!"
