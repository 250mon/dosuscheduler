import calendar
from datetime import date

from sqlalchemy import and_, func, join

from scheduler import db
from scheduler.models import DosuSess, Patient, Worker


def new_patient_count(year, month):
    first_day = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]

    # Subquery to get the patients of the month
    month_pt = (
        db.select(
            DosuSess.patient_id.label("month_patient_id"),
            Patient.name.label("patient_name"),
        )
        .select_from(join(DosuSess, Patient, DosuSess.patient_id == Patient.id))
        .where(
            and_(
                DosuSess.dosusess_date >= first_day,
                DosuSess.dosusess_date <= last_day,
            )
        )
        .distinct()
        .subquery()
    )

    # Subquery to get the first DosuSess date for each patient
    first_dates = (
        db.select(
            month_pt.c.month_patient_id,
            func.min(DosuSess.dosusess_date).label("first_date"),
        )
        .select_from(
            join(DosuSess, month_pt, DosuSess.patient_id == month_pt.c.month_patient_id)
        )
        .group_by(month_pt.c.month_patient_id)
        .subquery()
    )

    # Main query to get full DosuSess details for the first visit of each patient
    first_dosusess = (
        db.select(DosuSess, Worker.name.label("worker_name"), month_pt.c.patient_name)
        .select_from(DosuSess)
        .join(
            first_dates,
            and_(
                DosuSess.patient_id == first_dates.c.month_patient_id,
                DosuSess.dosusess_date == first_dates.c.first_date,
            ),
        )
        .join(month_pt, DosuSess.patient_id == month_pt.c.month_patient_id)
        .join(Worker, DosuSess.worker_id == Worker.id)
        .where(
            and_(
                DosuSess.dosusess_date >= first_day,
                DosuSess.dosusess_date <= last_day,
                DosuSess.status == "active",
            )
        )
        .subquery()
    )
    # Query to get the count of new patients per worker
    query = db.select(
        first_dosusess.c.worker_name,
        func.count(first_dosusess.c.id).label("count"),
        func.group_concat(first_dosusess.c.patient_name.distinct()).label(
            "patient_names"
        ),
    ).group_by(first_dosusess.c.worker_name)

    results = db.session.execute(query).all()
    res_dict = [
        {
            "worker_name": row.worker_name,
            "count": row.count,
            "patient_names": row.patient_names.split(",") if row.patient_names else [],
        }
        for row in results
    ]

    return res_dict
