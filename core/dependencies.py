from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from jose import jwt, JWTError
from core.database import get_db
from model.models import User
from typing import List

#  JWT settings (reuse same as in auth router) 
SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"

#  OAuth2 scheme 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

#  Get current user 
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

#  Role-based access 
def require_roles(allowed_roles: List[str]):
    """
    Dependency to ensure current user has one of the allowed roles.
    Usage: Depends(require_roles(["recruiter", "company"]))
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.lower() not in [r.lower() for r in allowed_roles]:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return role_checker
