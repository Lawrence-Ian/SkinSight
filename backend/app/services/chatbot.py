"""SKINSIGHT v2 — Advanced Health-Aware Chatbot"""
import re, random

# Emergency keywords that require professional help (DERMATOLOGY-FOCUSED)
EMERGENCY_KEYWORDS = [
    r"severe.*rash|rash.*severe|spreading.*rash|rash.*spreading",
    r"anaphylax|allergic reaction.*skin|severe.*allergic.*skin",
    r"skin.*infection|infected.*skin|abscess|sepsis.*skin",
    r"severe.*burn|chemical.*burn|thermal.*burn|sunburn.*severe",
    r"oozing|pus|discharge.*yellow|discharge.*green|wound.*infected",
    r"itching.*uncontrollable|unbearable.*itch|severe.*itching",
    r"bleeding.*skin|skin.*bleeding.*profuse|hemorrhag.*skin",
    r"hives.*severe|urticaria.*spread|swelling.*face|swelling.*lips",
    r"necrosis|tissue.*death|skin.*blackening|gangrene",
    r"lesion.*changing.*rapidly|mole.*bleeding|mole.*growing.*fast",
    r"acne.*cystic.*severe|cystic.*acne.*scarring|acne.*emergency",
    r"Stevens.*Johnson|toxic.*epidermal|TEN syndrome",
    r"pemphigus|bullous.*pemphigoid|severe.*blistering",
]

# Confidential/sensitive keywords requiring professional consultation
SENSITIVE_KEYWORDS = [
    r"std|stis?|sti|hiv|herpes|genital|sexual.*health|contraception|pregnancy|pregnant|abortion|miscarriage",
    r"mental health|depression|anxiety|bipolar|ocd|ptsd|eating disorder|addiction",
    r"prescription|medication|drug|controlled substance|narcotic",
    r"surgery|procedure|dermatology|laser|injectable",
    r"cancer|malignant|carcinoma|tumor|oncology",
    r"serious condition|chronic disease|cardiovascular|diabetes|hypertension",
]

# Health sources reference
HEALTH_SOURCES = {
    "dermatology": [
        "American Academy of Dermatology (aad.org)",
        "Mayo Clinic Dermatology (mayoclinic.org)",
        "WebMD Dermatology (webmd.com)",
    ],
    "skincare": [
        "NIH Skincare Guidelines (pubmed.ncbi.nlm.nih.gov)",
        "Mayo Clinic Skincare Tips (mayoclinic.org)",
        "American Academy of Dermatology Resources",
    ],
    "health": [
        "Mayo Clinic (mayoclinic.org)",
        "WebMD (webmd.com)",
        "CDC - Centers for Disease Control (cdc.gov)",
        "NIH - National Institutes of Health (nih.gov)",
        "NHS - National Health Service (nhs.uk)",
    ],
}

RULES = {
    # Greeting & Introduction
    r"hello|hi|hey|greetings": [
        "Hi! 🌸 I'm Sage, your SKINSIGHT skincare assistant. I provide health information based on legitimate sources like Mayo Clinic, AAD, and CDC. Ask me about skincare, ingredients, or routines — or go to the Scan tab to analyze your skin live!",
        "Hello! 🌸 How can I help your skin today? I can discuss skincare routines, ingredients, and conditions based on medical sources.",
    ],

    # Acne & Breakouts
    r"acne|pimple|breakout|zit|whitehead|blackhead": [
        "Acne Management (Based on AAD & Mayo Clinic) 🔍\n\n**What Causes It:**\n• Excess sebum + dead skin cells + bacteria (C. acnes)\n• Hormones, stress, diet (high glycemic index)\n\n**Treatment Options:**\n• Salicylic acid 0.5–2%: Unclogs pores\n• Benzoyl peroxide 2.5–5%: Kills bacteria\n• Niacinamide 10%: Reduces sebum\n• Retinoids: Prevent clogging\n\n**Prevention:**\n• Change pillowcases every 2 days\n• NEVER pop pimples (risk of scarring & infection)\n• Use non-comedogenic products\n• Don't skip moisturizer\n\n**When to see a dermatologist:** If moderate acne persists after 8–12 weeks of OTC treatment.\n\nSource: American Academy of Dermatology",
    ],

    # Oily Skin
    r"oily|shine|greasy|sebum|enlarged pore": [
        "Oily Skin Management 🛢️\n\n**Causes:**\n• Overactive sebaceous glands\n• Genetics, hormones, humidity\n\n**Treatment (Evidence-Based):**\n• **Cleanser:** Foaming or gel (salicylic acid 0.5–1%)\n• **Serum:** Niacinamide 10% (clinically proven to ↓ sebum)\n• **Mask:** Kaolin/bentonite clay (1–2×/week)\n• **Toner:** Alcohol-free with glycerin\n\n**Moisturize!** Dehydrated skin overproduces oil.\n\n**Avoid:** Heavy oils, petrolatum, SPF products (use oil-free)\n\n**Note:** Don't over-wash. 1–2×/day maximum. More stripping = more oil rebound.\n\nSource: Mayo Clinic Dermatology",
    ],

    # Dry Skin
    r"dry|flaky|tight|dehydrat|eczema|dermatitis": [
        "Dry Skin Care 💧\n\n**Root Causes:**\n• Compromised skin barrier (ceramide deficiency)\n• Low humidity, harsh cleansing, genetic predisposition\n\n**Treatment (Dermatologist-Approved):**\n• **Cleanser:** Gentle, ceramide-rich (hydrating, not foaming)\n• **Hydration:** Hyaluronic acid on DAMP skin (key!)\n• **Repair:** Ceramides, niacinamide, peptides\n• **Moisturizer:** Rich cream with occlusive ingredients\n• **SPF:** Sunscreen with moisturizing base\n\n**Technique Matters:**\n• Use lukewarm water (NEVER hot)\n• Pat dry gently (don't rub)\n• Moisturize within 60 seconds of washing\n• Use humidifier at night\n\n**See a dermatologist if:** Flaking persists, itching interferes with sleep, or signs of infection appear.\n\nSource: Mayo Clinic, National Eczema Association",
    ],

    # Sunscreen & UV Protection
    r"sunscreen|spf|uv.*protect|sun.*screen|photodamage": [
        "Sunscreen & UV Protection ☀️ [CRITICAL]\n\n**Why SPF Matters:**\n• UV exposure = 80–90% of visible aging\n• Causes wrinkles, age spots, skin cancer risk\n\n**The Right Approach:**\n• **SPF 30+ minimum** (blocks ~97% UVB)\n• **Broad-spectrum:** Protects from UVA + UVB\n• **Daily apply:** Even indoors (glass doesn't block UVA)\n• **Reapply:** Every 2 hours if outside\n• **Amount:** ~1/4 teaspoon for face\n\n**Types:**\n• **Chemical (organic):** Absorbs UV (avobenzone, oxybenzone)\n• **Mineral (physical):** Reflects UV (zinc oxide, titanium dioxide)\n  - Better for: Sensitive skin, pregnancy\n\n**Doctor's Note:** No sunscreen is 100% effective. Limit peak sun (10am–4pm), wear protective clothing.\n\nSource: American Academy of Dermatology, CDC, Mayo Clinic",
    ],

    # Vitamin C & Antioxidants
    r"vitamin c|vitamin.*c|brightening|dark spot|hyperpigment|antioxidant": [
        "Vitamin C & Brightening Actives 🍊\n\n**How It Works:**\n• Neutralizes free radicals (oxidative stress)\n• Boosts collagen synthesis\n• Reduces melanin (fades dark spots & melasma)\n• Brightens dull skin\n\n**Best Formulation:**\n• **L-Ascorbic Acid 10–20%** at pH 2–3.5 (most bioavailable)\n• Alternative: Stabilized derivatives (SAP, MAP) — more stable, slightly less potent\n• **Apply:** Morning, before sunscreen\n\n**Storage Crucial:** Oxidizes in light/air\n✓ Opaque, airtight bottle\n✓ Dark, cool storage\n✓ Replace after 3–6 months\n\n**Results Timeline:** 4–12 weeks for visible brightening\n\n**Note:** Efficacy disputed if concentration <10%. Choose clinical-strength brands.\n\nSource: Journal of Cosmetic Dermatology, Mayo Clinic",
    ],

    # Retinoids
    r"retinol|retinoid|tretinoin|adapalene|tazarotene|anti.*aging|wrinkle|fine line": [
        "Retinoids Explained 🌙\n\n**What They Do:**\n• Increase cell turnover (reveals fresh skin)\n• Stimulate collagen production\n• Reduce fine lines & wrinkles\n• Fade acne & hyperpigmentation\n• Most evidence-backed anti-aging ingredient\n\n**Types (Weakest → Strongest):**\n1. **Retinyl Palmitate** (weakest, OTC)\n2. **Retinol** (OTC, 0.3–1%)\n3. **Retinaldehyde** (prescription-strength effects)\n4. **Adapalene** (Differin — OTC retinoid, gentler)\n5. **Tretinoin** (Retin-A — prescription, strongest)\n6. **Isotretinoin** (Accutane — severe acne only, serious side effects)\n\n**How to Start:**\n• Begin with **0.025–0.3% retinol** 2×/week\n• Gradually increase frequency over 4–8 weeks\n• Use ONLY at night\n• ALWAYS apply SPF 30+ next morning\n• Expect: Redness, peeling, purging (temporary)\n\n**Results:** 8–16 weeks for visible improvement\n\n**Pregnancy:** AVOID retinoids entirely (teratogenic)\n\n**See a dermatologist if:** Severe irritation, rash, or no improvement after 12 weeks.\n\nSource: American Academy of Dermatology, Dermatologic Surgery journal",
    ],

    # Hyaluronic Acid
    r"hyaluronic|hydrat|moisture|moisturiz": [
        "Hyaluronic Acid (HA) 💧\n\n**The Magic:**\n• Holds UP TO 1000× its weight in water\n• Works for ALL skin types (including oily)\n• Non-comedogenic\n\n**How to Use It Right:**\n• **Apply to DAMP skin** (crucial!) — attracts water from air/moisturizer\n• Layer directly after toning\n• Follow with moisturizer to seal\n\n**Myth:** HA dehydrates skin if applied to dry skin\n✓ **Reality:** It needs moisture to work. Damp skin = effective hydration boost.\n\n**Weights Matter:**\n• Low MW (under 50kDa): Penetrates deeper\n• High MW (over 50kDa): Surface hydration\n• Ideal: Mixed-weight formulas\n\n**Best Used In:** Toners, serums, essences (lightweight)\n\n**Stacks Well With:** Glycerin, ceramides, niacinamide\n\nSource: Journal of Cosmetic Dermatology & Mayo Clinic",
    ],

    # Map Feature - Nearest Clinics & Stores
    r"map|clinic.*nearest|store.*nearest|dermatologist.*near|find.*clinic|find.*store|nearest.*dermatology": [
        "🗺️ **MAP ACTIVATED!** Finding your nearest dermatology clinic for consultation and stores to buy recommended products. Navigate to **Map** tab now! 📍",
    ],

    # Skin Lesions & Concerning Moles
    r"lesion|mole|spot|melanoma|growth|nevus|carcinoma|skin cancer": [
        "For concerns about moles or skin growths, please consult a board-certified dermatologist. They can properly evaluate and monitor any skin changes. Regular skin checks are important for early detection of any issues. 🏥",
    ],

    # Skincare Routine Order
    r"routine|steps|order|sequence|how.*apply": [
        "Perfect Skincare Routine Order 🧴\n\n**☀️ MORNING ROUTINE:**\n1. **Cleanser** (remove overnight oil/dead skin)\n2. **Toner** (balance pH, prep for absorption)\n3. **Serum/Active** (vitamin C, niacinamide — penetrates first)\n4. **Eye Cream** (optional, gentle formula)\n5. **Moisturizer** (hydrate & protect barrier)\n6. **SPF 30+** (ALWAYS — mineral or chemical)\n\n**🌙 NIGHT ROUTINE:**\n1. **First Cleanse** (oil cleanser removes makeup/sunscreen)\n2. **Second Cleanse** (water-based cleanser for deeper clean)\n3. **Toner** (restore pH)\n4. **Treatment/Active** (retinol, BHA, AHA — works best at night)\n5. **Moisturizer** (richer formula okay at night)\n6. **Eye Cream** (optional)\n7. **Overnight Mask** (optional, for extra hydration)\n\n**Pro Tips:**\n• **Wait 1–2 minutes** between steps for absorption\n• **5 consistent steps beat 15 random ones**\n• **Introduce ONE new product** every 2 weeks (monitor for reactions)\n• **Patch test** new actives on inner arm first\n\n**Key Principle:** Lightest to heaviest (thinnest to thickest texture)\n\nSource: AAD Skincare Guidelines, Mayo Clinic",
    ],

    # How SKINSIGHT Works
    r"scan|camera|how.*work|analyze|cnn|model|detection": [
        "How SKINSIGHT Works 📱\n\n**Live Camera Technology:**\n• Uses CNN (Convolutional Neural Network) model\n• Analyzes your live camera frame in REAL-TIME\n• No photo uploads — processing happens locally\n\n**What SKINSIGHT Detects:**\n✓ Acne-prone skin\n✓ Oily skin\n✓ Dry skin\n✓ Normal/balanced skin\n\n**How to Scan:**\n1. Tap the **Scan** tab 📸\n2. Allow camera permission\n3. Position your face in the oval guide\n4. Ensure good lighting\n5. Hold still & tap **Capture**\n\n**After Scan:**\n✓ Instant condition detection + confidence % \n✓ Personalized routine (morning/night steps)\n✓ Branded product recommendations\n✓ Professional tips based on dermatology sources\n✓ Scan saved to your history\n\n**Important Note:**\n⚠️ SKINSIGHT is a **screening tool**, not a diagnostic tool. For persistent skin issues, consult a board-certified dermatologist.\n\nSource: SKINSIGHT Medical Team",
    ],

    # Nutrition & Diet
    r"diet|food|eat|nutrition|carb|sugar|dairy|omega": [
        "Food & Skin Health 🥗\n\n**Evidence-Based Connections:**\n\n**Omega-3 Fatty Acids** ✓ Reduces inflammation\n• Sources: Salmon, sardines, walnuts, flaxseed\n• Helps: Acne, rosacea, eczema\n\n**Antioxidants** ✓ Fights free radical damage\n• Sources: Berries, dark chocolate, green tea\n• Helps: Premature aging, sun damage\n\n**Glycemic Index & Acne:**\n• High-GI foods (white bread, sugar) → ↑ insulin → ↑ sebum → acne (for susceptible individuals)\n• Choose: Whole grains, legumes, vegetables\n\n**Dairy Debate:**\n• **Milk** (not yogurt/cheese) linked to acne in some studies\n• Likely due to hormones in conventional milk\n• Effect varies by individual\n\n**Hydration** ✓ Essential\n• Aim: 2–3L water daily\n• Supports skin elasticity & detoxification\n\n**What the Research Shows:**\nNo single food \"causes\" breakouts, but overall diet quality matters. Mediterranean diet (fish, vegetables, olive oil) shows best skin benefits.\n\n**Takeaway:** No elimination needed, but balance matters.\n\nSource: Journal of Dermatology, Mayo Clinic Nutrition",
    ],

    # Sleep & Recovery
    r"sleep|rest|tiredness|fatigue|beauty.*sleep": [
        "Sleep & Skin Recovery 😴\n\n**Why Sleep Matters:**\n• Skin **peaks repair mode from 11pm–2am** (peak cell turnover)\n• During sleep: ↑ blood flow to skin, ↑ collagen synthesis\n• Sleep deprivation → ↑ cortisol → breakouts, inflammation\n\n**The Research:**\n• Poor sleep linked to increased acne, reduced barrier function\n• Sleep-deprived skin has lower moisture retention\n• Dark circles become permanent without adequate sleep\n\n**Sleep Skincare Hack:**\n• Use night creams/retinoids during sleep (optimal efficacy)\n• Silk pillowcase reduces friction (less wrinkles, breakage)\n• Sleep on back to prevent sleep crease wrinkles\n\n**Optimal Schedule:**\n• **7–9 hours nightly** (dermatologist recommendation)\n• Consistent bedtime/wake time\n\n**Reality Check:**\nYes, beauty sleep is real. But no amount of skincare fixes poor sleep. Prioritize zzz's.\n\nSource: Sleep journal, Mayo Clinic, AAD",
    ],

    # Stress & Mental Health
    r"stress|anxiety|mental.*health|cortisol|breakout.*stress|emotional": [
        "🧠 Stress & Skin Connection\n\n**The Science:**\n• Stress → ↑ cortisol → ↑ sebum, ↑ inflammation → acne flare\n• Stress impairs skin barrier function\n• Immune suppression → slower healing\n\n**Manage It:**\n• **Exercise:** 30 mins, any kind (↓ cortisol, ↑ endorphins)\n• **Meditation:** Even 5–10 mins daily improves skin (clinically studied)\n• **Sleep:** 7–9 hours (see above)\n• **Journaling:** Write out worries (↓ stress response)\n\n**When to Seek Help:**\nIf stress is severe, persistent, or affecting your daily life → **Consult a mental health professional**. Your skin reflects your overall wellness.\n\n**Reality:** Skincare alone won't fix stress-triggered breakouts. Address the root cause.\n\nSource: Journal of Cosmetic Dermatology, Mayo Clinic",
    ],

    # Routine & Consistency
    r"consistency|how.*long|when.*see.*result|patience|improvement": [
        "Results Timeline & Expectations 📅\n\n**Realistic Timeframes (Based on Studies):**\n• **Hydration:** 1–2 weeks (plumper, glowing skin)\n• **Acne prevention (cleansers):** 4–8 weeks\n• **Vitamin C brightening:** 6–12 weeks\n• **Retinol anti-aging:** 8–16 weeks\n• **Full barrier repair:** 4–6 weeks (with proper care)\n\n**What's NOT Realistic:**\n✗ Results in 1 week (superficial trends only)\n✗ Overnight wrinkle removal\n✗ Erasing scars with topicals alone\n✗ One product fixing everything\n\n**The Golden Rule:**\n**✓ Consistency beats perfection.**\n5 consistent steps > 15 inconsistent products\n\n**Tracking Progress:**\n• Take baseline photos (good lighting, same angle, weekly)\n• Give each product 4–6 weeks minimum\n• Change ONE product at a time\n\n**Dermatologist's Perspective:**\nIf no improvement after 8–12 weeks of consistent OTC treatment → Professional help (prescription options, professional treatments exist).\n\nSource: Journal of Cosmetic Dermatology, AAD",
    ],

    # Ingredients Explained
    r"ingredient|bha|aha|salicylic|glycolic|chemical.*peel": [
        "Skincare Acids Explained 🧪\n\n**BHA (Beta Hydroxy Acid) — Salicylic Acid:**\n• Oil-soluble → penetrates pores deeply\n• Unclogs clogged pores, dissolves sebum\n• **Best for:** Acne, oily skin, blackheads\n• **Strength:** 0.5–2%\n• **Frequency:** 2–5× weekly (build up frequency)\n• **Caution:** Can be irritating; don't combine with retinoids (at first)\n\n**AHA (Alpha Hydroxy Acid) — Glycolic, Lactic Acid:**\n• Water-soluble → surface exfoliation\n• Removes dead skin, brightens, evens texture\n• **Best for:** Dry skin, dull skin, surface hyperpigmentation\n• **Strength:** 5–10%\n• **Frequency:** 1–3× weekly\n• **Note:** Causes photosensitivity; MUST use SPF\n\n**Combination Warning:** ⚠️ Don't mix BHA + AHA daily\n✓ Use on alternate nights or Rotate Weekly\n✓ Sandwich irritated skin: Moisturizer → Acid → Moisturizer\n\n**Signs of Over-Exfoliation:**\n✗ Redness, burning, peeling, flaking\n✗ Barrier damage (dry, sensitive)\n→ Cut back frequency immediately\n\n**Best Brands (Efficacy-Based):**\nCheck: Niacinamide support, pH 2–4, clinical studies\n\nSource: Journal of Cosmetic Dermatology, AAD Guidelines",
    ],

    # Product Selection
    r"recommend|product|brand|which.*best|best.*product": [
        "Product Recommendation Guide 🛍️\n\n**How to Choose:**\n\n1. **Identify Your Skin Type:**\n   • Oily, Combination, Dry, Sensitive, Normal\n   • Take SKINSIGHT scan for personalized results\n\n2. **Look for Clinical Evidence:**\n   • Published studies (PubMed, dermatology journals)\n   • Established brands with research teams\n   • FDA-cleared claims (if medical-grade)\n\n3. **Check Ingredients:**\n   • Effective concentrations matter more than buzzwords\n   • Compare: Vitamin C (10%+ L-Ascorbic), Retinol (0.3–1%)\n   • Avoid: Denatured alcohol, fragrance (if sensitive)\n\n4. **Watch Price ≠ Efficacy:**\n   • High price doesn't = better results\n   • CeraVe, Cetaphil, Neutrogena have strong science\n\n5. **Patch Test:**\n   • New product? Test on jaw/inner arm 1–2 days\n   • Wait 2 weeks between new products\n\n**Red Flags:**\n✓ Unproven miracle claims\n✗ No ingredient list\n✗ Only Instagram testimonials (fake reviews common)\n✗ Contradicts dermatology guidelines\n\n**SKINSIGHT Recommendations:**\nAfter your scan, we provide specific branded products backed by dermatologist research.\n\nSource: AAD, Mayo Clinic, Evidence-based Dermatology",
    ],

    # General Thanks
    r"thank|thanks|appreciate": [
        "You're welcome! 🌸 Consistent skincare + professional guidance = glowing results!",
        "Happy to help! Remember: SPF daily & see a dermatologist for persistent issues. 💪",
    ],

    # Goodbye
    r"bye|goodbye|see.*you|talk.*later": [
        "Bye! Don't forget your SPF today ☀️ See you in Scan! 🌸",
        "Take care! Your skin deserves dermatology-backed care 💚",
    ],

    # About SKINSIGHT
    r"skinsight|about|who.*you|what.*app": [
        "About SKINSIGHT 🌸\n\nSKINSIGHT is an **AI-powered skin analysis app** designed for:\n✓ Live skin condition detection (acne-prone, oily, dry, normal/balanced)\n✓ Personalized skincare routines\n✓ Branded product recommendations from dermatologist sources\n✓ Scan history tracking\n\n**I'm Sage, your AI skincare assistant:**\n✓ Provide info based on legitimate health sources (Mayo Clinic, AAD, CDC, NIH, WebMD)\n✓ Recommend professional help for health emergencies or sensitive topics\n✓ Support your journey to healthy skin\n\n**Important:** SKINSIGHT is a screening & educational tool, NOT a medical diagnostic tool. For serious skin concerns, consult a board-certified dermatologist.\n\n🌸 Your skin health matters. Let's care for it together.",
    ],
}

def detect_emergency(message: str) -> bool:
    """Check if message indicates emergency requiring immediate professional help."""
    msg = message.lower()
    for pattern in EMERGENCY_KEYWORDS:
        if re.search(pattern, msg, re.IGNORECASE):
            return True
    return False

def detect_sensitive_topic(message: str) -> bool:
    """Check if message is about confidential/sensitive health topics."""
    msg = message.lower()
    for pattern in SENSITIVE_KEYWORDS:
        if re.search(pattern, msg, re.IGNORECASE):
            return True
    return False

EMERGENCY_RESPONSE = """
⚠️ DERMATOLOGICAL EMERGENCY DETECTED ⚠️

This appears to be a serious skin condition requiring immediate professional evaluation.

**Seek immediate care if:**
🚨 Severe spreading rash
🚨 Signs of skin infection (pus, oozing, discharge)
🚨 Severe allergic reaction affecting skin
🚨 Severe burns or chemical exposure
🚨 Rapid changes to moles or lesions
🚨 Severe blistering or tissue damage

**What to do NOW:**
👨‍⚕️ **Call your dermatologist immediately** — many offer urgent appointments
🏥 Visit an urgent care or emergency room
📞 Call 911 if symptoms worsen rapidly

**For telemedicine:** Dermatology-specific platforms like DermCheck or Doctor on Demand can provide emergency consultations.

I'm an AI skincare assistant and cannot diagnose or treat medical emergencies. A board-certified dermatologist must evaluate this. Please seek professional help now.
"""

SENSITIVE_RESPONSE = """
⚠️ SENSITIVE/CONFIDENTIAL TOPIC ⚠️

This topic requires professional medical, mental health, or legal guidance that I cannot provide.

**Please consult:**
👨‍⚕️ **Medical:** Board-certified dermatologist or primary care physician
🧠 **Mental Health:** Licensed therapist, counselor, or psychiatrist
📞 Call your doctor to schedule an appointment
💬 Use secure patient portals or HIPAA-compliant telemedicine

**Crisis Resources:**
• National Suicide Prevention Lifeline: 988 (US)
• Crisis Text Line: Text HOME to 741741
• SAMHSA National Helpline: 1-800-662-HELP (4357)

I'm here for general skincare info. For health concerns, professionals are best equipped to help. 🌸
"""

FALLBACKS = [
    "Great question! While I specialize in skincare, I'd recommend consulting a dermatologist for detailed guidance. In the meantime, try taking a SKINSIGHT scan! 😊",
    "Hmm, that's beyond my skincare expertise. A dermatologist or healthcare provider can give you the best answer. Want to learn about routines or ingredients instead? 🌸",
    "I'm not able to answer that with certainty. For personalized health advice, please consult a licensed healthcare professional. How can I help with your skincare routine?",
]

def get_bot_response(message: str) -> dict:
    """Get chatbot response with safety checks."""
    
    # Check for emergency first
    if detect_emergency(message):
        return {
            "response": EMERGENCY_RESPONSE,
            "type": "emergency",
            "matched": True
        }
    
    # Check for sensitive/confidential topics
    if detect_sensitive_topic(message):
        return {
            "response": SENSITIVE_RESPONSE,
            "type": "sensitive",
            "matched": True
        }
    
    # Standard rule-based matching
    msg = message.lower().strip()
    for pattern, responses in RULES.items():
        if re.search(pattern, msg, re.IGNORECASE):
            return {
                "response": random.choice(responses),
                "type": "matched",
                "matched": True
            }
    
    # Fallback for unknown questions
    return {
        "response": random.choice(FALLBACKS),
        "type": "fallback",
        "matched": False
    }
