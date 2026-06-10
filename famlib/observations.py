from famlib import dates, events


def add(con, source, text, date=None):
    if not text or not text.strip():
        raise SystemExit("observation text must not be empty")
    d = date or dates.today()
    dates.parse(d)
    with con:
        cur = con.execute(
            "INSERT INTO observations(date, text) VALUES (?,?)", (d, text))
        row = events.snapshot(con, "observations", cur.lastrowid)
        events.record(con, source, "observations", cur.lastrowid, "add",
                      None, row)
    return row


def archive(con, source, oid):
    before = events.snapshot(con, "observations", oid)
    if before is None:
        raise SystemExit("no observation #%s" % oid)
    if before["status"] == "archived":
        raise SystemExit("observation #%s is already archived — use fam undo"
                         " to reverse" % oid)
    with con:
        con.execute("UPDATE observations SET status='archived' WHERE id=?",
                    (oid,))
        after = events.snapshot(con, "observations", oid)
        events.record(con, source, "observations", oid, "archive",
                      before, after)
    return after


def list_active(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM observations WHERE status='active' ORDER BY id")]
