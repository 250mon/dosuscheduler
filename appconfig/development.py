from appconfig.default import BASE_DIR

SQLALCHEMY_DATABASE_URI = "sqlite:///{}".format(os.path.join(BASE_DIR, "scheduler.db"))
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = "dev"
