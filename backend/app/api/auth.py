"""SKINSIGHT v2 — Auth API"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import require_user
from app.database import get_db, User, UserProfile
from app.services.auth_service import hash_password, verify_password, create_token

router = APIRouter()

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    password: str = Field(min_length=6)

class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    skin_type: str | None = Field(default=None, max_length=50)


def _profile_values(profile):
    if not profile:
        return {"skin_type": None}
    return {"skin_type": profile.skin_type}

@router.post("/signup")
async def signup(data: SignupRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered.")
    user = User(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:
        db.flush()
        db.add(UserProfile(user_id=user.id))
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Email already registered.") from exc
    return JSONResponse({"message": "Account created!", "token": create_token(user.id, user.email),
                         "user": {"id": user.id, "name": user.name, "email": user.email}}, status_code=201)

@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password.")
    return JSONResponse({"message": "Login successful!", "token": create_token(user.id, user.email),
                         "user": {"id": user.id, "name": user.name, "email": user.email}})


@router.get("/me")
async def get_account(user=Depends(require_user), db: Session = Depends(get_db)):
    account = db.query(User).filter(User.id == user["user_id"]).one()
    profile = db.query(UserProfile).filter(UserProfile.user_id == account.id).first()
    return {
        "user": {
            "id": account.id,
            "name": account.name,
            "email": account.email,
            "created_at": account.created_at.isoformat() if account.created_at else None,
        },
        "profile": _profile_values(profile),
    }


@router.patch("/profile")
async def update_profile(
    data: ProfileUpdate,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user["user_id"]).first()
    if profile is None:
        profile = UserProfile(user_id=user["user_id"])
        db.add(profile)

    profile.skin_type = data.skin_type

    try:
        db.commit()
        db.refresh(profile)
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Could not save the profile. Please try again.") from exc
    return {"profile": _profile_values(profile)}
