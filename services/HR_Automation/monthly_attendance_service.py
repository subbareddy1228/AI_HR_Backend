import io
import csv
import calendar
from datetime import date, datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import extract
from fastapi import HTTPException

from model.HR_Automation.monthly_attendance import MonthlyAttendanceDay
from model.HR_Automation.holiday import Holiday
from model.HR_Automation.shift import Shift
from model.onboarding.employee import Employee
from schema.HR_Automation.monthly_attendance import (
    MonthlyAttendanceFilter,
    MonthlyCalendarOut,
    MonthlyFilterOptions,
    CalendarDayOut,
    EmployeeProfileCard,
    DayCodeUpdate,
    DAY_CODE_MAP,
)



WEEKDAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
MONTH_ABBR    = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                 "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


DEFAULT_WEEK_OFF_DAYS = {6}  



def _get_emp_or_404(db: Session, employee_id: int) -> Employee:
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(404, f"Employee {employee_id} not found.")
    return emp


def _get_holidays(db: Session, month: int, year: int, location: Optional[str]) -> set:

    q = db.query(Holiday).filter(
        extract("month", Holiday.holiday_date) == month,
        extract("year",  Holiday.holiday_date) == year,
        Holiday.is_active == True,
    )
    if location:
        q = q.filter(
            (Holiday.applicable_location == None) |
            (Holiday.applicable_location == location)
        )
    return {h.holiday_date for h in q.all()}


def _get_shift(db: Session, shift_name: Optional[str]) -> Optional[Shift]:
    if not shift_name:
        return db.query(Shift).filter(Shift.is_active == True).first()
    return db.query(Shift).filter(Shift.shift_name == shift_name).first()


def _week_off_days(emp: Employee) -> set:

    return DEFAULT_WEEK_OFF_DAYS


def _build_profile_card(emp: Employee) -> EmployeeProfileCard:
    return EmployeeProfileCard(
        employee_id=emp.id,
        employee_code=emp.employee_code,
        employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
        date_of_joining=emp.joining_date,
        date_of_exit=None,         
        location=emp.location,
        department=emp.department,
        designation=emp.designation,
        default_shift=emp.shift_policy or "General",
    )


def _infer_day_code(
    att_date: date,
    holiday_dates: set,
    week_off_days: set,
    emp_joining: date,
) -> str:

    if att_date < emp_joining:
        return "NA"
    if att_date.weekday() in week_off_days:
        return "W"
    if att_date in holiday_dates:
        return "H"
    return "A"


def _calc_worked_hours(check_in: Optional[str], check_out: Optional[str]) -> float:
    if not check_in or not check_out:
        return 0.0
    try:
        def _to_float(t: str) -> float:
            t = t.strip().upper()
            ampm = t[-1]
            parts = t[:-1].split(":")
            h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            if ampm == "P" and h != 12:
                h += 12
            if ampm == "A" and h == 12:
                h = 0
            return h + m / 60
        diff = _to_float(check_out) - _to_float(check_in)
        return round(max(diff, 0.0), 2)
    except Exception:
        return 0.0


class MonthlyAttendanceService:


    def get_filter_options(self, db: Session) -> MonthlyFilterOptions:
        emps = db.query(Employee).filter(Employee.is_active == True).all()
        return MonthlyFilterOptions(
            business_units=sorted({e.business_unit for e in emps if e.business_unit}),
            locations=sorted({e.location for e in emps if e.location}),
            cost_centers=sorted({e.cost_center for e in emps if e.cost_center}),
            departments=sorted({e.department for e in emps if e.department}),
        )

    def get_calendar(
        self, db: Session, employee_id: int, month: int, year: int
    ) -> MonthlyCalendarOut:

        emp            = _get_emp_or_404(db, employee_id)
        holiday_dates  = _get_holidays(db, month, year, emp.location)
        week_off_days  = _week_off_days(emp)
        _, days_in_month = calendar.monthrange(year, month)


        records = db.query(MonthlyAttendanceDay).filter(
            MonthlyAttendanceDay.employee_id == employee_id,
            extract("month", MonthlyAttendanceDay.att_date) == month,
            extract("year",  MonthlyAttendanceDay.att_date) == year,
        ).all()
        record_map: dict[date, MonthlyAttendanceDay] = {r.att_date: r for r in records}

        days: List[CalendarDayOut] = []
        counts = {"P": 0, "A": 0, "H": 0, "W": 0, "HD": 0,
                  "CL": 0, "SL": 0, "LW": 0, "CO": 0}

        for day_num in range(1, days_in_month + 1):
            att_date = date(year, month, day_num)
            weekday  = WEEKDAY_NAMES[att_date.weekday()]
            is_weekend = att_date.weekday() in week_off_days
            is_holiday = att_date in holiday_dates

            rec = record_map.get(att_date)

            if rec:
                day_code     = rec.day_code
                status       = rec.status
                leave_code   = rec.leave_code
                has_punch    = rec.has_punch
                check_in     = rec.check_in
                check_out    = rec.check_out
                worked_hours = rec.worked_hours
                is_late      = rec.is_late
            else:
                day_code = _infer_day_code(att_date, holiday_dates, week_off_days, emp.joining_date)
                if day_code == "NA":

                    continue
                meta         = DAY_CODE_MAP.get(day_code, {})
                status       = meta.get("label", day_code)
                leave_code   = meta.get("leave_code")
                has_punch    = False
                check_in     = None
                check_out    = None
                worked_hours = 0.0
                is_late      = False


            if day_code in counts:
                counts[day_code] += 1

            days.append(CalendarDayOut(
                date=att_date,
                day_number=day_num,
                weekday=weekday,
                day_code=day_code,
                status=status,
                leave_code=leave_code,
                has_punch=has_punch,
                check_in=check_in,
                check_out=check_out,
                worked_hours=worked_hours,
                is_late=is_late,
                is_weekend=is_weekend,
                is_holiday=is_holiday,
            ))

        leave_days = counts["CL"] + counts["SL"] + counts["LW"] + counts["CO"]

        return MonthlyCalendarOut(
            employee=_build_profile_card(emp),
            month=month,
            year=year,
            month_label=f"{MONTH_ABBR[month - 1]}-{year}",
            days=days,
            total_present=counts["P"],
            total_absent=counts["A"],
            total_holiday=counts["H"],
            total_week_off=counts["W"],
            total_half_day=counts["HD"],
            total_leave=leave_days,
            total_working_days=days_in_month - counts["W"] - counts["H"],
        )

    def list_calendars(
        self, db: Session, filters: MonthlyAttendanceFilter
    ) -> List[MonthlyCalendarOut]:

        q = db.query(Employee).filter(Employee.is_active == True)

        if filters.employee_id:
            q = q.filter(Employee.id == filters.employee_id)
        if filters.business_unit and filters.business_unit not in ("All Units", "All", ""):
            q = q.filter(Employee.business_unit == filters.business_unit)
        if filters.location and filters.location not in ("All Locations", "All", ""):
            q = q.filter(Employee.location == filters.location)
        if filters.cost_center and filters.cost_center not in ("All Cost Centers", "All", ""):
            q = q.filter(Employee.cost_center == filters.cost_center)
        if filters.department and filters.department not in ("All Departments", "All", ""):
            q = q.filter(Employee.department == filters.department)

        employees = q.order_by(Employee.first_name).all()
        return [self.get_calendar(db, emp.id, filters.month, filters.year) for emp in employees]

    def replace_day(
        self, db: Session, employee_id: int, att_date: date, payload: DayCodeUpdate
    ) -> MonthlyAttendanceDay:

        _get_emp_or_404(db, employee_id)

        meta   = DAY_CODE_MAP.get(payload.day_code.upper(), {})
        status = meta.get("label", payload.day_code)
        lcode  = meta.get("leave_code")

        rec = db.query(MonthlyAttendanceDay).filter(
            MonthlyAttendanceDay.employee_id == employee_id,
            MonthlyAttendanceDay.att_date    == att_date,
        ).first()

        worked = _calc_worked_hours(payload.check_in, payload.check_out)

        if rec:
            rec.day_code     = payload.day_code.upper()
            rec.status       = status
            rec.leave_code   = lcode
            rec.shift_name   = payload.shift_name or rec.shift_name
            rec.check_in     = payload.check_in  or rec.check_in
            rec.check_out    = payload.check_out or rec.check_out
            rec.worked_hours = worked if worked > 0 else rec.worked_hours
            rec.has_punch    = bool(payload.check_in)
            rec.updated_at   = datetime.utcnow()
        else:
            rec = MonthlyAttendanceDay(
                employee_id=employee_id,
                att_date=att_date,
                day_code=payload.day_code.upper(),
                status=status,
                leave_code=lcode,
                shift_name=payload.shift_name or "General",
                check_in=payload.check_in,
                check_out=payload.check_out,
                worked_hours=worked,
                has_punch=bool(payload.check_in),
            )
            db.add(rec)

        db.commit()
        db.refresh(rec)
        return rec

    def recalculate(self, db: Session, employee_id: int, month: int, year: int) -> dict:
 
        emp           = _get_emp_or_404(db, employee_id)
        holiday_dates = _get_holidays(db, month, year, emp.location)
        week_off_days = _week_off_days(emp)
        _, days_in_month = calendar.monthrange(year, month)

        try:
            from model.HR_Automation.daily_attendance import DailyAttendanceRecord
            daily_records = db.query(DailyAttendanceRecord).filter(
                DailyAttendanceRecord.employee_id == employee_id,
                extract("month", DailyAttendanceRecord.att_date) == month,
                extract("year",  DailyAttendanceRecord.att_date) == year,
            ).all()
            daily_map = {r.att_date: r for r in daily_records}
        except Exception:
            daily_map = {}

        updated = 0
        for day_num in range(1, days_in_month + 1):
            att_date = date(year, month, day_num)
            if att_date < emp.joining_date:
                continue

            daily = daily_map.get(att_date)
            if daily:
     
                status_to_code = {
                    "Present":  "P",
                    "Late":     "P",
                    "Half Day": "HD",
                    "Absent":   "A",
                    "WFH":      "P",
                }
                day_code     = status_to_code.get(daily.status, "A")
                status       = DAY_CODE_MAP.get(day_code, {}).get("label", daily.status)
                leave_code   = DAY_CODE_MAP.get(day_code, {}).get("leave_code")
                has_punch    = bool(daily.check_in)
                check_in     = daily.check_in
                check_out    = daily.check_out
                worked_hours = daily.worked_hours
                is_late      = daily.is_late
            else:
                day_code = _infer_day_code(att_date, holiday_dates, week_off_days, emp.joining_date)
                meta         = DAY_CODE_MAP.get(day_code, {})
                status       = meta.get("label", day_code)
                leave_code   = meta.get("leave_code")
                has_punch    = False
                check_in     = None
                check_out    = None
                worked_hours = 0.0
                is_late      = False

            rec = db.query(MonthlyAttendanceDay).filter(
                MonthlyAttendanceDay.employee_id == employee_id,
                MonthlyAttendanceDay.att_date    == att_date,
            ).first()

            if rec:
                rec.day_code     = day_code
                rec.status       = status
                rec.leave_code   = leave_code
                rec.has_punch    = has_punch
                rec.check_in     = check_in
                rec.check_out    = check_out
                rec.worked_hours = worked_hours
                rec.is_late      = is_late
                rec.updated_at   = datetime.utcnow()
            else:
                db.add(MonthlyAttendanceDay(
                    employee_id=employee_id,
                    att_date=att_date,
                    day_code=day_code,
                    status=status,
                    leave_code=leave_code,
                    has_punch=has_punch,
                    check_in=check_in,
                    check_out=check_out,
                    worked_hours=worked_hours,
                    is_late=is_late,
                ))
            updated += 1

        db.commit()
        return {"message": f"Recalculated {updated} days for employee {employee_id}.", "days_updated": updated}

    def download_csv(self, db: Session, month: int, year: int, filters: MonthlyAttendanceFilter) -> str:
        calendars = self.list_calendars(db, filters)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Employee Code", "Employee Name", "Department", "Location",
            "Month", "Year",
            "Present", "Absent", "Half Day", "Week Off",
            "Holiday", "Leave Days", "Total Working Days",
        ])
        for cal in calendars:
            emp = cal.employee
            writer.writerow([
                emp.employee_code,
                emp.employee_name,
                emp.department or "",
                emp.location or "",
                month,
                year,
                cal.total_present,
                cal.total_absent,
                cal.total_half_day,
                cal.total_week_off,
                cal.total_holiday,
                cal.total_leave,
                cal.total_working_days,
            ])
        return output.getvalue()


monthly_attendance_service = MonthlyAttendanceService()
