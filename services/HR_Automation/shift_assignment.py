from model.HR_Automation.shift_assignment import (
    ShiftAssignment
)


class ShiftAssignmentService:

    @staticmethod
    def assign_shift(
        db,
        payload
    ):

        assignment = ShiftAssignment(
            employee_id=payload.employee_id,
            shift_id=payload.shift_id,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to
        )

        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        return assignment