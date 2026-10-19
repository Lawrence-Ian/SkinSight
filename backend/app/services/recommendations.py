"""SKINSIGHT v2 — Recommendation Engine"""

RECOMMENDATIONS = {
    "acne": {
        "label": "Acne-Prone Skin", "severity": "moderate",
        "description": "Your live scan suggests acne-prone skin. Acne forms when hair follicles clog with oil and dead skin cells.",
        "morning_routine": ["Gentle foaming cleanser (salicylic acid 0.5–2%)", "Alcohol-free niacinamide toner", "Lightweight oil-free moisturizer", "Broad-spectrum SPF 30+ (gel or fluid)"],
        "night_routine": ["Micellar water pre-cleanse + salicylic acid cleanser", "BHA exfoliant 2–3× per week", "Benzoyl peroxide spot treatment (2.5–5%)", "Oil-free hydrating gel moisturizer"],
        "products": [
            {"name": "Affordable salicylic acid cleanser", "price_range": "₱100–₱300", "ingredient": "Salicylic Acid 0.5–2%", "purpose": "Helps unclog pores", "dermatologist_recommendation": "Choose a gentle, non-comedogenic option and stop if irritation occurs"},
        ],
        "preventive_tips": ["Change pillowcases every 2–3 days", "Never touch your face with unwashed hands", "Keep hair products away from forehead", "Clean your phone screen daily"],

        "ingredients_to_avoid": ["Coconut oil", "Isopropyl myristate", "Lanolin"],
        "consult_dermatologist": False,
    },
    "oily": {
        "label": "Oily Skin", "severity": "mild",
        "description": "Your scan shows oily skin. Overactive sebaceous glands produce excess sebum, causing shine and enlarged pores.",
        "morning_routine": ["Foaming or gel cleanser", "Niacinamide toner", "Lightweight water-based serum", "Mattifying oil-free SPF 30+"],
        "night_routine": ["Gentle gel cleanser", "AHA toner 2× per week", "Niacinamide serum"],
        "products": [
            {"name": "Affordable foaming or gel cleanser", "price_range": "₱100–₱300", "ingredient": "Zinc PCA or Salicylic Acid", "purpose": "Removes excess oil", "dermatologist_recommendation": "Choose an oil-free, non-comedogenic option"},
        ],
        "preventive_tips": ["Blotting papers > powder throughout the day", "Avoid over-washing (worsens oiliness)", "Lukewarm water only", "Minimal product layering"],

        "ingredients_to_avoid": ["Heavy oils", "Petrolatum in large amounts"],
        "consult_dermatologist": False,
    },
    "dry": {
        "label": "Dry Skin", "severity": "mild",
        "description": "Your scan indicates dry skin. The skin barrier is compromised, leading to tightness, flaking, and sensitivity.",
        "morning_routine": ["Creamy gentle cleanser", "Ceramide hydrating toner", "Hyaluronic acid serum on damp skin", "Rich ceramide moisturizer", "Moisturizing SPF 30+"],
        "night_routine": ["Oil or balm cleanser", "Glycerin hydrating toner", "Peptide serum or low-strength retinol (0.025%) 2×/week", "Rich night cream with ceramides"],
        "products": [
            {"name": "Affordable gentle hydrating cleanser", "price_range": "₱100–₱350", "ingredient": "Glycerin or Ceramides", "purpose": "Cleanses without stripping", "dermatologist_recommendation": "Choose a fragrance-free, creamy cleanser for dry or sensitive skin"},
        ],
        "preventive_tips": ["Use a bedroom humidifier at night", "Lukewarm — never hot — showers", "Pat dry, never rub", "Moisturize within 60 seconds of washing"],

        "ingredients_to_avoid": ["Alcohol denat", "Fragrance/parfum", "SLS"],
        "consult_dermatologist": False,
    },
    "normal": {
        "label": "Normal / Balanced Skin", "severity": "none",
        "description": "Excellent! Your skin appears balanced and healthy. Focus on maintenance and long-term prevention.",
        "morning_routine": ["Gentle pH-balanced cleanser", "Vitamin C antioxidant serum", "Lightweight moisturizer", "Broad-spectrum SPF 30+"],
        "night_routine": ["Gentle cleanser", "Retinol serum (0.025–0.1%) 2–3×/week", "Lightweight moisturizer"],
        "products": [
            {"name": "Affordable gentle pH-balanced cleanser", "price_range": "₱100–₱300", "ingredient": "Amino Acids or Glycerin", "purpose": "Maintains the skin's natural balance", "dermatologist_recommendation": "Choose a gentle option that does not leave skin tight or dry"},
        ],
        "preventive_tips": ["SPF daily — UV is the #1 skin ager", "Gentle exfoliation 1–2×/week", "Introduce new products one at a time", "Stay consistent"],

        "ingredients_to_avoid": [],
        "consult_dermatologist": False,
    },
}

def get_recommendation(condition: str) -> dict:
    return RECOMMENDATIONS.get(condition, RECOMMENDATIONS["normal"])
