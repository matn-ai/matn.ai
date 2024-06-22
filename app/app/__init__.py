import logging
import click
from os import getenv
from flask import Flask

# from flask_appbuilder import AppBuilder, SQLA
from flask_mail import Mail
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_pagedown import PageDown
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient

login_manager = LoginManager()
login_manager.login_view = "auth.login"

mongodb_uri = "mongodb://%s:%s/" % (
    getenv("MONGO_HOST") if getenv("MONGO_HOST") else 'localhost' ,
    getenv("MONGO_PORT") if getenv("MONGO_PORT") else '27017',
)


# mongodb_uri = "mongodb://%s:%s@%s:%s/" % (
#     getenv("MONGO_USER"),
#     getenv("MONGO_PASSWORD"),
#     getenv("MONGO_HOST"),
#     getenv("MONGO_PORT") if getenv("MONGO_PORT") else '27017',
# )

if getenv("DEBUG"):
    mongodb_uri = "mongodb://%s:%s/" % (
        getenv("MONGO_HOST") if getenv("MONGO_HOST") else 'localhost' ,
        getenv("MONGO_PORT") if getenv("MONGO_PORT") else '27017',
    )


client = MongoClient(mongodb_uri)
mdb = client[getenv("MONGO_DB") if getenv("MONGO_DB") else 'app']
contents_collection = mdb["contents"]

# # Ensure the collection is created (if not exists)
# if "contents" not in mdb.list_collection_names():
#     contents_collection = mdb.create_collection("contents")


@login_manager.user_loader
def load_user(user_id):
    from .models import User

    return User.query.get(user_id)


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
        broker_url=getenv("CELERY_BROKER"),
        result_backend=getenv("CELERY_RESULT_BACKEND"),
        task_ignore_result=True,
    ),
)


celery_app = celery_init_app(app)


db = SQLAlchemy()
migrate = Migrate(app, db)

db.init_app(app)
login_manager.init_app(app)
bootstrap.init_app(app)
moment.init_app(app)
pagedown.init_app(app)
mail.init_app(app)


from .main import main as main_blueprint

app.register_blueprint(main_blueprint)

from .dashboard import dashboard as dashboard_blueprint

app.register_blueprint(dashboard_blueprint)

from .auth import auth as auth_blueprint

app.register_blueprint(auth_blueprint, url_prefix="/auth")

from .api import api as api_blueprint

app.register_blueprint(api_blueprint, url_prefix="/api/v1")

from .decorators import show_content_type, gregorian_to_jalali
app.jinja_env.filters['show_content_type'] = show_content_type
app.jinja_env.filters['gregorian_to_jalali'] = gregorian_to_jalali


@app.cli.command("create-admin")
@click.argument("username")
@click.argument("email")
@click.argument("password")
def create_admin(username, email, password):
    """Create an admin user."""
    with app.app_context():
        from .models import Role, User

        user = User(username=username, email=email, confirmed=True)
        user.password = password
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user {username} created successfully.")
