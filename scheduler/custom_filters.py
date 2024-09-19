from datetime import date, datetime, time

from flask import Blueprint

# Create a blueprint for filters (optional, if you want to organize them)
bp = Blueprint("filters", __name__)


def format_kr_date(value):
    """
    When a value is a datetime or date, get a weekday in korean
    """
    if isinstance(value, (datetime, date)):
        custom_weekdays = {
            "Monday": "월",
            "Tuesday": "화",
            "Wednesday": "수",
            "Thursday": "목",
            "Friday": "금",
            "Saturday": "토",
            "Sunday": "일",
        }
        formatted_date = value.strftime("%m.%d %A").lstrip("0").replace(".0", ".")
        weekday = value.strftime("%A")
        return formatted_date.replace(weekday, custom_weekdays.get(weekday, weekday))
    return value


def format_birthday_date(value):
    """
    Format a birthday in 6 digits
    """
    if isinstance(value, (datetime, date)):
        return value.strftime("%y.%m.%d")
    return value


def format_date(value, format="%Y-%m-%d"):
    """
    Format a date in a given format
    """
    if isinstance(value, (datetime, date)):
        return value.strftime(format)
    return value


def format_time(value, format="%H:%M"):
    """
    Format a date in a given format
    """
    if isinstance(value, (datetime, time)):
        return value.strftime(format)
    return value


def format_currency(value):
    """
    Format currency
    """
    if isinstance(value, float):
        value = int(value)

    if isinstance(value, int):
        return "{:,}".format(value)

    return value


# Register the filter
bp.add_app_template_filter(format_kr_date)
bp.add_app_template_filter(format_birthday_date)
bp.add_app_template_filter(format_date)
bp.add_app_template_filter(format_time)
bp.add_app_template_filter(format_currency)
