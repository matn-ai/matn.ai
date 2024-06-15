from flask import Blueprint

dashboard = Blueprint('dashboard', __name__)

from . import views, errors
from ..models import Permission


@dashboard.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
