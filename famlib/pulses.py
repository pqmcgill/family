from famlib import dates, events, people


def log(con, source, alias, rating, note=None, date=None):
    if isinstance(rating, bool) or not isinstance(rating, int) \
            or not 1 <= rating <= 10:
        raise SystemExit("rating must be an integer 1-10 (10 = great)")
    p = people.resolve(con, alias)
    if p is None:
        raise SystemExit(
            "unknown person: %r — add with: fam person add" % alias)
    if p["role"] != "adult":
        raise SystemExit("pulses are for adults only (%s is %s)"
                         % (p["alias"], p["role"]))
    d = date or dates.today()
    dates.parse(d)
    existing = con.execute(
        "SELECT * FROM pulses WHERE person_id=? AND date=?",
        (p["id"], d)).fetchone()
    with con:
        if existing is None:
            cur = con.execute(
                "INSERT INTO pulses(person_id, date, rating, note)"
                " VALUES (?,?,?,?)", (p["id"], d, rating, note))
            rid = cur.lastrowid
            events.record(con, source, "pulses", rid, "log", None,
                          events.snapshot(con, "pulses", rid))
        else:
            con.execute("UPDATE pulses SET rating=?, note=? WHERE id=?",
                        (rating, note, existing["id"]))
            rid = existing["id"]
            events.record(con, source, "pulses", rid, "log", dict(existing),
                          events.snapshot(con, "pulses", rid))
    return events.snapshot(con, "pulses", rid)


def recent(con, today, days=7):
    cutoff = dates.add_days(today, -days)
    return [dict(r) for r in con.execute(
        "SELECT p.*, ppl.alias FROM pulses p JOIN people ppl"
        " ON p.person_id = ppl.id WHERE p.date > ? AND p.date <= ?"
        " ORDER BY p.date, ppl.alias", (cutoff, today))]
