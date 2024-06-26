from functools import wraps
from flask import abort
from flask_login import current_user
from .const import content_type_map
from .utils import utils_gre2jalali, to_persian_numerals

import jdatetime
from datetime import datetime

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

def to_persian_num(num):
    return to_persian_numerals(num)


def gregorian_to_jalali_detail(date):
    return utils_gre2jalali(date)

def convert_seconds_to_min_sec(total_seconds):
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    formatted_minutes = f"{minutes:02}"
    formatted_seconds = f"{seconds:02}"

    persian_minutes = to_persian_numerals(formatted_minutes)
    persian_seconds = to_persian_numerals(formatted_seconds)

    return f"{persian_minutes}:{persian_seconds}"
