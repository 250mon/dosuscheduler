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
from flask_wtf import csrf
from sqlalchemy import and_

from scheduler import db
from scheduler.forms import DosutypeForm
from scheduler.models import DosuType, Patient

bp = Blueprint("dosutype", __name__, url_prefix="/dosutype")


@bp.route("/")
def dosutype_list():
    dosutypes = db.session.execute(db.select(DosuType).order_by(DosuType.id)).scalars()
    return render_template("dosutype/list.html", dosutypes=dosutypes)


@bp.route("/create", methods=["GET", "POST"])
def dosutype_create():
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("dosutype.dosutype_list"))

    form = DosutypeForm()
    if request.method == "POST" and form.validate_on_submit():
        name = form.name.data
        order_code = form.order_code.data
        slot_quantity = int(form.slot_quantity.data)
        price = form.price.data
        available = form.available.data == "yes"

        try:
            dosutype = DosuType(
                name=name,
                order_code=order_code,
                slot_quantity=slot_quantity,
                price=price,
                available=available,
            )
            db.session.add(dosutype)
            db.session.commit()
            return redirect(url_for("dosutype.dosutype_detail", id=dosutype.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Dosutype: Failed creating {name}: {e}")

    return render_template("dosutype/form.html", form=form)


@bp.route("/<int:id>/update", methods=["GET", "POST"])
def dosutype_update(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("dosutype.dosutype_list"))

    dosutype = db.get_or_404(DosuType, id)
    if request.method == "POST":
        form = DosutypeForm()
        if form.validate_on_submit():
            dosutype.name = form.name.data
            dosutype.order_code = form.order_code.data
            dosutype.slot_quantity = int(form.slot_quantity.data)
            dosutype.price = form.price.data
            dosutype.available = form.available.data == "yes"
            try:
                db.session.commit()
                return redirect(url_for("dosutype.dosutype_detail", id=dosutype.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Dosutype: Failed updateing {dosutype.name}: {e}")

    form = DosutypeForm(obj=dosutype)
    return render_template("dosutype/form.html", form=form)


@bp.route("/<int:id>")
def dosutype_detail(id):
    dosutype = db.get_or_404(DosuType, id)
    return render_template("dosutype/detail.html", dosutype=dosutype)


@bp.route("/<int:id>/delete", methods=["GET", "POST"])
def dosutype_delete(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("dosutype.dosutype_list"))

    dosutype = db.get_or_404(DosuType, id)
    if request.method == "POST":
        db.session.delete(dosutype)
        db.session.commit()
        return redirect(url_for("dosutype.dosutype_list"))

    return render_template(
        "delete.html",
        entity_type="DosuType",
        entity_name=dosutype.name,
        entity_order_code=dosutype.order_code,
        entity_id=dosutype.id,
        entity_delete_url="dosutype.dosutype_delete",
        entity_list_url="dosutype.dosutype_list",
    )


@bp.route("/get_dosutypes/<int:patient_id>")
def get_dosutypes(patient_id):
    mrn = db.session.execute(
        db.select(Patient.mrn).where(Patient.id == patient_id)
    ).scalar()

    dosutypes = db.session.execute(
        db.select(DosuType).where(
            and_(
                DosuType.available,
                (
                    DosuType.name.like("off%")
                    if mrn == 0
                    else DosuType.name.not_like("off%")
                ),
            )
        )
    ).scalars()

    dosutypes_dict = {}
    for dt in dosutypes:
        dosutypes_dict[dt.id] = dt.to_dict()

    if dosutypes:
        return jsonify(dosutypes=dosutypes_dict)
    else:
        return jsonify({"error": "dosusess not found"}), 404
