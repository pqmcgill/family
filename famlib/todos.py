from famlib import dates, events, people


def add(con, source, title, owner=None, due=None, today=None):
    if due:
        dates.parse(due)
    owner_id = people.get_id(con, owner) if owner else None
    with con:
        cur = con.execute(
            "INSERT INTO todos(title, owner_id, due, created) VALUES (?,?,?,?)",
            (title, owner_id, due, today or dates.today()))
        row = events.snapshot(con, "todos", cur.lastrowid)
        events.record(con, source, "todos", cur.lastrowid, "add", None, row)
    return row


def _require(con, tid):
    row = events.snapshot(con, "todos", tid)
    if row is None:
        raise SystemExit("no todo #%s" % tid)
    return row


def _set_status(con, source, tid, status, today):
    before = _require(con, tid)
    if before["status"] in ("done", "dropped"):
        raise SystemExit("todo #%s is already %s — use fam undo to reverse"
                         % (tid, before["status"]))
    with con:
        con.execute("UPDATE todos SET status=?, resolved=? WHERE id=?",
                    (status, today, tid))
        after = events.snapshot(con, "todos", tid)
        events.record(con, source, "todos", tid, status, before, after)
    return after


def done(con, source, tid, today=None):
    return _set_status(con, source, tid, "done", today or dates.today())


def drop(con, source, tid, today=None):
    return _set_status(con, source, tid, "dropped", today or dates.today())


def defer(con, source, tid, to=None):
    if to:
        dates.parse(to)
    before = _require(con, tid)
    if before["status"] in ("done", "dropped"):
        raise SystemExit("todo #%s is already %s — use fam undo to reverse"
                         % (tid, before["status"]))
    with con:
        if to:
            con.execute(
                "UPDATE todos SET due=?, status='open',"
                " defer_count=defer_count+1 WHERE id=?", (to, tid))
        else:
            con.execute(
                "UPDATE todos SET status='deferred', defer_count=defer_count+1"
                " WHERE id=?", (tid,))
        after = events.snapshot(con, "todos", tid)
        events.record(con, source, "todos", tid, "defer", before, after)
    return after


def list_open(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM todos WHERE status='open' ORDER BY due IS NULL, due, id")]


def list_parked(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM todos WHERE status='deferred' ORDER BY id")]
