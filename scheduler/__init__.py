from datetime import datetime

from flask import Flask, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData
from werkzeug.routing import BaseConverter, ValidationError


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()


def page_not_found(e):
    return render_template("404.html"), 404


class DateConverter(BaseConverter):
    def to_python(self, value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return value.strftime("%Y-%m-%d")


def create_app(test_config=None):
    app = Flask(__name__)
    # app.config.from_object(config)
    app.config.from_envvar("APP_CONFIG_FILE")

    # ORM
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        migrate.init_app(app, db, render_as_batch=True)
    else:
        migrate.init_app(app, db)

    db.init_app(app)

    csrf = CSRFProtect(app)

    app.url_map.converters["date"] = DateConverter

    from . import custom_filters
    from .views import (
        auth_views,
        config_views,
        dosusess_views,
        dosutype_views,
        main_views,
        patient_views,
        stats_views,
        worker_views,
    )

    app.register_blueprint(custom_filters.bp)
    app.register_blueprint(main_views.bp)
    app.register_blueprint(patient_views.bp)
    app.register_blueprint(worker_views.bp)
    app.register_blueprint(dosutype_views.bp)
    app.register_blueprint(dosusess_views.bp)
    app.register_blueprint(stats_views.bp)
    app.register_blueprint(auth_views.bp)
    app.register_blueprint(config_views.bp)

    with app.app_context():
        db.create_all()
        from scheduler.defaults import create_defaults
        create_defaults()

    app.register_error_handler(404, page_not_found)

    return app
