from famlib import dates, events, people

KINDS = ("chore", "commitment")
DAYS = dates.DAYS
STATUSES = ("active", "paused", "retired")


def add(con, source, title, kind, grp=None, owner=None, day=None, time=None,
        today=None):
    if kind not in KINDS:
        raise SystemExit("invalid kind: %r (expected chore|commitment)" % kind)
    if day is not None and day not in DAYS:
        raise SystemExit("invalid day: %r (expected mon..sun)" % day)
    if time is not None:
        dates.parse_time(time)
    grp = grp.strip().lower() if grp else None
    owner_id = people.get_id(con, owner) if owner else None
    with con:
        cur = con.execute(
            "INSERT INTO standing(kind, title, grp, owner_id, day, time, created)"
            " VALUES (?,?,?,?,?,?,?)",
            (kind, title, grp, owner_id, day, time, today or dates.today()))
        row = events.snapshot(con, "standing", cur.lastrowid)
        events.record(con, source, "standing", cur.lastrowid, "add", None, row)
    return row


def set_status(con, source, sid, status):
    if status not in STATUSES:
        raise SystemExit("invalid status: %r" % status)
    before = events.snapshot(con, "standing", sid)
    if before is None:
        raise SystemExit("no standing item #%s" % sid)
    if before["status"] == status:
        raise SystemExit("standing item #%s is already %s" % (sid, status))
    with con:
        con.execute("UPDATE standing SET status=? WHERE id=?", (status, sid))
        after = events.snapshot(con, "standing", sid)
        events.record(con, source, "standing", sid, status, before, after)
    return after


def list_items(con, status=None, kind=None):
    q, args = "SELECT * FROM standing WHERE 1=1", []
    if status:
        q += " AND status=?"
        args.append(status)
    if kind:
        q += " AND kind=?"
        args.append(kind)
    return [dict(r) for r in con.execute(q + " ORDER BY kind, grp, id", args)]
