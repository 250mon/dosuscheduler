import calendar

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from scheduler import db
from scheduler.forms import ConfigForm
from scheduler.models import TimeSlotConfig

bp = Blueprint("config", __name__, url_prefix="/config")


@bp.route("/list")
def config_list():
    configs = db.session.execute(db.select(TimeSlotConfig)).scalars()
    return render_template("config/list.html", configs=configs)


@bp.route("/create", methods=["GET", "POST"])
def config_create():
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("config.config_list"))

    form = ConfigForm()
    if request.method == "POST" and form.validate_on_submit():
        name = form.name.data
        is_default = form.is_default.data == "yes"
        start_date = form.start_date.data.replace(day=1)
        edate = form.end_date.data
        end_date = edate.replace(day=calendar.monthrange(edate.year, edate.month)[1])
        # weekdays
        wd_start_hour = form.wd_start_hour.data
        wd_end_hour = form.wd_end_hour.data
        wd_lunch_start_hour = form.wd_lunch_start_hour.data
        wd_lunch_end_hour = form.wd_lunch_end_hour.data
        wd_overtime_hour = form.wd_overtime_hour.data
        # saturday
        sd_start_hour = form.sd_start_hour.data
        sd_end_hour = form.sd_end_hour.data
        sd_overtime_hour = form.sd_overtime_hour.data

        duration = form.duration.data

        try:
            config = TimeSlotConfig(
                name=name,
                is_default=is_default,
                start_date=start_date,
                end_date=end_date,
                wd_start_hour=wd_start_hour,
                wd_end_hour=wd_end_hour,
                wd_lunch_start_hour=wd_lunch_start_hour,
                wd_lunch_end_hour=wd_lunch_end_hour,
                wd_overtime_hour=wd_overtime_hour,
                sd_start_hour=sd_start_hour,
                sd_end_hour=sd_end_hour,
                sd_overtime_hour=sd_overtime_hour,
                duration=duration,
            )
            db.session.add(config)
            db.session.commit()
            return redirect(url_for("config.config_detail", id=config.id))
        except Exception as e:
            db.session.rollback()
            flash(f"config: Failed creating {name}: {e}")

    return render_template("config/form.html", form=form)


@bp.route("/update/<int:id>", methods=("GET", "POST"))
def config_update(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("config.config_list"))

    config = db.get_or_404(TimeSlotConfig, id)
    if request.method == "POST":
        form = ConfigForm()
        if form.validate_on_submit():
            config.name = form.name.data
            config.is_default = form.is_default.data == "yes"
            config.start_date = form.start_date.data
            end_date = form.end_date.data
            config.end_date = end_date.replace(
                day=calendar.monthrange(end_date.year, end_date.month)[1]
            )
            # weekdays
            config.wd_start_hour = form.wd_start_hour.data
            config.wd_end_hour = form.wd_end_hour.data
            config.wd_lunch_start_hour = form.wd_lunch_start_hour.data
            config.wd_lunch_end_hour = form.wd_lunch_end_hour.data
            config.wd_overtime_hour = form.wd_overtime_hour.data
            # saturday
            config.sd_start_hour = form.sd_start_hour.data
            config.sd_end_hour = form.sd_end_hour.data
            config.sd_overtime_hour = form.sd_overtime_hour.data
            config.duration = form.duration.data
            try:
                db.session.commit()
                return redirect(url_for("config.config_detail", id=config.id))
            except Exception as e:
                db.session.rollback()
                flash(f"config: Failed updating {config.name}: {e}")

    form = ConfigForm(obj=config)
    return render_template("config/form.html", form=form)


@bp.route("/<int:id>")
def config_detail(id):
    config = db.get_or_404(TimeSlotConfig, id)
    return render_template("config/detail.html", config=config)


@bp.route("/delete/<int:id>", methods=["GET", "POST"])
def config_delete(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("config.config_list"))

    config = db.get_or_404(TimeSlotConfig, id)
    if config.is_default:
        flash("디폴트 셋팅은 삭제할 수 없습니다")
        return redirect(url_for("config.config_list"))
    elif request.method == "POST":
        db.session.delete(config)
        db.session.commit()
        return redirect(url_for("config.config_list"))
    else:  # GET
        return render_template(
            "delete.html",
            entity_type="config",
            entity_name=config.name,
            entity_id=config.id,
            entity_delete_url="config.config_delete",
            entity_list_url="config.config_list",
        )
