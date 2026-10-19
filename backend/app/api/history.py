"""SKINSIGHT v2 — History API"""
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.dependencies import require_user
from app.database import get_db, RoutineProgress, ScanHistory
from app.services.recommendations import get_recommendation

router = APIRouter()

class RoutineProgressUpdate(BaseModel):
    morning: list[int] = Field(default_factory=list)
    night: list[int] = Field(default_factory=list)


def _saved_products(scan):
    recommendations = get_recommendation(scan.condition)["products"]
    current_products = {product["name"]: product for product in recommendations}
    saved = []
    for recommendation in scan.recommendations:
        product = recommendation.product
        if product is None:
            continue
        catalog_product = current_products.get(product.name)
        if catalog_product is None or product.brand:
            return recommendations
        saved.append({
            "name": product.name,
            "ingredient": product.ingredients,
            "purpose": product.description,
            "price_range": catalog_product["price_range"],
            "dermatologist_recommendation": recommendation.recommendation_reason,
        })
    return saved or recommendations

@router.get("/")
async def get_history(user=Depends(require_user), db: Session = Depends(get_db)):
    scans = (db.query(ScanHistory)
             .filter(ScanHistory.user_id == user["user_id"])
             .order_by(ScanHistory.created_at.desc()).limit(50).all())
    return JSONResponse({"history": [{
        "id": s.id, "condition": s.condition, "confidence": s.confidence,
        "confidence_percent": round(s.confidence * 100, 1),
        "all_scores": json.loads(s.all_predictions) if s.all_predictions else {},
        "source": s.source,
        "created_at": s.created_at.isoformat(),
        "products": _saved_products(s),
    } for s in scans]})

@router.delete("/{scan_id}")
async def delete_scan(scan_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    scan = db.query(ScanHistory).filter(ScanHistory.id == scan_id,
                                        ScanHistory.user_id == user["user_id"]).first()
    if not scan:
        raise HTTPException(404, "Scan not found.")
    db.delete(scan); db.commit()
    return JSONResponse({"message": "Deleted."})

@router.get("/{scan_id}")
async def get_scan(scan_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    scan = db.query(ScanHistory).filter(ScanHistory.id == scan_id, ScanHistory.user_id == user["user_id"]).first()
    if not scan:
        raise HTTPException(404, "Scan not found.")
    all_scores = json.loads(scan.all_predictions) if scan.all_predictions else {}
    rec = get_recommendation(scan.condition)
    return JSONResponse({
        "scan_id": scan.id,
        "condition": scan.condition,
        "condition_label": rec["label"],
        "confidence": scan.confidence,
        "confidence_percent": round(scan.confidence * 100, 1),
        "all_scores": all_scores,
        "severity": rec["severity"],
        "description": rec["description"],
        "morning_routine": rec["morning_routine"],
        "night_routine": rec["night_routine"],
        "products": _saved_products(scan),
        "preventive_tips": rec["preventive_tips"],
        "ingredients_to_avoid": rec.get("ingredients_to_avoid", []),
        "consult_dermatologist": rec["consult_dermatologist"],
        "first_aid_tips": rec.get("first_aid_tips", []),
        "emergency_note": rec.get("emergency_note", []),
        "source": scan.source,
        "timestamp": scan.created_at.isoformat(),
    })


@router.get("/{scan_id}/routine-progress")
async def get_routine_progress(scan_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    scan = db.query(ScanHistory).filter(
        ScanHistory.id == scan_id,
        ScanHistory.user_id == user["user_id"],
    ).first()
    if not scan:
        raise HTTPException(404, "Scan not found.")

    progress = db.query(RoutineProgress).filter_by(
        user_id=user["user_id"],
        scan_id=scan_id,
    ).first()
    return {"progress": json.loads(progress.completed_steps) if progress else {"morning": [], "night": []}}


@router.put("/{scan_id}/routine-progress")
async def save_routine_progress(
    scan_id: int,
    data: RoutineProgressUpdate,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    scan = db.query(ScanHistory).filter(
        ScanHistory.id == scan_id,
        ScanHistory.user_id == user["user_id"],
    ).first()
    if not scan:
        raise HTTPException(404, "Scan not found.")

    routine = get_recommendation(scan.condition)
    for period, steps in (("morning", routine["morning_routine"]), ("night", routine["night_routine"])):
        if any(index < 0 or index >= len(steps) for index in getattr(data, period)):
            raise HTTPException(422, f"Invalid {period} routine step.")

    progress = db.query(RoutineProgress).filter_by(
        user_id=user["user_id"],
        scan_id=scan_id,
    ).first()
    if progress is None:
        progress = RoutineProgress(user_id=user["user_id"], scan_id=scan_id)
        db.add(progress)
    progress.completed_steps = json.dumps(data.model_dump())

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Could not save routine progress. Please try again.") from exc
    return {"progress": data.model_dump()}
