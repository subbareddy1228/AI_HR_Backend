from datetime import datetime

from pydantic import BaseModel


class AttendancePunchCreate(
    BaseModel
):
    employee_id: int

    punch_type: str

    attendance_mode: str

    latitude: float | None = None

    longitude: float | None = None

    location: str | None = None

    selfie_url: str | None = None

    remarks: str | None = None


class AttendancePunchUpdate(
    BaseModel
):
    latitude: float | None = None

    longitude: float | None = None

    location: str | None = None

    selfie_url: str | None = None

    verified: bool | None = None

    remarks: str | None = None


class AttendancePunchResponse(
    BaseModel
):
    id: int

    employee_id: int

    punch_time: datetime

    punch_type: str

    attendance_mode: str

    latitude: float | None

    longitude: float | None

    location: str | None

    verified: bool

    class Config:
        from_attributes = True