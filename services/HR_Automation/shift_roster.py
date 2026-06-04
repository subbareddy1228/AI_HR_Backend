from model.HR_Automation.shift_roster import (
    ShiftRoster
)


class ShiftRosterService:

    @staticmethod
    def create_roster(
        db,
        payload
    ):

        roster = ShiftRoster(
            employee_id=payload.employee_id,
            shift_id=payload.shift_id,
            roster_date=payload.roster_date
        )

        db.add(roster)
        db.commit()
        db.refresh(roster)

        return roster