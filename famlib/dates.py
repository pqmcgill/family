from datetime import date, datetime, timedelta

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

ROLLOVER_HOUR = 4  # before 04:00 the "family day" is still yesterday


def effective_today(now=None):
    """The family day: a check-in just past midnight describes the night
    that began the previous calendar day, so it lands on that date."""
    n = now or datetime.now()
    d = n.date()
    if n.hour < ROLLOVER_HOUR:
        d -= timedelta(days=1)
    return d.isoformat()


def today():
    return effective_today()


def dow(s):
    """Weekday name (mon..sun) for a YYYY-MM-DD date."""
    return DAYS[parse(s).weekday()]


def parse(s):
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        raise SystemExit("invalid date: %r (expected YYYY-MM-DD)" % (s,))


def week_start(s):
    d = parse(s)
    return (d - timedelta(days=d.weekday())).isoformat()


def days_until(frm, to):
    """Days from frm to to; negative if to is in the past."""
    return (parse(to) - parse(frm)).days


def add_days(s, n):
    return (parse(s) + timedelta(days=n)).isoformat()


def parse_time(s):
    """Validate optional HH:MM (24h). Returns s; raises on bad format."""
    if s is None:
        return None
    import re
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", s):
        raise SystemExit("invalid time: %r (expected HH:MM, 24h)" % (s,))
    return s
