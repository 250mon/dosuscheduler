from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, render_template, request
from sqlalchemy import func

from scheduler import db
from scheduler.forms import PatientStatsForm, WorkerStatsForm
from scheduler.models import DosuSess, DosuType, Patient, Worker

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
    if request.method == "POST" and form.validate_on_submit():
        mrn = form.mrn.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Check for the vailidity of mrn
        patient = db.session.execute(
            db.select(Patient).filter_by(mrn=mrn)
        ).scalar_one_or_none()
        if patient is None:
            flash(f"MRN({mrn}) does not exist.")
            return render_template("stats/patient_stats.html", form=form)

        query = (
            db.session.query(
                DosuSess.status,
                DosuType.name.label("dosutype_name"),
                Worker.name.label("worker_name"),
                func.count(DosuSess.id).label("count"),
                func.sum(DosuSess.price).label("total_amount"),
            )
            .join(DosuSess.dosutype)
            .join(DosuSess.worker)
            .filter(
                DosuSess.patient_id == patient.id,
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
            "치료사별": {},
        }

        dosutype_stats = query.group_by(DosuType.name).all()
        for dosutype_stat in dosutype_stats:
            more_stats["도수타입별"][dosutype_stat.dosutype_name] = dosutype_stat.count

        worker_stats = query.group_by(Worker.name).all()
        for worker_stat in worker_stats:
            more_stats["치료사별"][worker_stat.worker_name] = worker_stat.count

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
    if request.method == "POST" and form.validate_on_submit():
        id = form.id.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Check for the vailidity of id
        worker = db.session.execute(
            db.select(Worker).filter_by(id=id)
        ).scalar_one_or_none()
        if worker is None:
            flash(f"id({id}) does not exist.")
            return render_template("stats/worker_stats.html", form=form)

        query = (
            db.session.query(
                DosuSess.status,
                DosuType.name.label("dosutype_name"),
                Patient.name.label("patient_name"),
                func.count(DosuSess.id).label("count"),
                func.sum(DosuSess.price).label("total_amount"),
            )
            .join(DosuSess.dosutype)
            .join(DosuSess.patient)
            .filter(
                DosuSess.worker_id == worker.id,
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

        dosutype_stats = query.group_by(DosuType.name).all()
        for dosutype_stat in dosutype_stats:
            more_stats["도수타입별"][dosutype_stat.dosutype_name] = dosutype_stat.count

        patient_stats = query.group_by(Patient.name).all()
        for patient_stat in patient_stats:
            more_stats["환자별"][patient_stat.patient_name] = patient_stat.count

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
