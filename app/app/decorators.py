from functools import wraps
from flask import abort
from flask_login import current_user
from .const import content_type_map

import jdatetime


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    pass
    # return permission_required(Permission.ADMIN)(f)


def show_content_type(content_type: int) -> str:
    return content_type_map[content_type]

def gregorian_to_jalali(date):
    j_date = jdatetime.date.fromgregorian(date=date)
    return j_date.strftime('%Y-%m-%d')
