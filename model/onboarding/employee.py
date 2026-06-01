from datetime import date
import enum

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    transgender = "transgender"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)

    onboarding_id: Mapped[int | None] = mapped_column(
        ForeignKey("onboarding_forms.id")
    )

    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))

    date_of_birth: Mapped[date | None]
    joining_date: Mapped[date]
    confirmation_date: Mapped[date | None]

    gender: Mapped[GenderEnum]

    employee_code: Mapped[str] = mapped_column(String(50), unique=True)
    biometric_code: Mapped[str | None] = mapped_column(String(50))

    mobile_number: Mapped[str] = mapped_column(String(15), unique=True)
    official_email: Mapped[str | None] = mapped_column(String(255))

    business_unit: Mapped[str | None]
    location: Mapped[str | None]
    cost_center: Mapped[str | None]
    department: Mapped[str | None]
    designation: Mapped[str | None]
    grade: Mapped[str | None]

    shift_policy: Mapped[str | None]
    week_off_policy: Mapped[str | None]
    overtime_policy: Mapped[str | None]

    send_mobile_login: Mapped[bool] = mapped_column(default=True)
    send_web_login: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)
