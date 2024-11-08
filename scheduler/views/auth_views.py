import functools

from flask import Blueprint, flash, g, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import redirect

from scheduler import db
from scheduler.forms import UserForm, UserLoginForm, UserModifyForm
from scheduler.models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/list")
def user_list():
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("main.monthly"))

    users = db.session.execute(
        db.select(User).order_by(User.privilege.desc(), User.id.desc())
    ).scalars()
    return render_template("auth/list_user.html", users=users)


@bp.route("/signup", methods=("GET", "POST"))
def signup():
    form = UserForm()
    if request.method == "POST" and form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter(User.username == form.username.data)
        ).first()
        if not user:
            user = User(
                username=form.username.data,
                password=generate_password_hash(form.password1.data),
                email=form.email.data,
            )
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("main.monthly"))
        else:
            flash("이미 존재하는 사용자입니다.")
    return render_template("auth/form.html", form=form)


@bp.route("/update/<int:user_id>", methods=("GET", "POST"))
def update(user_id):
    user = db.get_or_404(User, user_id)

    if g.user != user:
        flash("수정권한이 없습니다")
        return redirect(url_for("main.monthly"))

    if request.method == "POST":
        form = UserForm()
        if form.validate_on_submit():
            user.password = generate_password_hash(form.password1.data)
            user.email = form.email.data
            db.session.commit()
            return redirect(url_for("main.monthly"))

    form = UserForm(obj=user)
    return render_template("auth/form.html", form=form)


@bp.route("/login/", methods=("GET", "POST"))
def login():
    form = UserLoginForm()
    if request.method == "POST" and form.validate_on_submit():
        error = None
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            error = "존재하지 않는 사용자입니다."
        elif not user.available:
            error = "정지된 사용자입니다."
        elif not check_password_hash(user.password, form.password.data):
            error = "비밀번호가 올바르지 않습니다."
        if error is None:
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("main.monthly"))
        flash(error)
    return render_template("auth/login.html", form=form)


@bp.route("modify_user/<int:id>", methods=("GET", "POST"))
def user_modify(id):
    """
    This function is for admin to modify a user account
    """
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("main.monthly"))

    user = db.get_or_404(User, id)
    if request.method == "POST":
        form = UserModifyForm()
        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            user.privilege = form.privilege.data
            user.available = form.available.data == "yes"

            if form.password1.data and form.password1.data != "":
                user.password = generate_password_hash(form.password1.data)
            try:
                db.session.commit()
                return redirect(url_for("auth.user_list"))
            except Exception as e:
                db.session.rollback()
                flash(f"User: Failed updating {user.username}: {e}")

    form = UserModifyForm(obj=user)
    return render_template("auth/modify_user.html", form=form)


@bp.route("/delete/<int:id>", methods=["GET", "POST"])
def user_delete(id):
    if not g.user or g.user.privilege != 5:
        flash("권한이 없습니다")
        return redirect(url_for("auth.user_list"))

    user = db.get_or_404(User, id)
    if request.method == "POST":
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("auth.user_list"))
    else:  # GET
        return render_template(
            "delete.html",
            entity_type="User",
            entity_name=user.username,
            entity_id=user.id,
            entity_delete_url="auth.user_delete",
            entity_list_url="auth.user_list",
        )


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


@bp.route("/logout/")
def logout():
    session.clear()
    return redirect(url_for("main.monthly"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
