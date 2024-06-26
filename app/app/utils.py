
import jdatetime
from datetime import datetime

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


def utils_gre2jalali(date):
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
    persian_date_str = f"{hour}:{minute} - {day} {month} {year}"
    
    return persian_date_str
