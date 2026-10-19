"""
SKINSIGHT v2 — Analysis API
Accepts a base64-encoded JPEG frame captured from the live camera.
File uploads are explicitly rejected.
"""

import json, base64, sys, os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, ScanHistory, UserProfile, persist_scan_recommendations
from app.api.dependencies import require_user
from app.services.recommendations import get_recommendation

router = APIRouter()

# ── Lazy-load predictor ───────────────────────────────────────────────────────
_predictor = None

def get_predictor():
    global _predictor
    if _predictor is None:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ml"))
            from ml.skin_model import SkinPredictor
            _predictor = SkinPredictor()
        except Exception:
            class MockPredictor:
                def predict(self, image_bytes):
                    import random
                    classes = ["oily", "dry", "normal"]
                    random.seed(len(image_bytes) % 97)
                    raw = [random.uniform(0.05, 0.9) for _ in classes]
                    raw[len(image_bytes) % len(classes)] *= 2.8
                    total = sum(raw)
                    scores = {c: round(r/total, 4) for c, r in zip(classes, raw)}
                    condition = max(scores, key=scores.get)
                    return {"condition": condition, "confidence": scores[condition],
                            "all_scores": scores, "using_mock": True, "error": None}
            _predictor = MockPredictor()
    return _predictor


# ── Request model ─────────────────────────────────────────────────────────────
class LiveScanRequest(BaseModel):
    frame: str          # base64-encoded JPEG from webcam capture
    source: str = "live_camera"


# ── Main scan endpoint ────────────────────────────────────────────────────────
@router.post("/scan")
async def scan_live_frame(
    body: LiveScanRequest,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Accept a base64 JPEG frame from the live camera feed and run CNN inference.
    Only 'live_camera' source is accepted — file uploads go nowhere.
    """

    # Enforce live-camera source
    if body.source != "live_camera":
        raise HTTPException(status_code=400,
            detail="Only live camera captures are accepted. File uploads are not permitted.")

    # Decode base64 frame
    try:
        # Strip data-URI prefix if present
        frame_data = body.frame
        if "," in frame_data:
            frame_data = frame_data.split(",", 1)[1]
        image_bytes = base64.b64decode(frame_data)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid base64 image data.")

    if len(image_bytes) < 3000:
        raise HTTPException(status_code=422, detail="Frame too small. Please ensure your camera is working.")
    if len(image_bytes) > 10_000_000:
        raise HTTPException(status_code=422, detail="Frame too large.")

    # Run prediction
    predictor = get_predictor()
    result = predictor.predict(image_bytes)

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    condition   = result["condition"]
    confidence  = result["confidence"]
    all_scores  = result["all_scores"]
    rec         = get_recommendation(condition)

    try:
        scan = ScanHistory(
            user_id=user["user_id"],
            condition=condition,
            confidence=confidence,
            all_predictions=json.dumps(all_scores),
            source="live_camera",
            created_at=datetime.utcnow(),
        )
        db.add(scan)
        db.flush()

        profile = db.query(UserProfile).filter_by(user_id=user["user_id"]).first()
        if profile is None:
            profile = UserProfile(user_id=user["user_id"])
            db.add(profile)
        profile.skin_type = condition

        persist_scan_recommendations(db, scan, condition, rec["products"])

        db.commit()
        db.refresh(scan)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the analysis. Please try again.",
        ) from exc

    return JSONResponse({
        "scan_id":              scan.id,
        "condition":            condition,
        "condition_label":      rec["label"],
        "confidence":           confidence,
        "confidence_percent":   round(confidence * 100, 1),
        "all_scores":           all_scores,
        "severity":             rec["severity"],
        "description":          rec["description"],
        "morning_routine":      rec["morning_routine"],
        "night_routine":        rec["night_routine"],
        "products":             rec["products"],
        "preventive_tips":      rec["preventive_tips"],

        "ingredients_to_avoid": rec.get("ingredients_to_avoid", []),
        "consult_dermatologist":rec["consult_dermatologist"],
        "first_aid_tips":       rec.get("first_aid_tips", []),
        "emergency_note":       rec.get("emergency_note"),
        "using_mock_model":     result.get("using_mock", True),
        "source":               "live_camera",
        "timestamp":            scan.created_at.isoformat(),
    })
