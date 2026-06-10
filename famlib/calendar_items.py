from famlib import dates, events, people


def add(con, source, title, date, time=None, who=None, today=None):
    dates.parse(date)
    dates.parse_time(time)
    who_id = people.get_id(con, who) if who else None
    with con:
        cur = con.execute(
            "INSERT INTO calendar(title, date, time, who_id, created)"
            " VALUES (?,?,?,?,?)",
            (title, date, time, who_id, today or dates.today()))
        row = events.snapshot(con, "calendar", cur.lastrowid)
        events.record(con, source, "calendar", cur.lastrowid, "add", None, row)
    return row


def _set_status(con, source, cid, status):
    before = events.snapshot(con, "calendar", cid)
    if before is None:
        raise SystemExit("no calendar item #%s" % cid)
    if before["status"] in ("done", "cancelled"):
        raise SystemExit("calendar item #%s is already %s — use fam undo"
                         " to reverse" % (cid, before["status"]))
    with con:
        con.execute("UPDATE calendar SET status=? WHERE id=?", (status, cid))
        after = events.snapshot(con, "calendar", cid)
        events.record(con, source, "calendar", cid, status, before, after)
    return after


def done(con, source, cid):
    return _set_status(con, source, cid, "done")


def cancel(con, source, cid):
    return _set_status(con, source, cid, "cancelled")


def upcoming(con, today, days=14):
    """Scheduled items from today forward; days=None means no upper bound."""
    q = "SELECT * FROM calendar WHERE status='scheduled' AND date >= ?"
    args = [today]
    if days is not None:
        q += " AND date <= ?"
        args.append(dates.add_days(today, days))
    q += " ORDER BY date, time IS NULL, time, id"
    return [dict(r) for r in con.execute(q, args)]
