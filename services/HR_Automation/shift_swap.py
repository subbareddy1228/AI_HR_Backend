from model.HR_Automation.shift_swap import (
    ShiftSwapRequest
)


class ShiftSwapService:

    @staticmethod
    def create_request(
        db,
        payload
    ):

        req = ShiftSwapRequest(
            requester_employee_id=payload.requester_employee_id,
            target_employee_id=payload.target_employee_id,
            swap_date=payload.swap_date
        )

        db.add(req)
        db.commit()
        db.refresh(req)

        return req
    @staticmethod
    def approve_request(
        db,
        request_obj
    ):

        request_obj.status = "APPROVED"

        db.commit()

        db.refresh(request_obj)

        return request_obj
    
    @staticmethod
    def reject_request(
        db,
        request_obj
    ):

        request_obj.status = "REJECTED"

        db.commit()

        db.refresh(request_obj)

        return request_obj