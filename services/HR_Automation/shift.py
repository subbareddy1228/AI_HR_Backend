from model.HR_Automation.shift import Shift


class ShiftService:

    @staticmethod
    def create_shift(
        db,
        payload
    ):
        obj = Shift(
            shift_name=payload.shift_name,
            shift_code=payload.shift_code,
            start_time=payload.start_time,
            end_time=payload.end_time,
            break_minutes=payload.break_minutes,
            grace_minutes=payload.grace_minutes,
            weekly_off=payload.weekly_off
        )

        return ShiftCRUD.create(
            db,
            obj
        )
    @staticmethod
    def update_shift(
        db,
        shift,
        payload
    ):

        update_data = payload.model_dump(
            exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(
                shift,
                key,
                value
            )

        db.commit()
        db.refresh(shift)

        return shift
    
    @staticmethod
    def delete_shift(
        db,
        shift
    ):

        db.delete(shift)

        db.commit()

        return {
            "message": "Shift deleted successfully"
        }