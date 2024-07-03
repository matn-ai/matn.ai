from flask import Blueprint

finance = Blueprint('finance', __name__)

from . import views