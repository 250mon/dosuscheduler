from calendar import monthrange
from datetime import date, datetime

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import Integer, String, extract, func, or_

from scheduler import db
from scheduler.forms import PatientStatsForm, WorkerStatsForm
from scheduler.models import DosuSess, DosuType, Patient, Worker
from scheduler.utils import Pagination

bp = Blueprint("stats", __name__, url_prefix="/stats")


def parse_date_range(start_date_str: str, end_date_str: str) -> tuple:
    if not start_date_str or not end_date_str:
        return jsonify({"error": "Both start_date and end_date are required"}), 400
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        return start_date, end_date
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400


@bp.route("/api/patient_stats", methods=["GET", "POST"])
def patient_stats():
    form = PatientStatsForm()

    # Handle direct navigation from patient detail
    mrn_from_url = request.args.get("mrn", type=int)
    if mrn_from_url is not None:
        form.mrn.data = mrn_from_url
        # Set default date range (last 3 months)
        today = date.today()
        three_months_ago = (
            today.replace(month=today.month - 3)
            if today.month > 3
            else today.replace(year=today.year - 1, month=today.month + 9)
        )
        form.start_date.data = three_months_ago
        form.end_date.data = today

    if (
        request.method == "POST"
        and form.validate_on_submit()
        or mrn_from_url is not None
    ):
        mrn = form.mrn.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Check for the validity of mrn
        patient = db.session.execute(
            db.select(Patient).filter_by(mrn=mrn)
        ).scalar_one_or_none()
        if patient is None:
            flash(f"MRN({mrn}) does not exist.")
            return render_template("stats/patient_stats.html", form=form)

        # Get status counts
        status_counts = patient.get_status_counts(start_date, end_date)
        overview_stats = {
            "total": status_counts.get("active", 0)
            + status_counts.get("canceled", 0)
            + status_counts.get("noshow", 0),
            "total_amount": status_counts.get("total_amount", 0),
            "active": status_counts.get("active", 0),
            "canceled": status_counts.get("canceled", 0),
            "noshow": status_counts.get("noshow", 0),
        }

        if overview_stats["total"] != 0:
            noshow_rate = overview_stats["noshow"] / overview_stats["total"] * 100
            overview_stats["noshow_rate"] = f"{round(noshow_rate)} %"
        else:
            overview_stats["noshow_rate"] = "-"

        more_stats = {
            "도수타입별": {},
            "치료사별": {},
        }

        # per dosutype stats
        dt_counts = patient.get_dosutype_counts(start_date, end_date)
        for dt_name, status_dict in dt_counts.items():
            for status, count in status_dict.items():
                more_stats["도수타입별"][f"{dt_name} - {status}"] = count

        # per worker stats
        worker_counts = patient.get_worker_counts(start_date, end_date)
        for worker_id, status_dict in worker_counts.items():
            worker_name = db.session.scalar(
                db.select(Worker.name).where(Worker.id == worker_id)
            )
            for status, count in status_dict.items():
                more_stats["치료사별"][f"{worker_name} - {status}"] = count

        return render_template(
            "stats/patient_stats.html",
            form=form,
            patient=patient,
            overview_stats=overview_stats,
            more_stats=more_stats,
        )

    return render_template("stats/patient_stats.html", form=form)


@bp.route("/api/worker_stats", methods=["GET", "POST"])
def worker_stats():
    form = WorkerStatsForm()
    if not g.user or g.user.privilege < 3:
        flash("Not permitted for this page")
        return redirect(url_for("main.monthly"))
    elif g.user and g.user.privilege == 3:
        worker = db.session.execute(
            db.select(Worker).filter_by(user_id=g.user.id)
        ).scalar_one_or_none()
        if worker:
            form.id.data = worker.id
        else:
            flash("No matching worker for the user found")
            return redirect(url_for("main.monthly"))

    if request.method == "POST" and form.validate_on_submit():
        worker_id = form.id.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Check for the validity of worker_id
        worker = db.session.execute(
            db.select(Worker).filter_by(id=worker_id)
        ).scalar_one_or_none()
        if worker_id != 0 and worker is None:
            flash(f"worker_id({worker_id}) does not exist.")
            return render_template("stats/worker_stats.html", form=form)
        elif g.user.privilege == 3 and g.user.id != worker.user_id:
            flash(
                f"Manager of the worker({worker.user_id}) does not match to the user{g.user.id}."
            )
            return render_template("stats/worker_stats.html", form=form)

        query = (
            db.session.query(
                DosuSess.status,
                DosuType.name.label("dosutype_name"),
                Patient.id.label("patient_id"),
                Patient.mrn.label("patient_mrn"),
                Patient.name.label("patient_name"),
                func.count(DosuSess.id).label("count"),
                func.sum(DosuSess.price).label("total_amount"),
            )
            .join(DosuSess.dosutype)
            .join(DosuSess.patient)
            .filter(
                DosuSess.worker_id == worker_id if worker_id != 0 else True,
                Patient.mrn != 0,
                DosuSess.dosusess_date.between(start_date, end_date),
            )
        )

        status_stats = query.group_by(DosuSess.status).all()

        overview_stats = {
            "total": 0,
            "total_amount": 0,
            "active": 0,
            "canceled": 0,
            "noshow": 0,
        }

        for status_stat in status_stats:
            overview_stats[status_stat.status] = status_stat.count
            overview_stats["total"] += status_stat.count
            if status_stat.status == "active":
                overview_stats["total_amount"] += float(status_stat.total_amount or 0)

        if overview_stats["total"] != 0:
            noshow_rate = overview_stats["noshow"] / overview_stats["total"] * 100
            overview_stats["noshow_rate"] = f"{round(noshow_rate)} %"
        else:
            overview_stats["noshow_rate"] = "-"

        more_stats = {
            "도수타입별": {},
            "환자별": {},
        }

        # per dosutype, counts status
        dosutype_stats = query.group_by(DosuType.name, DosuSess.status).all()
        status_counts = {}
        # Accumulate counts for each dosutype and status
        for dosutype_stat in dosutype_stats:
            dt_name = dosutype_stat.dosutype_name
            # Ensure the dosutype is in the dictionary
            status_counts.setdefault(dt_name, {})
            # Store counts based on the status
            status_counts[dt_name].setdefault(dosutype_stat.status, dosutype_stat.count)

        # Compose the result for dosutype
        for dt_name, status_counts in status_counts.items():
            active_count = status_counts.get("active", 0)
            canceled_count = status_counts.get("canceled", 0)
            noshow_count = status_counts.get("noshow", 0)

            # the final string: active - canceled - noshow
            more_stats["도수타입별"].setdefault(
                dt_name, f"{active_count} - {canceled_count} - {noshow_count}"
            )

        # per patient, counts status
        patient_stats = query.group_by(Patient.id, DosuSess.status).all()
        status_counts = {}
        # Accumulate counts for each patient and status
        for pt_stat in patient_stats:
            pt_id = pt_stat.patient_id
            pt_mrn = pt_stat.patient_mrn
            pt_name = pt_stat.patient_name
            pt_mrn_name = f"{pt_mrn} {pt_name}"

            # Ensure the pt_id_name is in the dictionary
            # if it is a new patient, create a dict container which includes total counts
            if pt_mrn_name not in status_counts:
                patient = db.session.scalar(
                    db.select(Patient).where(Patient.id == pt_id)
                )
                pt_total = patient.get_status_counts()
                pt_total = f"{pt_total.get('active', 0)} - {pt_total.get('canceled', 0)} - {pt_total.get('noshow', 0)}"

                # create an entry
                status_counts[pt_mrn_name] = {}
                status_counts[pt_mrn_name]["total_counts"] = pt_total

            # Store counts based on the status
            status_counts[pt_mrn_name].setdefault(pt_stat.status, pt_stat.count)

        # Compose the final result
        for pt_mrn_name, status_counts in status_counts.items():
            active_count = status_counts.get("active", 0)
            canceled_count = status_counts.get("canceled", 0)
            noshow_count = status_counts.get("noshow", 0)
            total_counts = status_counts.get("total_counts", 0)

            # the final string: active - canceled - noshow
            more_stats["환자별"].setdefault(
                pt_mrn_name,
                f"{active_count} - {canceled_count} - {noshow_count} ({total_counts})",
            )

        return render_template(
            "stats/worker_stats.html",
            form=form,
            worker=worker,
            overview_stats=overview_stats,
            more_stats=more_stats,
        )

    return render_template("stats/worker_stats.html", form=form)


@bp.route("/api/dosusess_stats", methods=["POST"])
def dosusess_stats():
    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        date_range = parse_date_range(start_date, end_date)
        if isinstance(date_range, tuple):
            start_date, end_date = date_range
        else:
            return date_range

        stats = (
            db.session.query(
                func.count(DosuSess.id).label("total_dosusess"),
                func.sum(DosuSess.price).label("total_amount"),
            )
            .filter(DosuSess.dosusess_date.between(start_date, end_date))
            .first()
        )

        result = {
            "total_dosusess": stats.total_dosusess,
            "total_amount": float(stats.total_amount or 0),
        }

        return jsonify(result)


@bp.route("/new_patient_count/<int:year>/<int:month>")
def new_patient_count(year=None, month=None, stats_only=False):
    if year is None or month is None:
        today = datetime.today()
        year = today.year
        month = today.month

    kw = request.args.get("kw", type=str, default="")
    page = request.args.get("page", type=int, default=1)

    # Create base query with common conditions
    base_condition = [
        extract("year", DosuSess.dosusess_date) == year,
        extract("month", DosuSess.dosusess_date) == month,
        DosuSess.status == "active",
        DosuSess.is_first == True,
    ]

    # Get stats using the base conditions
    stats = db.session.execute(
        db.select(Worker.name, func.count(DosuSess.id).label("count"))
        .join(DosuSess.worker)
        .where(*base_condition)
        .group_by(Worker.name)
    ).all()

    if stats_only:
        stats_dict = [
            {
                "worker_name": row.name,
                "count": row.count,
            }
            for row in stats
        ]
        return stats_dict

    # Build main query using the same base conditions
    dosusess_list = (
        db.select(DosuSess)
        .join(DosuSess.worker)
        .join(DosuSess.patient)
        .where(*base_condition)
        .order_by(DosuSess.created_at.desc())
    )

    # Add search conditions if keyword provided
    if kw:
        search = f"%{kw}%"
        dosusess_list = (
            dosusess_list.join(DosuSess.dosutype)
            .where(
                db.or_(
                    Worker.name.ilike(search),
                    Patient.name.ilike(search),
                    Patient.mrn.ilike(search),
                    DosuType.name.ilike(search),
                    DosuSess.note.ilike(search),
                    DosuSess.dosusess_date.cast(db.String).ilike(search),
                )
            )
            .distinct()
        )

    pagination = db.paginate(dosusess_list, page=page, per_page=10)

    return render_template(
        "stats/new_patient_count.html",
        year=year,
        month=month,
        pagination=pagination,
        stats=stats,
        kw=kw,
    )


@bp.route("/monthly_stats/")
def monthly_stats():
    # Get year and month from query parameters, default to current date
    today = datetime.today()
    year = request.args.get("year", type=int, default=today.year)
    month = request.args.get("month", type=int, default=today.month)

    # Calculate previous and next months
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # Validate year and month
    try:
        # This will raise ValueError if the date is invalid
        date(year, month, 1)
    except ValueError:
        flash("Invalid year or month selected")
        return redirect(url_for("stats.monthly_stats"))

    # Get the start and end dates for the specified month
    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # Query for overall statistics - exclude blocked patient
    stats = db.session.execute(
        db.select(
            DosuSess.status,
            func.count(DosuSess.id).label("count"),
            func.sum(DosuSess.price).label("total_amount"),
        )
        .join(Patient, DosuSess.patient_id == Patient.id)  # Add join with Patient
        .where(
            DosuSess.dosusess_date.between(start_date, end_date),
            Patient.mrn != 0,  # Exclude blocked patient
        )
        .group_by(DosuSess.status)
    ).all()

    # Query for statistics by worker - exclude blocked patient
    worker_stats = db.session.execute(
        db.select(
            Worker.name,
            DosuSess.status,
            func.count(DosuSess.id).label("count"),
            func.sum(DosuSess.price).label("total_amount"),
        )
        .join(DosuSess.worker)
        .join(Patient, DosuSess.patient_id == Patient.id)  # Add join with Patient
        .where(
            DosuSess.dosusess_date.between(start_date, end_date),
            Patient.mrn != 0,  # Exclude blocked patient
        )
        .group_by(Worker.name, DosuSess.status)
    ).all()

    # Query for statistics by dosutype - exclude blocked patient
    dosutype_stats = db.session.execute(
        db.select(
            DosuType.name,
            DosuSess.status,
            func.count(DosuSess.id).label("count"),
            func.sum(DosuSess.price).label("total_amount"),
        )
        .join(DosuSess.dosutype)
        .join(Patient, DosuSess.patient_id == Patient.id)  # Add join with Patient
        .where(
            DosuSess.dosusess_date.between(start_date, end_date),
            Patient.mrn != 0,  # Exclude blocked patient
        )
        .group_by(DosuType.name, DosuSess.status)
    ).all()

    # Process the statistics
    overview_stats = {
        "total": 0,
        "total_amount": 0,
        "active": 0,
        "canceled": 0,
        "noshow": 0,
    }

    for stat in stats:
        overview_stats[stat.status] = stat.count
        overview_stats["total"] += stat.count
        if stat.status == "active":
            overview_stats["total_amount"] = stat.total_amount or 0

    if overview_stats["total"] != 0:
        noshow_rate = overview_stats["noshow"] / overview_stats["total"] * 100
        overview_stats["noshow_rate"] = f"{round(noshow_rate)} %"
    else:
        overview_stats["noshow_rate"] = "-"

    # Process worker statistics
    worker_data = {}
    for stat in worker_stats:
        if stat.name not in worker_data:
            worker_data[stat.name] = {
                "active": 0,
                "canceled": 0,
                "noshow": 0,
                "total_amount": 0,
            }
        worker_data[stat.name][stat.status] = stat.count
        if stat.status == "active":
            worker_data[stat.name]["total_amount"] = stat.total_amount or 0

    # Process dosutype statistics
    dosutype_data = {}
    for stat in dosutype_stats:
        if stat.name not in dosutype_data:
            dosutype_data[stat.name] = {
                "active": 0,
                "canceled": 0,
                "noshow": 0,
                "total_amount": 0,
            }
        dosutype_data[stat.name][stat.status] = stat.count
        if stat.status == "active":
            dosutype_data[stat.name]["total_amount"] = stat.total_amount or 0

    return render_template(
        "stats/monthly_stats.html",
        year=year,
        month=month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        overview_stats=overview_stats,
        worker_stats=worker_data,
        dosutype_stats=dosutype_data,
    )


@bp.route("/dosusess_list/")
def dosusess_list():
    # Get query parameters
    year = request.args.get("year", type=int, default=datetime.today().year)
    month = request.args.get("month", type=int, default=datetime.today().month)
    search = request.args.get("search", type=str, default="")
    sort_by = request.args.get("sort", type=str, default="date")  # default sort by date
    order = request.args.get("order", type=str, default="desc")
    page = request.args.get("page", type=int, default=1)

    # Create base query - exclude blocked patient
    base_query = (
        db.select(DosuSess, Patient, Worker, DosuType)
        .join(Patient, DosuSess.patient_id == Patient.id)
        .join(Worker, DosuSess.worker_id == Worker.id)
        .join(DosuType, DosuSess.dosutype_id == DosuType.id)
        .where(
            extract("year", DosuSess.dosusess_date) == year,
            extract("month", DosuSess.dosusess_date) == month,
            Patient.mrn != 0,  # Exclude blocked patient
        )
    )

    # Apply search if provided
    if search:
        search_term = f"%{search}%"
        base_query = base_query.where(
            or_(
                Patient.name.ilike(search_term),
                Patient.mrn.cast(String).ilike(search_term),
                Worker.name.ilike(search_term),
                DosuType.name.ilike(search_term),
                DosuSess.status.ilike(search_term),
                DosuSess.note.ilike(search_term),
            )
        )

    # Apply sorting
    sort_options = {
        "date": DosuSess.dosusess_date,
        "mrn": Patient.mrn.cast(Integer),  # Cast to Integer for proper numeric sorting
        "patient": Patient.name,
        "worker": Worker.name,
        "type": DosuType.name,
        "status": DosuSess.status,
        "amount": DosuSess.price,
    }

    sort_column = sort_options.get(sort_by, DosuSess.dosusess_date)
    if order == "desc":
        sort_column = sort_column.desc()
    base_query = base_query.order_by(sort_column)

    # Execute query with manual pagination
    per_page = 20
    offset = (page - 1) * per_page

    # Get total count for pagination
    count_query = db.select(func.count()).select_from(base_query.subquery())
    total = db.session.scalar(count_query)

    # Get paginated results
    results = db.session.execute(base_query.offset(offset).limit(per_page)).all()

    # Create pagination object manually
    pagination = Pagination(None, page, per_page, total, results)

    return render_template(
        "stats/dosusess_list.html",
        pagination=pagination,
        year=year,
        month=month,
        search=search,
        sort_by=sort_by,
        order=order,
    )
