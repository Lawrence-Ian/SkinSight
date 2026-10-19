from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import User, get_db
from app.services.auth_service import verify_token


def require_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required.")

    token_data = verify_token(authorization.split(" ", 1)[1])
    if not token_data:
        raise HTTPException(401, "Invalid or expired token.")

    user = db.query(User).filter(
        User.id == token_data["user_id"],
        User.is_active.is_(True),
    ).first()
    if not user:
        raise HTTPException(401, "Account is unavailable.")

    return {"user_id": user.id, "email": user.email}