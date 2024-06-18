import logging

from flask import Flask
# from flask_appbuilder import AppBuilder, SQLA
from flask_mail import Mail
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_pagedown import PageDown
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
login_manager.login_view = 'auth.login'


from celery import Celery, Task

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

"""
 Logging configuration
"""

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

moment = Moment()
mail = Mail()
pagedown = PageDown()
bootstrap = Bootstrap()

app = Flask(__name__)
app.config.from_object("config")

app.config.from_mapping(
    CELERY=dict(
        broker_url="redis://localhost",
        result_backend="redis://localhost",
        task_ignore_result=True,
    ),
)

app.config.from_prefixed_env()
celery_app = celery_init_app(app)


db = SQLAlchemy()
migrate = Migrate(app, db)

db.init_app(app)
login_manager.init_app(app)
bootstrap.init_app(app)
moment.init_app(app)
pagedown.init_app(app)
mail.init_app(app)
"""
from sqlalchemy.engine import Engine
from sqlalchemy import event

#Only include this for SQLLite constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Will force sqllite contraint foreign keys
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
"""


from .main import main as main_blueprint
app.register_blueprint(main_blueprint)

from .dashboard import dashboard as dashboard_blueprint
app.register_blueprint(dashboard_blueprint)

from .auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint, url_prefix='/auth')

from .api import api as api_blueprint
app.register_blueprint(api_blueprint, url_prefix='/api/v1')

# from . import views