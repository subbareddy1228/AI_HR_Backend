from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from jose import jwt, JWTError
from core.database import get_db
from model.models import User
from typing import List, Optional

 
SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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

 
def require_roles(allowed_roles: List[str]):

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.lower() not in [r.lower() for r in allowed_roles]:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return role_checker


def get_current_tenant_id(current_user: User = Depends(get_current_user)) -> Optional[int]:
   
    if current_user.role.lower() == "super_admin":
        return None

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Your account is not linked to a company yet. Contact support.",
        )

    return current_user.tenant_id


def get_current_location_id(current_user: User = Depends(get_current_user)) -> Optional[int]:
    """
    Returns the branch (CompanyLocation.id) the current admin should be scoped
    to, or None if they should see the whole company.

    - role != "admin" (superadmin, hr_admin, company, recruiter) -> None,
      no branch filter applied by this helper.
    - role == "admin" and location_id is set -> that location_id: this admin
      only sees data for their one branch.
    - role == "admin" and location_id is None -> None: a whole-company admin
      (not tied to any single branch), keeps full-tenant access.

    Usage in a route: filter results by `.where(Model.location_id == loc_id)`
    only when `loc_id is not None`.
    """
    if current_user.role.lower() != "admin":
        return None
    return current_user.location_id