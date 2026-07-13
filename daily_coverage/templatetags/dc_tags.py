import json

import nepali_datetime
from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def bs_date(value, style="full"):
    """Render a Gregorian date (or datetime) as a Bikram Sambat string,
    e.g. "28 Asar 2083" ("short" style drops the year)."""
    if not value:
        return ""
    if hasattr(value, "hour"):  # datetime → date
        value = value.date()
    try:
        bs = nepali_datetime.date.from_datetime_date(value)
    except (TypeError, ValueError):
        return value
    label = f"{bs.day} {bs.strftime('%B')}"
    return label if style == "short" else f"{label} {bs.year}"


@register.simple_tag
def bs_calendar_json(years_back=2, years_ahead=1):
    """BS month table for the client-side Nepali date picker (bs-date.js):
    [{y, m, days, start}] where `start` is the AD date of BS day 1,
    covering the current BS year ± the given range."""
    today_bs = nepali_datetime.date.from_datetime_date(timezone.localdate())
    data = []
    for year in range(today_bs.year - years_back, today_bs.year + years_ahead + 1):
        for month in range(1, 13):
            try:
                start = nepali_datetime.date(year, month, 1)
                if month == 12:
                    nxt = nepali_datetime.date(year + 1, 1, 1)
                else:
                    nxt = nepali_datetime.date(year, month + 1, 1)
            except ValueError:  # outside the package's supported range
                continue
            start_ad = start.to_datetime_date()
            data.append({
                "y": year,
                "m": month,
                "days": (nxt.to_datetime_date() - start_ad).days,
                "start": start_ad.isoformat(),
            })
    return mark_safe(json.dumps(data))
