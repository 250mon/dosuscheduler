from datetime import datetime

from flask import Blueprint, render_template, session

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

    return render_template(
        "monthly.html",
        year=year,
        month=month,
    )
