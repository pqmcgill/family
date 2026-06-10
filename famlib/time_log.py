from famlib import dates, events, people

KINDS = ("personal", "couple", "family")
LEVELS = ("partial", "full")


def add(con, source, kind, who=None, level=None, date=None, note=None):
    """Log restorative time that happened. personal needs an adult + level
    (default partial); couple/family are household-level (no person, no
    level)."""
    if kind not in KINDS:
        raise SystemExit("invalid kind: %r (expected personal|couple|family)"
                         % kind)
    if kind == "personal":
        if who is None:
            raise SystemExit("personal time needs a person:"
                             " fam time log personal <alias>")
        if level is None:
            level = "partial"
        if level not in LEVELS:
            raise SystemExit("invalid level: %r (expected partial|full)"
                             % level)
        p = people.resolve(con, who)
        if p is None:
            raise SystemExit("unknown person: %r — add with: fam person add"
                             " <alias> --role <adult|kid|other>" % who)
        if p["role"] != "adult":
            raise SystemExit("personal-time tracking is for adults only"
                             " (%s is %s)" % (p["alias"], p["role"]))
        person_id = p["id"]
    else:
        if who is not None:
            raise SystemExit("%s time is household-level — drop the alias"
                             % kind)
        if level is not None:
            raise SystemExit("%s time has no level — drop --level" % kind)
        person_id = None
    d = dates.today() if date is None else date
    dates.parse(d)
    with con:
        cur = con.execute(
            "INSERT INTO time_log(date, kind, level, person_id, note)"
            " VALUES (?,?,?,?,?)", (d, kind, level, person_id, note))
        row = events.snapshot(con, "time_log", cur.lastrowid)
        events.record(con, source, "time_log", cur.lastrowid, "log", None, row)
    return row


def recent(con, today, days=14):
    cutoff = dates.add_days(today, -days)
    return [dict(r) for r in con.execute(
        "SELECT t.*, p.alias FROM time_log t LEFT JOIN people p"
        " ON t.person_id = p.id WHERE t.date > ? AND t.date <= ?"
        " ORDER BY t.date DESC, t.id DESC", (cutoff, today))]
