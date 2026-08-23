"""
utils.py — Rule-based NLP parsing + local knowledge tables for the
Voice Command Shopping Assistant.

No external NLU API / key is used anywhere in this file. Intent
detection, categorization, seasonal logic and substitutes are all
driven by small local lookup tables + regex, which keeps the app
free, fast (no network round trip for understanding) and fully
offline-debuggable.
"""

import re
from datetime import datetime

# ---------------------------------------------------------------------
# 1. CATEGORIZATION
# ---------------------------------------------------------------------
CATEGORY_MAP = {
    "Dairy": ["milk", "cheese", "yogurt", "yoghurt", "butter", "curd", "paneer", "cream"],
    "Bakery": ["bread", "bun", "bagel", "cake", "croissant", "muffin"],
    "Produce": ["apple", "banana", "orange", "tomato", "potato", "onion", "spinach",
                "carrot", "grape", "mango", "lettuce", "cucumber", "garlic", "ginger",
                "pepper", "berries", "strawberry", "avocado"],
    "Meat & Seafood": ["chicken", "beef", "fish", "egg", "shrimp", "mutton", "prawn", "salmon"],
    "Snacks": ["chips", "cookie", "chocolate", "biscuit", "popcorn", "namkeen", "candy"],
    "Beverages": ["water", "juice", "soda", "coffee", "tea", "cola", "coconut water"],
    "Household": ["soap", "detergent", "tissue", "napkin", "cleaner", "sponge", "trash bag"],
    "Personal Care": ["toothpaste", "shampoo", "toothbrush", "lotion", "deodorant", "razor"],
    "Pantry": ["rice", "flour", "sugar", "salt", "oil", "pasta", "cereal", "atta", "lentil",
               "dal", "spice", "honey", "jam"],
    "Frozen": ["ice cream", "frozen", "frozen peas", "frozen fries"],
}


def categorize(item: str) -> str:
    item_l = item.lower()
    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in item_l:
                return category
    return "Other"


# ---------------------------------------------------------------------
# 2. SUBSTITUTES
# ---------------------------------------------------------------------
SUBSTITUTES = {
    "milk": ["almond milk", "soy milk", "oat milk"],
    "sugar": ["honey", "jaggery", "stevia"],
    "butter": ["margarine", "ghee"],
    "rice": ["quinoa", "cauliflower rice"],
    "bread": ["multigrain bread", "gluten-free bread"],
    "chicken": ["tofu", "paneer"],
    "regular milk": ["almond milk", "oat milk"],
    "maida": ["whole wheat flour"],
    "flour": ["whole wheat flour", "almond flour"],
}


def get_substitute(item: str):
    item_l = item.lower()
    for key, subs in SUBSTITUTES.items():
        if key in item_l:
            return subs
    return []


# ---------------------------------------------------------------------
# 3. SEASONAL SUGGESTIONS (rule table, no external API)
# ---------------------------------------------------------------------
SEASONAL_BY_MONTH_NORTH = {
    1: ["oranges", "kale", "cabbage", "carrots"],
    2: ["oranges", "spinach", "broccoli"],
    3: ["asparagus", "peas", "spinach", "strawberries"],
    4: ["asparagus", "strawberries", "peas"],
    5: ["strawberries", "cherries", "asparagus"],
    6: ["watermelon", "cherries", "corn", "peaches"],
    7: ["watermelon", "corn", "tomatoes", "peaches", "berries"],
    8: ["corn", "tomatoes", "peaches", "grapes", "plums"],
    9: ["apples", "grapes", "pumpkin", "pears"],
    10: ["apples", "pumpkin", "sweet potatoes", "pears"],
    11: ["sweet potatoes", "cranberries", "pumpkin", "brussels sprouts"],
    12: ["citrus", "cranberries", "pomegranate", "brussels sprouts"],
}


def get_seasonal_items(hemisphere: str = "Northern"):
    month = datetime.now().month
    if hemisphere == "Southern":
        month = ((month + 5) % 12) + 1  # shift by 6 months
    return SEASONAL_BY_MONTH_NORTH.get(month, [])


# ---------------------------------------------------------------------
# 4. "RUNNING LOW" MOCK SUGGESTION ENGINE
#    (In a real system this would come from purchase-history frequency;
#     here we simulate it with a common-staples table + what's missing
#     from the current list, which is enough to demo the feature.)
# ---------------------------------------------------------------------
STAPLES = ["milk", "bread", "eggs", "bananas", "onions"]


def get_running_low_suggestions(current_items):
    current = {i.lower() for i in current_items}
    missing = [s for s in STAPLES if not any(s in c or c in s for c in current)]
    return missing[:3]


# ---------------------------------------------------------------------
# 5. MOCK PRODUCT CATALOG for voice-activated search / price filtering
# ---------------------------------------------------------------------
MOCK_CATALOG = [
    {"name": "organic apples", "price": 3.5, "brand": "Nature's Best"},
    {"name": "apples", "price": 2.0, "brand": "Generic"},
    {"name": "toothpaste", "price": 2.99, "brand": "Colgate"},
    {"name": "toothpaste", "price": 6.5, "brand": "Sensodyne"},
    {"name": "almond milk", "price": 4.2, "brand": "Silk"},
    {"name": "whole milk", "price": 2.1, "brand": "Local Dairy"},
    {"name": "bananas", "price": 0.5, "brand": "Generic"},
    {"name": "bread", "price": 2.0, "brand": "Local Bakery"},
    {"name": "multigrain bread", "price": 3.2, "brand": "Local Bakery"},
    {"name": "greek yogurt", "price": 3.0, "brand": "Chobani"},
    {"name": "basmati rice", "price": 8.0, "brand": "India Gate"},
    {"name": "olive oil", "price": 9.5, "brand": "Filippo Berio"},
    {"name": "dark chocolate", "price": 2.5, "brand": "Lindt"},
    {"name": "orange juice", "price": 3.1, "brand": "Tropicana"},
]


def search_catalog(item: str, price_max=None, brand=None):
    item_l = (item or "").lower().strip()
    results = []
    for p in MOCK_CATALOG:
        if item_l and item_l not in p["name"] and p["name"] not in item_l:
            continue
        if price_max is not None and p["price"] > price_max:
            continue
        if brand and brand.lower() not in p["brand"].lower():
            continue
        results.append(p)
    return results


# ---------------------------------------------------------------------
# 6. INTENT PARSER
# ---------------------------------------------------------------------
ADD_TRIGGERS = ["i want to buy", "i need to buy", "i need", "i want", "add", "buy",
                "get me", "put", "purchase", "grab", "we need"]
REMOVE_TRIGGERS = ["remove", "delete", "take off", "don't need", "no longer need",
                    "get rid of"]
SEARCH_TRIGGERS = ["find me", "find", "search for", "search", "look for", "show me"]

NUM_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "couple": 2, "few": 3, "dozen": 12,
}

FILLERS = [
    "to my list", "to the list", "from my list", "from the list", "my list",
    "the list", "to buy", "to cart", "please", "for me", "some",
]

# Container / unit words that precede the real item name (e.g. "2 bottles
# of water" -> item should be "water", not "bottles water").
UNIT_WORDS = [
    "bottles", "bottle", "cans", "can", "packs", "pack", "boxes", "box",
    "bags", "bag", "kg", "kilogram", "kilograms", "liters", "litres",
    "liter", "litre", "dozen", "pieces", "piece", "cartons", "carton",
]


def _strip_fillers(text: str) -> str:
    out = text
    for f in FILLERS:
        out = out.replace(f, " ")
    for u in UNIT_WORDS:
        out = re.sub(rf"\b{u}\b", " ", out)
    out = re.sub(r"\bof\b", " ", out)
    out = re.sub(r"\s+", " ", out).strip(" .,!?")
    return out


def parse_command(raw_text: str) -> dict:
    """Rule-based intent parser. Returns a dict describing the action."""
    text = (raw_text or "").lower().strip()

    action, trigger = None, ""
    for trig in sorted(REMOVE_TRIGGERS, key=len, reverse=True):
        if trig in text:
            action, trigger = "remove", trig
            break
    if not action:
        for trig in sorted(SEARCH_TRIGGERS, key=len, reverse=True):
            if trig in text:
                action, trigger = "search", trig
                break
    if not action:
        for trig in sorted(ADD_TRIGGERS, key=len, reverse=True):
            if trig in text:
                action, trigger = "add", trig
                break
    if not action:
        action = "add"  # default: bare item name means "add it"

    rest = text.split(trigger, 1)[1] if trigger and trigger in text else text

    # price filter: "under $5" / "less than 5" / "below 5 dollars"
    price_max = None
    m = re.search(r"(?:under|less than|below)\s*\$?(\d+(?:\.\d+)?)", rest)
    if m:
        price_max = float(m.group(1))
        rest = rest[: m.start()] + rest[m.end():]

    # quantity: digits first, then number words
    qty = 1
    m2 = re.search(r"\b(\d+)\b", rest)
    if m2:
        qty = int(m2.group(1))
        rest = rest[: m2.start()] + rest[m2.end():]
    else:
        for w, v in NUM_WORDS.items():
            if re.search(rf"\b{w}\b", rest):
                qty = v
                rest = re.sub(rf"\b{w}\b", " ", rest, count=1)
                break

    item = _strip_fillers(rest)

    return {
        "action": action,
        "item": item,
        "quantity": max(qty, 1),
        "price_max": price_max,
        "raw": raw_text,
    }
