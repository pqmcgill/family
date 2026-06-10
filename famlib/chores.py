from famlib import dates, events


def touch(con, source, name, done_date):
    """Record that a chore happened; learn cadence from observed intervals."""
    if not name or not name.strip():
        raise SystemExit("chore name must not be empty")
    dates.parse(done_date)
    r = con.execute("SELECT * FROM chore_memory WHERE name=?", (name,)).fetchone()
    with con:
        if r is None:
            cur = con.execute(
                "INSERT INTO chore_memory(name, last_done, times_done)"
                " VALUES (?,?,1)", (name, done_date))
            row = events.snapshot(con, "chore_memory", cur.lastrowid)
            events.record(con, source, "chore_memory", cur.lastrowid,
                          "add", None, row)
            return row
        before = dict(r)
        cadence = before["cadence_days"]
        last_done = done_date
        if before["last_done"]:
            interval = dates.days_until(before["last_done"], done_date)
            if interval > 0:
                cadence = float(interval) if cadence is None \
                    else 0.5 * cadence + 0.5 * interval
            else:
                last_done = before["last_done"]  # never regress
        con.execute(
            "UPDATE chore_memory SET last_done=?, times_done=times_done+1,"
            " cadence_days=? WHERE id=?", (last_done, cadence, before["id"]))
        after = events.snapshot(con, "chore_memory", before["id"])
        events.record(con, source, "chore_memory", before["id"],
                      "touch", before, after)
    return after


def set_cadence(con, source, name, days):
    if float(days) <= 0:
        raise SystemExit("cadence must be a positive number of days")
    r = con.execute("SELECT * FROM chore_memory WHERE name=?", (name,)).fetchone()
    if r is None:
        raise SystemExit("no chore named %r in chore memory" % name)
    before = dict(r)
    with con:
        con.execute("UPDATE chore_memory SET cadence_days=? WHERE id=?",
                    (float(days), before["id"]))
        after = events.snapshot(con, "chore_memory", before["id"])
        events.record(con, source, "chore_memory", before["id"],
                      "cadence", before, after)
    return after


NEVER_DONE_GRACE_DAYS = 14


def never_done(con, today, grace_days=NEVER_DONE_GRACE_DAYS):
    """Active standing chores with no completion on record, past grace.

    chores.neglected() can't see these — they have no cadence to be
    overdue against — so without this they'd be invisible forever.
    """
    out = []
    for s in con.execute(
            "SELECT * FROM standing WHERE status='active' AND kind='chore'"
            " ORDER BY id"):
        r = con.execute("SELECT last_done FROM chore_memory WHERE name=?",
                        (s["title"],)).fetchone()
        if r is None or not r["last_done"]:
            age = dates.days_until(s["created"], today)
            if age > grace_days:
                out.append({"title": s["title"], "days": age,
                            "since": s["created"]})
    return out


def neglected(con, today):
    """Chores whose days-since-done exceeds 1.5x their cadence."""
    out = []
    for r in con.execute("SELECT * FROM chore_memory ORDER BY name"):
        if not r["last_done"] or not r["cadence_days"]:
            continue
        since = dates.days_until(r["last_done"], today)
        if since > r["cadence_days"] * 1.5:
            out.append({"name": r["name"], "days_since": since,
                        "cadence_days": round(r["cadence_days"], 1)})
    return out


def list_all(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM chore_memory ORDER BY name")]
