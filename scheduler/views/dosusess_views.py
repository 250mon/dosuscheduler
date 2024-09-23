from datetime import date, datetime

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import String, cast, or_

from scheduler import db
from scheduler.models import (
    DateTable,
    DosuSess,
    DosuType,
    Patient,
    TimeSlot,
    Worker,
    get_day_schedule,
    get_dosusess_detail_by_id,
    get_month_schedule,
    get_or_create,
    get_timeslot_config,
)

bp = Blueprint("dosusess", __name__, url_prefix="/dosusess")


@bp.route("/status-settings", methods=["GET", "POST"])
def status_settings():
    next_url = "/"
    if request.method == "POST":
        session["status_filter"] = request.form.get("new-status")
        next_url = request.form.get("next", "/")

    return redirect(next_url)


@bp.context_processor
def inject_settings():
    if not session.get("status_filter"):
        session["status_filter"] = "active"

    return dict(status_filter=session.get("status_filter"))


@bp.route("/daily/<int:year>/<int:month>/<int:day>")
def daily_list(year, month, day):
    return render_template(
        "dosusess/daily_list.html",
        year=year,
        month=month,
        day=day,
    )


@bp.route("/available_slot_selected", methods=["GET", "POST"])
def available_slot_selected():
    if request.method == "POST":
        sess_date = request.form.get("sess_date")
        sess_date = datetime.strptime(sess_date, "%Y-%m-%d").date()
        year = sess_date.year
        month = sess_date.month
        day = sess_date.day
        room = request.form.get("room")
        slot = request.form.get("slot")

        if session.get("status_filter") == "active":
            dosusess_info = {
                # "sess_date": sess_date_str,
                "year": year,
                "month": month,
                "day": day,
                "room": room,
                "slot": slot,
            }
            # set a session
            session["dosusess_info"] = dosusess_info

            # Render the select form with dosusess info as hidden fields
            return redirect(url_for("dosusess.select_patient_to_create_dosusess"))
        else:
            return redirect(
                url_for(
                    "dosusess.daily_list",
                    year=sess_date.year,
                    month=sess_date.month,
                    day=sess_date.day,
                )
            )
    return redirect(url_for("main.monthly"))


@bp.route("/select_patient_to_create_dosusess", methods=["GET", "POST"])
def select_patient_to_create_dosusess():
    query = request.args.get("query", type=str, default="")

    if query:
        query_str = f"%{query}%"
        patients = db.session.execute(
            db.select(Patient)
            .filter(
                Patient.name.like(query_str)
                | (cast(Patient.mrn, String).like(query_str))
            )
            .order_by(Patient.mrn)
        ).scalars()
    else:
        # initally showing an empty page
        patients = []

    dosutypes = db.session.execute(
        db.select(DosuType).filter(DosuType.available)
    ).scalars()
    return render_template(
        "dosusess/create.html",
        patients=patients,
        dosutypes=dosutypes,
        dosusess_info=session.get("dosusess_info"),
    )


@bp.route("/create", methods=["GET", "POST"])
def dosusess_create():
    if request.method == "POST":
        try:
            # get data about the slot info that was stored beforehand
            dosusess_info = session.pop("dosusess_info", None)
            room = int(dosusess_info.get("room", ""))
            slot = int(dosusess_info.get("slot", ""))
            year = int(dosusess_info.get("year", ""))
            month = int(dosusess_info.get("month", ""))
            day = int(dosusess_info.get("day", ""))
            sess_date = date(year, month, day)
            # get the inputs from form
            patient_id = int(request.form.get("patient_id", ""))
            dosutype_id = int(request.form.get("dosutype_id", ""))
        except Exception as e:
            return e, 404
        note = request.form.get("note", "")

        # Get the dosutype of the id
        dosutype = db.session.execute(
            db.select(DosuType).filter_by(id=dosutype_id)
        ).scalar_one_or_none()
        if not dosutype:
            return "Dosutype not found", 404

        # Check if the time slot is available
        # by checking any active dosusess on the slots of the day
        quantity = dosutype.slot_quantity
        date_obj, is_new_day = get_or_create(DateTable, date=sess_date)
        if not is_new_day:
            existing_dosusess = db.session.execute(
                db.select(DosuSess)
                .join(DosuSess.timeslot_set)
                .filter(
                    TimeSlot.date_id == date_obj.id,
                    TimeSlot.room == room,
                    TimeSlot.number >= slot,
                    TimeSlot.number < slot + quantity,
                    DosuSess.status == "active",
                )
            ).scalar_one_or_none()
            if existing_dosusess:
                # print(
                #     f"DosuSess: Failed creating {sess_date} {room} {slot}: Occupied slot selected!!:"
                # )
                # print(f"Existing DosuSesses: {existing_dosusess}")
                flash("이미 예약된 시간과 중복됩니다!!!")
                return redirect(
                    url_for(
                        "dosusess.daily_list",
                        year=sess_date.year,
                        month=sess_date.month,
                        day=sess_date.day,
                    )
                )

        new_timeslots = [
            get_or_create(TimeSlot, date_id=date_obj.id, room=room, number=(slot + i))
            for i in range(quantity)
        ]
        # Get the patient of the id
        patient = db.session.execute(
            db.select(Patient).filter_by(id=patient_id)
        ).scalar_one_or_none()
        if not patient:
            return "Patient not found", 404

        # Get the first available worker belonging to the room
        worker = db.session.scalar(
            db.select(Worker)
            .filter(Worker.room == room, Worker.available == True)
            .order_by(Worker.id)
        )
        if not worker:
            return "Worker not found", 404

        try:
            # Create the dosusess
            dosusess = DosuSess(
                dosusess_date=sess_date,
                room=room,
                slot=slot,
                dosutype_id=dosutype.id,
                price=dosutype.price,
                worker_id=worker.id,
                patient_id=patient.id,
                status="active",
                note=note,
            )
            for timeslot in new_timeslots:
                dosusess.timeslot_set.append(timeslot)
            db.session.add(dosusess)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Failed creating {sess_date} {room} {slot}: {e}")

        return redirect(
            url_for(
                "dosusess.daily_list",
                year=sess_date.year,
                month=sess_date.month,
                day=sess_date.day,
            )
        )

    return redirect(url_for("main.monthly"))


@bp.route("/detail/<int:id>", methods=["GET", "POST"])
def dosusess_detail(id):
    dosusess = get_dosusess_detail_by_id(id)
    if dosusess:
        return render_template("dosusess/detail.html", dosusess=dosusess)
    else:
        return jsonify({"error": "dosusess not found"}), 404


@bp.route("/update", methods=["GET", "POST"])
def dosusess_update():
    id = int(request.args.get("id", ""))
    next_url = request.args.get("next", "/")

    if request.method == "POST":
        dosusess = db.get_or_404(DosuSess, id)
        # Get form data
        # theses are the data that are always included in the post req
        status = request.form.get("status", "")
        note = request.form.get("note", "")

        # if the req is changing the shcedule, there is more data comming together
        if _date := request.form.get("dosusess_date", ""):
            try:
                sess_date = datetime.strptime(_date, "%Y-%m-%d").date()
                dosutype_id = int(request.form.get("dosutype_id", ""))
                room = int(request.form.get("room", ""))
                slot = int(request.form.get("slot", ""))
            except Exception as e:
                return e, 404

            dosutype = db.session.execute(
                db.select(DosuType).filter_by(id=dosutype_id)
            ).scalar_one_or_none()
            if not dosutype:
                return "Dosutype not found", 404

            # Check for existing active session with the same date, room, slot, and quantity
            quantity = dosutype.slot_quantity
            date_obj, is_new_day = get_or_create(DateTable, date=sess_date)
            if not is_new_day:
                existing_dosusess = db.session.execute(
                    db.select(DosuSess)
                    .join(DosuSess.timeslot_set)
                    .filter(
                        TimeSlot.date_id == date_obj.id,
                        TimeSlot.room == room,
                        TimeSlot.number >= slot,
                        TimeSlot.number < slot + quantity,
                        DosuSess.status == "active",
                    )
                ).scalar_one_or_none()
                if existing_dosusess:
                    # print(
                    #     f"DosuSess: Failed creating {sess_date} {room} {slot}: Occupied slot selected!!:"
                    # )
                    # print(f"Existing DosuSesses: {existing_dosusess}")
                    flash("이미 예약된 시간과 중복됩니다!!!")
                    dosusess_detail = get_dosusess_detail_by_id(id)
                    dosutypes = db.session.execute(
                        db.select(DosuType).filter(DosuType.available)
                    ).scalars()
                    return render_template(
                        "dosusess/update.html",
                        dosusess=dosusess_detail,
                        dosutypes=dosutypes,
                        next=next_url,
                    )

            # check_slot = DosuSess.slot == slot
            # if quantity > 1:
            #     check_slot = or_(*(DosuSess.slot == slot + i for i in range(quantity)))
            # existing_timeslot = db.session.execute(
            #     db.select(DosuSess).filter(
            #         DosuSess.dosusess_date == sess_date,
            #         DosuSess.room == room,
            #         check_slot,
            #         DosuSess.status == "active",
            #         DosuSess.id != id,
            #     )
            # ).scalar()
            #
            # if existing_timeslot:
            #     return render_template(
            #         "dosusess/update.html",
            #         dosusess=dosusess,
            #         error="A session already exists.",
            #     )

            new_timeslots = [
                # get_or_create(
                #     TimeSlot, date_id=date_obj.id, room=room, number=(slot + i)
                # )
                TimeSlot(date_id=date_obj.id, room=room, number=(slot + i))
                for i in range(quantity)
            ]

            worker = db.session.scalar(
                db.select(Worker)
                .filter(Worker.room == room, Worker.available == True)
                .order_by(Worker.id)
            )
            if not worker:
                return "Worker not found", 404

            dosusess.dosusess_date = sess_date
            dosusess.dosutype_id = dosutype.id
            dosusess.room = room
            dosusess.slot = slot
            dosusess.worker_id = worker.id
            dosusess.timeslot_set = []
            for timeslot in new_timeslots:
                dosusess.timeslot_set.append(timeslot)

        dosusess.status = status
        dosusess.note = note

        try:
            # Commit changes to the database
            db.session.commit()
            print(new_timeslots)
            return redirect(next_url)
        except Exception as e:
            db.session.rollback()
            flash(f"dosusess: Failed updating {id}: {e}")

    dosusess_detail = get_dosusess_detail_by_id(id)
    dosutypes = db.session.execute(
        db.select(DosuType).filter(DosuType.available)
    ).scalars()
    return render_template(
        "dosusess/update.html",
        dosusess=dosusess_detail,
        dosutypes=dosutypes,
        next=next_url,
    )


@bp.route("/delete", methods=["POST"])
def dosusess_delete():
    if request.method == "POST":
        try:
            id = int(request.form.get("id", ""))
        except Exception as e:
            return e, 404
        dosusess = db.get_or_404(DosuSess, id)
        db.session.delete(dosusess)
        db.session.commit()

        next_url = request.form.get("next", "/")
        return redirect(next_url)


@bp.route("/get_schedule", methods=["POST"])
def get_schedule_route():
    if request.method == "POST":
        try:
            # Attempt to parse JSON data
            data = request.get_json(
                force=True
            )  # force=True will attempt parsing regardless of content type

            if not data:
                raise ValueError("No JSON data provided")

            sess_date = None
            if data.get("date"):
                # Parse the javascript date string
                sess_date = datetime.strptime(data.get("date"), "%Y-%m-%d").date()
                year = sess_date.year
                month = sess_date.month
            else:
                year = int(data.get("year"))
                month = int(data.get("month"))

            # Function to get the schedule for the given year and month
            if sess_date:
                schedule = get_day_schedule(sess_date)
            else:
                schedule = get_month_schedule(year, month)

            # Return the schedule as a JSON response
            tsc = get_timeslot_config(year, month)
            return jsonify(schedule=schedule, timeslotConfig=tsc.to_dict())

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        except Exception as e:
            return (
                jsonify({"error": "An error occurred while processing the request"}),
                500,
            )


@bp.route("/get_dosusess/<int:id>")
def get_dosusess(id):
    dosusess = get_dosusess_detail_by_id(id)
    if dosusess:
        return jsonify(dosusess=dosusess)
    else:
        return jsonify({"error": "dosusess not found"}), 404
