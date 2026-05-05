from sqlalchemy import Column, String
from app.models.base import BaseModel

class Clinic(BaseModel):
    __tablename__ = "clinics"

    name           = Column(String, nullable=False)
    doctor_name    = Column(String, nullable=False)
    qualification  = Column(String, nullable=True)   # B.H.M.S.
    address        = Column(String, nullable=True)
    city           = Column(String, nullable=True)
    phone          = Column(String, nullable=True)
    email          = Column(String, nullable=True)
    logo_url       = Column(String, nullable=True)
    signature_url  = Column(String, nullable=True)   # for receipts
    timings        = Column(String, nullable=True)   # "10am-2pm, 5pm-9pm"
    plan_id        = Column(String, default="starter")