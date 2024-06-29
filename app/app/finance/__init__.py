from flask import Blueprint

finance = Blueprint('payment', __name__)

from . import views