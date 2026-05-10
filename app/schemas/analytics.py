from pydantic import BaseModel
from typing import Optional, List

class RevenueDaily(BaseModel):
    date:             str
    total:            float
    visit_count:      int
    average_per_visit: float

class RevenueSummary(BaseModel):
    today:            float
    yesterday:        float
    this_month:       float
    last_month:       float
    today_growth:     float   # % vs yesterday
    monthly_growth:   float   # % vs last month
    today_visits:     int
    this_month_visits: int

class MissedPatientSummary(BaseModel):
    missed_count:     int
    estimated_loss:   float
    currency:         str = "INR"

class RetentionSummary(BaseModel):
    total_patients:   int
    retained:         int
    retention_rate:   float
    new_this_month:   int

class TopPatient(BaseModel):
    id:               str
    name:             str
    phone:            Optional[str]
    total_visits:     int
    total_spent:      float
    value_score:      float

class FollowUpSummary(BaseModel):
    due_today:        int
    pending_total:    int
    sent_this_month:  int
    conversion_rate:  float   # % who came back after reminder

class PaymentSplit(BaseModel):
    cash:             float
    upi:              float
    online:           float
    card:             float
    cash_percent:     float
    upi_percent:      float

class TopRemedy(BaseModel):
    remedy:           str
    count:            int
    percentage:       float

class DashboardSummary(BaseModel):
    """Single call loads entire doctor dashboard"""
    revenue:          RevenueSummary
    missed_patients:  MissedPatientSummary
    retention:        RetentionSummary
    followups:        FollowUpSummary
    payment_split:    PaymentSplit
    top_patients:     List[TopPatient]
    top_remedies:     List[TopRemedy]
    action_items:     List[str]   # what doctor should do TODAY