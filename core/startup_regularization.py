"""
core/startup_regularization.py

Called once at server boot — seeds default auto-reject rules.
Add to your existing lifespan / startup event in main.py.

Usage:
    from core.startup_regularization import seed_regularization
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        seed_regularization()
        yield
"""

import logging
from sqlalchemy.orm import Session
from core.database import SessionLocal

logger = logging.getLogger(__name__)


def seed_regularization():
    """
    Seeds 2 default auto-reject rules on startup.
    Matches the component's initialSettings.autoRejectRules:
      Missing Punch → 7 days
      Forgot Punch  → 5 days
    Safe to call multiple times — skips if rules already exist.
    """
    db: Session = SessionLocal()
    try:
        from services.HR_Automation.regularization import seed_auto_reject_rules
        seed_auto_reject_rules(db)
    except Exception as exc:
        logger.error("Regularization seed failed: %s", exc)
    finally:
        db.close()
