from functools import wraps
from flask import abort
from flask_login import current_user
from .const import content_type_map

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

# Helper function to convert Arabic numerals to Persian numerals
def to_persian_numerals(number):
    persian_numbers = {
        "0": "۰",
        "1": "۱",
        "2": "۲",
        "3": "۳",
        "4": "۴",
        "5": "۵",
        "6": "۶",
        "7": "۷",
        "8": "۸",
        "9": "۹"
    }
    return ''.join(persian_numbers.get(digit, digit) for digit in str(number))


def gregorian_to_jalali_detail(date):
    gregorian_date = datetime.strptime(str(date), "%Y-%m-%d %H:%M:%S")
    jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
    # Load Persian month names from jdatetime
    months = jdatetime.datetime.j_months_fa

    # Convert the date and time components to Persian numerals
    year = to_persian_numerals(jalali_date.year)
    month = months[jalali_date.month - 1]
    day = to_persian_numerals(jalali_date.day)
    hour = to_persian_numerals(f"{jalali_date.hour:02}")
    minute = to_persian_numerals(f"{jalali_date.minute:02}")
    # second = to_persian_numerals(f"{jalali_date.second:02}")

    # Format Jalali date to desired format
    persian_date_str = f"{hour}:{minute} - {month} {day} {year}"
    
    return persian_date_str


def to_persian_numerals(number):
    persian_numbers = {
        "0": "۰",
        "1": "۱",
        "2": "۲",
        "3": "۳",
        "4": "۴",
        "5": "۵",
        "6": "۶",
        "7": "۷",
        "8": "۸",
        "9": "۹"
    }
    return ''.join(persian_numbers.get(digit, digit) for digit in str(number))

def convert_seconds_to_min_sec(total_seconds):
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    formatted_minutes = f"{minutes:02}"
    formatted_seconds = f"{seconds:02}"

    persian_minutes = to_persian_numerals(formatted_minutes)
    persian_seconds = to_persian_numerals(formatted_seconds)

    return f"{persian_minutes}:{persian_seconds}"
