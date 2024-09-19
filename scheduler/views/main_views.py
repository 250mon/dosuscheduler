from datetime import datetime

from flask import Blueprint, render_template, session

from scheduler import db
from scheduler.models import TimeSlotConfig, get_timeslot_config

bp = Blueprint("main", __name__)


@bp.context_processor
def inject_settings():
    if not session.get("status_filter"):
        session["status_filter"] = "active"

    return dict(status_filter=session.get("status_filter"))


@bp.route("/")
@bp.route("/monthly/<int:year>/<int:month>", methods=["GET", "POST"])
def monthly(year=None, month=None):
    if year is None or month is None:
        today = datetime.today()
        year = today.year
        month = today.month

    tsc = db.session.execute(
        db.select(TimeSlotConfig).filter_by(is_default=True)
    ).scalar_one_or_none()

    tsc = get_timeslot_config(year, month)

    return render_template(
        "monthly.html",
        year=year,
        month=month,
        timeslot_config=tsc.to_dict(),
    )
