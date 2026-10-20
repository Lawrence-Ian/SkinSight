"""SKINSIGHT v2 — Recommendation Engine"""

RECOMMENDATIONS = {
    "oily": {
        "label": "Oily Skin", "severity": "mild",
        "description": "Your scan shows oily skin. Overactive sebaceous glands produce excess sebum, causing shine and enlarged pores.",
        "morning_routine": ["Foaming or gel cleanser", "Niacinamide toner", "Lightweight water-based serum", "Mattifying oil-free SPF 30+"],
        "night_routine": ["Gentle gel cleanser", "AHA toner 2× per week", "Niacinamide serum"],
        "products": [
            {"name": "Celeteque Hydration Facial Wash", "brand": "Celeteque", "price_range": "₱180–₱300", "ingredient": "Glycerin and mild cleansing agents", "purpose": "Removes daily oil and impurities without a heavy finish", "dermatologist_recommendation": "A practical, affordable option; choose the smallest size first if your skin is sensitive", "image_url": "https://www.watsons.com.ph/medias/10081418_0.jpg?context=bWFzdGVyfGltYWdlc3w1NjQ1NjB8aW1hZ2UvanBlZ3xpbWFnZXMvaDAyL2g1ZS85NDAzNDkzODk5ODcwLmpwZ3wyOTZhOGJhZGU1ZmMwMzQyYmM0YjM4OGQwMjQ2ZDk2ZTg1NDgwYjU0ZTRkNTFiNGE2ODlmY2FkZjYwMmFkMTEy", "product_url": "https://www.watsons.com.ph/celeteque-dermo-science-hydration-facial-wash-100ml/p/BP_10081418"},
            {"name": "Luxe Organix Aloe Vera Facial Cleanser", "brand": "Luxe Organix", "price_range": "₱150–₱250", "ingredient": "Aloe vera and mild cleansing agents", "purpose": "Helps remove excess oil while keeping cleansing gentle", "dermatologist_recommendation": "Use once daily at first and reduce frequency if dryness or stinging develops", "image_url": "https://www.watsons.com.ph/medias/50020852-01.jpg?context=bWFzdGVyfGltYWdlc3wyODMxN3xpbWFnZS9qcGVnfGg5MC9oNTcvMTA0OTkzODAwNjg4NTQvNTAwMjA4NTItMDEuanBnfDY0YzlkMzJjN2QyNTAzOWU3MWM2NzVmZTdhNGE1YjRjYzJiMzhiODE4NzFjM2U4ZmNjNGZkMWQ4MTBmYjFiZjA", "product_url": "https://www.watsons.com.ph/luxe-organix-luxe-organix-99-aloe-vera-vitamin-c-hydrabright-cleanser-120ml/p/BP_50020852"},
            {"name": "Pond's Pure White Facial Foam", "brand": "Pond's", "price_range": "₱120–₱220", "ingredient": "Mild cleansing agents and activated carbon", "purpose": "Cleanses excess sebum and surface impurities", "dermatologist_recommendation": "Avoid over-washing; follow with a lightweight, non-comedogenic moisturizer", "image_url": "https://www.watsons.co.id/medias/307668-01.jpg-1200ftw?context=bWFzdGVyfGltYWdlc3w0Mzc4N3xpbWFnZS9qcGVnfGltYWdlcy9oNDcvaDJkLzg4NzEwMTUwNTI1NzQuanBnfDI1ZTQxNTAzYTJiMGU1OTI2YjVlNTMyMmJlMzA2MzRlMTNiYmJmNjVkNzM3ZTE2ZTkwZGMyODE1ZDQ3MzQ5OWE", "product_url": "https://www.watsons.com.ph/pond-s-pure-white-pollution-out-facial-foam-100g/p/BP_10033141"},
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
            {"name": "Human Nature Nourishing Facial Wash", "brand": "Human Nature", "price_range": "₱180–₱300", "ingredient": "Plant-based cleansing agents and glycerin", "purpose": "Gently cleanses without leaving skin tight", "dermatologist_recommendation": "A budget-friendly gentle option; stop if fragrance or botanical ingredients irritate your skin", "image_url": "https://www.humanheartnature.com/image/cache/data/products/cleanser-nourishing-facial-wash-50ml-500x500-01-660x660.jpg", "product_url": "https://humanheartnature.com/buy/nourishing-facial-wash.html"},
            {"name": "Celeteque Hydration Facial Wash", "brand": "Celeteque", "price_range": "₱180–₱300", "ingredient": "Glycerin and mild cleansing agents", "purpose": "Cleanses while helping maintain skin comfort", "dermatologist_recommendation": "Use lukewarm water and moisturize immediately after cleansing", "image_url": "https://www.watsons.com.ph/medias/10081418_0.jpg?context=bWFzdGVyfGltYWdlc3w1NjQ1NjB8aW1hZ2UvanBlZ3xpbWFnZXMvaDAyL2g1ZS85NDAzNDkzODk5ODcwLmpwZ3wyOTZhOGJhZGU1ZmMwMzQyYmM0YjM4OGQwMjQ2ZDk2ZTg1NDgwYjU0ZTRkNTFiNGE2ODlmY2FkZjYwMmFkMTEy", "product_url": "https://www.watsons.com.ph/celeteque-dermo-science-hydration-facial-wash-100ml/p/BP_10081418"},
            {"name": "Pond's Hydra Light Facial Foam", "brand": "Pond's", "price_range": "₱120–₱220", "ingredient": "Hydrating cleansing agents", "purpose": "Provides an affordable daily cleanse", "dermatologist_recommendation": "Choose a gentle formula and discontinue if skin feels tight after washing", "product_url": "https://www.watsons.com.ph/search?text=pond%27s%20hydra%20light"},
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
            {"name": "Celeteque Hydration Facial Wash", "brand": "Celeteque", "price_range": "₱180–₱300", "ingredient": "Glycerin and mild cleansing agents", "purpose": "Maintains the skin's natural balance", "dermatologist_recommendation": "Choose a gentle option that does not leave skin tight or dry", "image_url": "https://www.watsons.com.ph/medias/10081418_0.jpg?context=bWFzdGVyfGltYWdlc3w1NjQ1NjB8aW1hZ2UvanBlZ3xpbWFnZXMvaDAyL2g1ZS85NDAzNDkzODk5ODcwLmpwZ3wyOTZhOGJhZGU1ZmMwMzQyYmM0YjM4OGQwMjQ2ZDk2ZTg1NDgwYjU0ZTRkNTFiNGE2ODlmY2FkZjYwMmFkMTEy", "product_url": "https://www.watsons.com.ph/celeteque-dermo-science-hydration-facial-wash-100ml/p/BP_10081418"},
            {"name": "Human Nature Nourishing Facial Wash", "brand": "Human Nature", "price_range": "₱180–₱300", "ingredient": "Plant-based cleansing agents and glycerin", "purpose": "Supports a comfortable daily cleansing routine", "dermatologist_recommendation": "Patch test first if you are sensitive to botanical ingredients", "image_url": "https://www.humanheartnature.com/image/cache/data/products/cleanser-nourishing-facial-wash-50ml-500x500-01-660x660.jpg", "product_url": "https://humanheartnature.com/buy/nourishing-facial-wash.html"},
            {"name": "Pond's Bright Beauty Facial Foam", "brand": "Pond's", "price_range": "₱120–₱220", "ingredient": "Mild cleansing agents and vitamin B3", "purpose": "Provides an accessible daily cleanser for balanced skin", "dermatologist_recommendation": "Avoid scrubbing and moisturize if skin feels dry after washing", "product_url": "https://www.watsons.com.ph/pond-s-bright-miracle-facial-wash-100g/p/BP_10066002"},
        ],
        "preventive_tips": ["SPF daily — UV is the #1 skin ager", "Gentle exfoliation 1–2×/week", "Introduce new products one at a time", "Stay consistent"],

        "ingredients_to_avoid": [],
        "consult_dermatologist": False,
    },
}

def get_recommendation(condition: str) -> dict:
    return RECOMMENDATIONS.get(condition, RECOMMENDATIONS["normal"])
