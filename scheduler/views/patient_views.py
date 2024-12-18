from datetime import date

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, send_file
from datetime import date, datetime
import csv
from io import StringIO, BytesIO

from scheduler import db
from scheduler.forms import PatientForm
from scheduler.models import DosuSess, DosuType, Patient, Worker

bp = Blueprint("patient", __name__, url_prefix="/patient")


@bp.route("/list")
def patient_list():
    kw = request.args.get("kw", type=str, default="")
    so = request.args.get("so", type=str, default="mrn")
    page = request.args.get("page", type=int, default=1)

    if so and so == "mrn":
        patient_list = db.select(Patient).order_by(Patient.mrn.desc())
    elif so and so == "name":
        patient_list = db.select(Patient).order_by(Patient.name.desc())
    else:
        patient_list = db.select(Patient).order_by(Patient.id.desc())

    if kw:
        search = f"%{kw}%"
        patient_list = patient_list.options(db.joinedload(Patient.dosusess_set)).filter(
            Patient.mrn.ilike(search)
            | Patient.name.ilike(search)
            | Patient.birthday.ilike(search)
            | Patient.tel.ilike(search)
            | Patient.note.ilike(search)
        )

    # Add error handling for invalid page numbers
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    pagination = db.paginate(
        patient_list,
        page=page,
        per_page=10,
    )
    return render_template("patient/list.html", pagination=pagination, kw=kw, so=so)


@bp.route("/create", methods=["GET", "POST"])
def patient_create():
    form = PatientForm()
    if request.method == "POST" and form.validate_on_submit():
        mrn = int(form.mrn.data)
        name = form.name.data
        sex = form.sex.data
        birthday = form.birthday.data
        tel = form.tel.data
        note = form.note.data

        # Check for duplicate mrn
        existing_patient = db.session.execute(
            db.select(Patient).filter_by(mrn=mrn)
        ).scalar_one_or_none()
        if existing_patient:
            flash(f"MRN({mrn}) already exists.")
            return render_template("patient/form.html", form=form)

        try:
            # Create a new Patient instance with the provided form data
            patient = Patient(
                mrn=mrn, name=name, sex=sex, birthday=birthday, tel=tel, note=note
            )
            db.session.add(patient)
            db.session.commit()
            return redirect(url_for("patient.patient_detail", id=patient.id))
        except IntegrityError:
            db.session.rollback()
            flash("Patient with this MRN already exists")
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Failed to create patient")
            flash("An unexpected error occurred")

    return render_template("patient/form.html", form=form)


@bp.route("/update/<int:id>", methods=["GET", "POST"])
def patient_update(id):
    patient = db.get_or_404(Patient, id)
    # if g.user != ###:
    #     flash("수정권한이 없습니다")
    #     return redirect(url_for("worker.worker_detail", id=worker.id))

    if request.method == "POST":
        form = PatientForm()
        if form.validate_on_submit():
            patient.name = form.name.data
            patient.sex = form.sex.data
            patient.birthday = form.birthday.data
            patient.tel = form.tel.data
            patient.note = form.note.data
            try:
                db.session.commit()
                return redirect(url_for("patient.patient_detail", id=patient.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Patient: Failed updating {patient.mrn} {patient.name}: {e}")

    form = PatientForm(obj=patient)
    return render_template("patient/form.html", form=form)


@bp.route("/detail/<int:id>")
def patient_detail(id):
    patient = db.get_or_404(Patient, id)
    kw = request.args.get("kw", type=str, default="")
    page = request.args.get("page", type=int, default=1)

    dosusess_list = (
        db.select(DosuSess)
        .filter_by(patient_id=id)
        .order_by(DosuSess.dosusess_date.desc())
    )

    if kw:
        search = f"%{kw}%"
        dosusess_list = (
            dosusess_list.join(DosuSess.worker)
            .join(DosuSess.dosutype)
            .filter(
                DosuSess.note.ilike(search)
                | DosuSess.status.ilike(search)
                | DosuSess.dosusess_date.ilike(search)
                | Worker.name.ilike(search)
                | DosuType.name.ilike(search)
            )
            .distinct()
        )

    pagination = db.paginate(
        dosusess_list,
        page=page,
        per_page=10,
    )

    today = date.today()

    return render_template(
        "patient/detail.html",
        patient=patient,
        pagination=pagination,
        kw=kw,
        today=today,
    )


@bp.route("/delete/<int:id>", methods=["GET", "POST"])
def patient_delete(id):
    patient = db.get_or_404(Patient, id)

    if request.method == "POST":
        # Check if there's a confirmation query parameter (or handle via form submission)
        confirm = request.form.get("confirm", None)
        if len(patient.dosusess_set) == 0 or confirm == "yes":
            db.session.delete(patient)
            db.session.commit()
            flash("환자가 성공적으로 삭제되었습니다.")
        else:
            flash("환자 기록에 도수 세션이 있습니다.")
        return redirect(url_for("patient.patient_list"))

    # If there are dosu sessions, but the user has privilege 5, ask for confirmation
    need_confirm = False
    if len(patient.dosusess_set) > 0 and g.user and g.user.privilege == 5:
        need_confirm = True

    return render_template(
        "delete.html",
        entity_type="Patient",
        entity_name=patient.name,
        entity_id=patient.id,
        entity_delete_url="patient.patient_delete",
        entity_list_url="patient.patient_list",
        need_confirm=need_confirm,
    )


@bp.route("/export")
def patient_export():
    # Get query parameters to match the current list view
    kw = request.args.get("kw", type=str, default="")
    so = request.args.get("so", type=str, default="mrn")

    # Create the base query
    if so == "mrn":
        patient_list = db.select(Patient).order_by(Patient.mrn.desc())
    elif so == "name":
        patient_list = db.select(Patient).order_by(Patient.name.desc())
    else:
        patient_list = db.select(Patient).order_by(Patient.id.desc())

    # Apply search filter if exists
    if kw:
        search = f"%{kw}%"
        patient_list = patient_list.filter(
            Patient.mrn.ilike(search)
            | Patient.name.ilike(search)
            | Patient.birthday.ilike(search)
            | Patient.tel.ilike(search)
            | Patient.note.ilike(search)
        ).distinct()

    # Execute query
    patients = db.session.execute(patient_list).scalars()

    # Create a string buffer and write to it
    si = StringIO()
    cw = csv.writer(si)
    
    # Write headers with BOM for Excel
    cw.writerow(['환자번호', '이름', '성별', '생일', '전화번호', '메모'])
    
    # Write data
    for patient in patients:
        cw.writerow([
            patient.mrn,
            patient.name,
            '남' if patient.sex == 'male' else '여',
            patient.birthday.strftime('%Y-%m-%d') if patient.birthday else '',
            patient.tel,
            patient.note
        ])

    # Get the string value and encode it
    output = si.getvalue().encode('utf-8-sig')  # Use UTF-8 with BOM for Excel
    si.close()
    
    # Create a BytesIO object
    bio = BytesIO()
    bio.write(output)
    bio.seek(0)  # Move to the beginning of the buffer
    
    # Generate filename with current timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'patients_{timestamp}.csv'

    return send_file(
        bio,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )
