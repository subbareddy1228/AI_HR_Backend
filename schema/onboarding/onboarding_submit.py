from pydantic import BaseModel
from typing import Dict, Any

class OnboardingStepSubmit(BaseModel):
    step: int             
    progress: int         
    payload: Dict[str, Any]  
