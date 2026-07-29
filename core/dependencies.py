from fastapi import Depends, HTTPException, Header
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
   
    if current_user.role.lower() == "superadmin":
        return None

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Your account is not linked to a company yet. Contact support.",
        )

    return current_user.tenant_id


def get_current_location_id(
    current_user: User = Depends(get_current_user),
    x_location_id: Optional[int] = Header(default=None, alias="X-Location-Id"),
) -> Optional[int]:
    """
    Returns the branch (CompanyLocation.id) the current user should be scoped
    to, or None if they should see all branches.

    - role == "admin": ALWAYS forced to their own location_id (or None if
      they're a whole-company admin not tied to a branch). The X-Location-Id
      header is ignored for this role — a branch-scoped admin can never
      widen their own access just by sending a different header.
    - role in ("company", "superadmin"): may OPTIONALLY narrow to one branch
      via the X-Location-Id header sent by the frontend branch selector.
      No header (the default) -> None -> all branches, matching "company
      sees all branches" from the role plan.
    - hr_admin / recruiter: None, unaffected by this helper (they aren't
      branch-filtered at all today).

    Usage in a route: filter results by `.where(Model.location_id == loc_id)`
    only when `loc_id is not None`. Callers that also scope by tenant_id
    should keep doing so — this header is not a substitute for tenant
    isolation, only an optional branch narrowing on top of it.
    """
    role = current_user.role.lower()

    if role == "admin":
        return current_user.location_id

    if role in ("company", "superadmin"):
        return x_location_id

    return None