from datetime import date, datetime

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_wtf import csrf

from scheduler import db
from scheduler.forms import WorkerForm
from scheduler.models import DosuSess, DosuType, Patient, User, Worker

bp = Blueprint("worker", __name__, url_prefix="/worker")


@bp.route("/list")
def worker_list():
    workers = db.session.execute(
        db.select(Worker).order_by(Worker.available, Worker.id)
    ).scalars()
    return render_template("worker/list.html", workers=workers)


@bp.route("/create", methods=["GET", "POST"])
def worker_create():
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("worker.worker_list"))

    form = WorkerForm()
    if request.method == "POST" and form.validate_on_submit():
        user_id = form.user_id.data
        name = form.name.data
        room = int(form.room.data)
        available = form.available.data == "yes"

        try:
            worker = Worker(
                user_id=user_id,
                name=name,
                room=room,
                available=available,
            )
            db.session.add(worker)
            db.session.commit()
            return redirect(url_for("worker.worker_detail", id=worker.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Worker: Failed creating {name}: {e}")

    users = db.session.execute(db.select(User).filter_by(available=True)).scalars()
    return render_template("worker/form.html", form=form, users=users)


@bp.route("/update/<int:id>", methods=("GET", "POST"))
def worker_update(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("worker.worker_list"))

    worker = db.get_or_404(Worker, id)
    if request.method == "POST":
        form = WorkerForm()
        if form.validate_on_submit():
            worker.user_id = form.user_id.data
            worker.name = form.name.data
            worker.room = form.room.data
            worker.available = form.available.data == "yes"
            try:
                db.session.commit()
                return redirect(url_for("worker.worker_detail", id=worker.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Worker: Failed updating {worker.name}: {e}")

    form = WorkerForm(obj=worker)
    users = db.session.execute(db.select(User).filter_by(available=True)).scalars()
    return render_template("worker/form.html", form=form, users=users)


@bp.route("/<int:id>")
def worker_detail(id):
    worker = db.get_or_404(Worker, id)
    kw = request.args.get("kw", type=str, default="")
    page = request.args.get("page", type=int, default=1)

    start_date = datetime.strptime(
        request.args.get(
            "start_date",
            default=date.today()
            .replace(month=date.today().month - 1)
            .strftime("%Y-%m-%d"),
        ),
        "%Y-%m-%d",
    )
    end_date = datetime.strptime(
        request.args.get(
            "end_date",
            default=date.today()
            .replace(month=date.today().month + 1)
            .strftime("%Y-%m-%d"),
        ),
        "%Y-%m-%d",
    )

    dosusess_list = (
        db.select(DosuSess)
        .filter(
            DosuSess.worker_id == id,
            DosuSess.dosusess_date.between(start_date, end_date),
        )
        .order_by(DosuSess.dosusess_date.desc())
    )

    if kw:
        search = "%%{}%%".format(kw)
        dosusess_list = (
            dosusess_list.join(DosuSess.patient)
            .join(DosuSess.dosutype)
            .filter(
                DosuSess.note.ilike(search)
                | DosuSess.status.ilike(search)
                | DosuSess.dosusess_date.ilike(search)
                | Patient.mrn.ilike(search)
                | Patient.name.ilike(search)
                | DosuType.name.ilike(search)
            )
            .distinct()
        )

    pagination = db.paginate(
        dosusess_list,
        page=page,
        per_page=10,
    )

    return render_template(
        "worker/detail.html",
        worker=worker,
        pagination=pagination,
        kw=kw,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )


@bp.route("/delete/<int:id>", methods=["GET", "POST"])
def worker_delete(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("worker.worker_list"))

    worker = db.get_or_404(Worker, id)
    if request.method == "POST":
        confirm = request.form.get("confirm", None)
        if len(worker.dosusess_set) == 0 or confirm == "yes":
            db.session.delete(worker)
            db.session.commit()
            flash("Success deleting the worker.")
        else:
            flash("The worker has dosu session records")
        return redirect(url_for("worker.worker_list"))
    # If there are dosu sessions, but the user has privilege 5, ask for confirmation
    need_confirm = False
    if len(worker.dosusess_set) > 0:
        need_confirm = True

    return render_template(
        "delete.html",
        entity_type="Worker",
        entity_name=worker.name,
        entity_id=worker.id,
        entity_delete_url="worker.worker_delete",
        entity_list_url="worker.worker_list",
        need_confirm=need_confirm,
    )
