from datetime import date

from model.HR_Automation.attendance_daily import (
    AttendanceDaily
)

from model.HR_Automation.attendance_punch import (
    AttendancePunch
)


class AttendanceDailyService:

    @staticmethod
    def process_attendance(
        db,
        employee_id: int,
        attendance_date: date
    ):
        punches = (
            db.query(
                AttendancePunch
            )
            .filter(
                AttendancePunch.employee_id
                == employee_id
            )
            .all()
        )

        if not punches:
            return None

        punches.sort(
            key=lambda x: x.punch_time
        )

        first_in = None
        last_out = None

        for punch in punches:

            if (
                punch.punch_type
                == "CHECKIN"
            ):
                first_in = (
                    first_in
                    or punch.punch_time
                )

            if (
                punch.punch_type
                == "CHECKOUT"
            ):
                last_out = (
                    punch.punch_time
                )

        work_minutes = 0

        if first_in and last_out:
            work_minutes = int(
                (
                    last_out - first_in
                ).total_seconds() / 60
            )

        overtime = max(
            0,
            work_minutes - 480
        )

        existing = (
            AttendanceDailyCRUD
            .get_by_employee_date(
                db,
                employee_id,
                attendance_date
            )
        )

        if existing:
            existing.first_in = first_in
            existing.last_out = last_out
            existing.work_minutes = work_minutes
            existing.overtime_minutes = overtime

            db.commit()

            return existing

        obj = AttendanceDaily(
            employee_id=employee_id,
            attendance_date=attendance_date,
            first_in=first_in,
            last_out=last_out,
            work_minutes=work_minutes,
            overtime_minutes=overtime,
            attendance_status="P"
        )

        return AttendanceDailyCRUD.create(
            db,
            obj
        )