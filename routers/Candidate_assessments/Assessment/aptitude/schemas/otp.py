from pydantic import BaseModel

class OTPRequest(BaseModel):
    name: str
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str
