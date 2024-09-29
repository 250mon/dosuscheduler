# models.py
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from flask import session
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    and_,
    event,
    or_,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from scheduler import db
from scheduler.custom_filters import format_kr_date


class Worker(db.Model):
    __tablename__ = "worker_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_table.id"))
    name: Mapped[str] = mapped_column(String)
    room: Mapped[int] = mapped_column(Integer)  # "worker1" or "worker2"
    available: Mapped[bool] = mapped_column(Boolean)

    user: Mapped["User"] = relationship(back_populates="worker")
    dosusess_set: Mapped[List["DosuSess"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Worker(id={self.id!r}, name={self.name!r})"


class Patient(db.Model):
    __tablename__ = "patient_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mrn: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String)
    sex: Mapped[str] = mapped_column(String)
    birthday: Mapped[Optional[date]] = mapped_column(Date, default=date(9999, 12, 31))
    tel: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text)

    dosusess_set: Mapped[List["DosuSess"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Patient(id={self.id!r}, mrn={self.mrn!r}, name={self.name!r})"


class DosuType(db.Model):
    __tablename__ = "dosutype_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    order_code: Mapped[str] = mapped_column(String)
    slot_quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean)

    dosusess_set: Mapped[List["DosuSess"]] = relationship(
        back_populates="dosutype", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"DosuType(id={self.id!r}, name={self.name!r})"


class DateTable(db.Model):
    __tablename__ = "date_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True)

    timeslot_set: Mapped[List["TimeSlot"]] = relationship(
        back_populates="date", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"Date(id={self.id!r}, date={self.date!r})"


class TimeSlotConfig(db.Model):
    __tablename__ = "timeslot_config_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="default")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    start_date: Mapped[date] = mapped_column(Date, default=date.today().replace(day=1))
    end_date: Mapped[date] = mapped_column(Date, default=date(9999, 12, 1))
    wd_start_hour: Mapped[time] = mapped_column(Time, default=time(hour=9))
    wd_end_hour: Mapped[time] = mapped_column(Time, default=time(hour=21))
    wd_lunch_start_hour: Mapped[time] = mapped_column(Time, default=time(hour=13))
    wd_lunch_end_hour: Mapped[time] = mapped_column(Time, default=time(hour=14))
    wd_overtime_hour: Mapped[time] = mapped_column(Time, default=time(hour=18))
    sd_start_hour: Mapped[time] = mapped_column(Time, default=time(hour=9))
    sd_end_hour: Mapped[time] = mapped_column(Time, default=time(hour=15))
    sd_overtime_hour: Mapped[time] = mapped_column(Time, default=time(hour=13))
    duration: Mapped[int] = mapped_column(Integer, default=30)

    @validates("is_default")
    def validate_default(self, key, is_default_value):
        if is_default_value:
            # Check if there is an existing default
            existing_default = (
                db.session.query(TimeSlotConfig).filter_by(is_default=True).first()
            )
            if existing_default and existing_default.id != self.id:
                # Unset the current default
                existing_default.is_default = False
                db.session.add(existing_default)  # Add to session for update

        return is_default_value

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_default": self.is_default,
            "wd_start_hour": self.wd_start_hour.strftime("%H:%M"),
            "wd_end_hour": self.wd_end_hour.strftime("%H:%M"),
            "wd_lunch_start_hour": self.wd_lunch_start_hour.strftime("%H:%M"),
            "wd_lunch_end_hour": self.wd_lunch_end_hour.strftime("%H:%M"),
            "wd_overtime_hour": self.wd_overtime_hour.strftime("%H:%M"),
            "sd_start_hour": self.sd_start_hour.strftime("%H:%M"),
            "sd_end_hour": self.sd_end_hour.strftime("%H:%M"),
            "sd_overtime_hour": self.sd_overtime_hour.strftime("%H:%M"),
            "duration": self.duration,
        }

    def __repr__(self):
        return f"TimeSlotConfig(id={self.id!r} name={self.name!r})"


class TimeSlot(db.Model):
    # TimeSlot has only active timeslots and other timeslots are deleted
    # using the below event listener
    __tablename__ = "timeslot_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_id: Mapped[int] = mapped_column(Integer, ForeignKey("date_table.id"))
    room: Mapped[int] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(Integer)
    dosusess_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dosu_session_table.id")
    )

    date: Mapped["DateTable"] = relationship(back_populates="timeslot_set")
    dosusess: Mapped["DosuSess"] = relationship(back_populates="timeslot_set")

    # Add composite unique constraint
    __table_args__ = (
        UniqueConstraint(
            "date_id", "room", "number", name="unique_timeslot_constraint"
        ),
    )

    def __repr__(self):
        return f"TimeSlot(id={self.id!r}, date_id={self.date_id!r}, room={self.room!r}, number={self.number!r})"


class DosuSess(db.Model):
    __tablename__ = "dosu_session_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # room, slot, dosusess_date is the info about the first timeslot of the timeslot_set
    room: Mapped[int] = mapped_column(Integer)
    slot: Mapped[int] = mapped_column(Integer)
    dosusess_date: Mapped[date] = mapped_column(Date)
    dosutype_id: Mapped[int] = mapped_column(Integer, ForeignKey("dosutype_table.id"))
    worker_id: Mapped[int] = mapped_column(Integer, ForeignKey("worker_table.id"))
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patient_table.id"))
    price: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    dosutype: Mapped["DosuType"] = relationship(back_populates="dosusess_set")
    patient: Mapped["Patient"] = relationship(back_populates="dosusess_set")
    worker: Mapped["Worker"] = relationship(back_populates="dosusess_set")
    timeslot_set: Mapped[List["TimeSlot"]] = relationship(
        back_populates="dosusess", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"DosuSess(id={self.id!r}, date={self.dosusess_date!r}, status={self.status!r})"


# Changing from active to others will trigger the deletion of associated TimeSlots
@event.listens_for(DosuSess.status, "set")
def dosusess_status_listener(target, value, oldvalue, initiator):
    if oldvalue == "active" and value in ["canceled", "noshow"]:
        target.timeslot_set = []


class User(db.Model):
    __tablename__ = "user_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    privilege: Mapped[int] = mapped_column(Integer, default=1)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    worker: Mapped[List["Worker"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"


def get_timeslot_config(year, month):
    call_day = date(year, month, 1)
    config_cond = or_(
        and_(
            TimeSlotConfig.is_default == False,
            TimeSlotConfig.start_date <= call_day,
            TimeSlotConfig.end_date >= call_day,
        ),
        TimeSlotConfig.is_default == True,
    )

    tsc = db.session.execute(db.select(TimeSlotConfig).filter(config_cond)).scalar()
    if not tsc:
        try:
            tsc = TimeSlotConfig(is_default=True)
            db.session.add(tsc)
            db.session.commit()
            return tsc
        except IntegrityError as e:
            db.session.rollback()
            raise Exception(e)
    return tsc


def display_date(_date: date):
    weekdays = ["일", "월", "화", "수", "목", "금", "토"]
    weekday = weekdays[_date.weekday()]
    str_date = _date.strftime("%Y-%m-%d")
    return f"{str_date} ({weekday})"


def display_slot(_date: date, slot: int):
    """
    Converts date and slot number into a slot hour for display
    """
    tsc = get_timeslot_config(_date.year, _date.month)
    slot_hour = (
        datetime.combine(datetime.today(), tsc.wd_start_hour)
        + timedelta(minutes=tsc.duration) * slot
    )
    if _date.weekday() != 5 and slot_hour.time() > tsc.wd_lunch_start_hour:
        dt_end = datetime.combine(datetime.today(), tsc.wd_lunch_end_hour)
        dt_start = datetime.combine(datetime.today(), tsc.wd_lunch_start_hour)
        slot_hour -= dt_end - dt_start

    return slot_hour.time().strftime("%H:%M")


def format_dosusess_detail(row):
    # TODO remove this and use relationships in the html
    sess = {
        "id": row.DosuSess.id,
        "date": row.DosuSess.dosusess_date,
        "date_display": format_kr_date(row.DosuSess.dosusess_date),
        "room": row.DosuSess.room,
        "slot": row.DosuSess.slot,
        "slot_display": display_slot(row.DosuSess.dosusess_date, row.DosuSess.slot),
        "dosutype_id": row.DosuSess.dosutype_id,
        "dosutype_name": row.DosuType.name,
        "slot_quantity": row.DosuType.slot_quantity,
        "price": row.DosuSess.price,
        "worker_id": row.DosuSess.worker_id,
        "worker_name": row.Worker.name,
        "patient_id": row.DosuSess.patient_id,
        "mrn": row.Patient.mrn,
        "patient_name": row.Patient.name,
        "tel": row.Patient.tel,
        "patient_note": row.Patient.note,
        "status": row.DosuSess.status,
        "note": row.DosuSess.note,
    }
    return sess


def get_data_by_date(
    target_date: date,
):  # Subquery to get all TimeSlots for the target date
    # if status-filter is active, use TimeSlot which stores only active dosusesses
    # otherwise, search the DosuSess for the date
    if session.get("status_filter", "active") == "active":
        timeslot_subquery = (
            db.select(TimeSlot.dosusess_id)
            .join(DateTable, TimeSlot.date_id == DateTable.id)
            .where(DateTable.date == target_date)
            .distinct()
            .subquery()
        )
        stmt = (
            db.select(DosuSess, DosuType, Worker, Patient)
            .join(DosuSess.dosutype)
            .join(DosuSess.patient)
            .join(DosuSess.worker)
            .join(timeslot_subquery, DosuSess.id == timeslot_subquery.c.dosusess_id)
        )
    else:
        stmt = (
            db.select(DosuSess, DosuType, Worker, Patient)
            .join(DosuSess.dosutype)
            .join(DosuSess.patient)
            .join(DosuSess.worker)
            .where(
                DosuSess.dosusess_date == target_date,
                DosuSess.status == session.get("status_filter"),
            )
        )

    return db.session.execute(stmt).all()


def get_data_by_dosusess_id(dosusess_id: int):
    stmt = (
        db.select(DosuSess, DosuType, Worker, Patient)
        .join(DosuType, DosuSess.dosutype_id == DosuType.id)
        .join(Patient, DosuSess.patient_id == Patient.id)
        .join(Worker, DosuSess.worker_id == Worker.id)
        .filter(
            DosuSess.id == dosusess_id,
            DosuSess.status == session.get("status_filter", "active"),
        )
        .limit(1)
    )
    return db.session.execute(stmt).first()


def get_dosusess_detail_by_id(id: int):
    dosusess = get_data_by_dosusess_id(id)
    return format_dosusess_detail(dosusess)


def get_day_schedule(sess_date: date):
    results = get_data_by_date(sess_date)
    dosu_sessions = []
    if results:
        for row in results:
            sess = format_dosusess_detail(row)
            dosu_sessions.append(sess)
    return dosu_sessions


def get_month_schedule(year: int, month: int):
    # TODO reduce the db access by inputting date range and getting results by filtering of db
    m_schedule = {}
    for day in range(1, 32):
        try:
            sess_date = datetime(year, month, day).date()
        except ValueError:
            continue  # Skip invalid dates

        dosu_sessions = get_day_schedule(sess_date)
        if dosu_sessions:
            m_schedule[str(day)] = dosu_sessions
    return m_schedule


def get_or_create(model, **kwargs):
    """
    Either retrieve a record matching certain conditions or
    create a new record if none exists.
    """
    instance = db.session.execute(
        db.select(model).filter_by(**kwargs)
    ).scalar_one_or_none()

    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        try:
            db.session.add(instance)
            db.session.commit()
            return instance, True
        except IntegrityError:
            db.session.rollback()
            return (
                db.session.execute(db.select(model).filter_by(**kwargs)).scalar_one(),
                False,
            )
