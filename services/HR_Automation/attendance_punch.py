from datetime import datetime

from model.HR_Automation.attendance_punch import (
    AttendancePunch
)


class AttendancePunchService:

    @staticmethod
    def create_punch(
        db,
        payload
    ):
        obj = AttendancePunch(
            employee_id=payload.employee_id,

            punch_time=datetime.utcnow(),

            punch_type=payload.punch_type,

            attendance_mode=payload.attendance_mode,

            latitude=payload.latitude,

            longitude=payload.longitude,

            location=payload.location,

            selfie_url=payload.selfie_url,

            remarks=payload.remarks,

            verified=True
        )

        return AttendancePunchCRUD.create(
            db,
            obj
        )

    @staticmethod
    def get_employee_punches(
        db,
        employee_id
    ):
        return AttendancePunchCRUD.get_by_employee(
            db,
            employee_id
        )