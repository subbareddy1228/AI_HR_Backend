from pydantic import BaseModel
from typing import Dict, Any

class OnboardingStepSubmit(BaseModel):
    step: int              # 1..11
    progress: int          # %
    payload: Dict[str, Any]  # step data
