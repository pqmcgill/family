from famlib import chores, dates, events, people, todos

ENTRY_KINDS = ("chore", "personal", "oneoff")


def new_week(con, source, start=None, today=None):
    """Create a week and draft entries from active standing chores.

    Refuses to draft while any earlier week still has pending entries —
    every item must be dispositioned (done or skipped) so nothing exits
    the visible set without an explicit decision.
    """
    start = dates.week_start(start or today or dates.today())
    if con.execute("SELECT 1 FROM weeks WHERE start=?", (start,)).fetchone():
        raise SystemExit("week %s already exists" % start)
    stale = [dict(r) for r in con.execute(
        "SELECT e.*, w.start AS week_start FROM week_entries e"
        " JOIN weeks w ON e.week_id = w.id"
        " WHERE e.status='pending' AND w.start < ? ORDER BY w.start, e.id",
        (start,))]
    if stale:
        lines = ["  #%d %s (week of %s)" % (e["id"], e["title"],
                                            e["week_start"]) for e in stale]
        raise SystemExit(
            "cannot draft week %s — %d pending entr%s from earlier weeks"
            " need a decision first:\n%s\n"
            "disposition each: fam week done <id> | fam week skip <id>;"
            " carry one forward by re-adding it to the new week after"
            " drafting (fam week add ...)"
            % (start, len(stale), "y" if len(stale) == 1 else "ies",
               "\n".join(lines)))
    with con:
        cur = con.execute("INSERT INTO weeks(start, created) VALUES (?,?)",
                          (start, today or dates.today()))
        wid = cur.lastrowid
        events.record(con, source, "weeks", wid, "add", None,
                      events.snapshot(con, "weeks", wid))
        for s in con.execute(
                "SELECT * FROM standing WHERE status='active' AND kind='chore'"
                " ORDER BY id"):
            c2 = con.execute(
                "INSERT INTO week_entries(week_id, kind, title, owner_id,"
                " standing_id) VALUES (?, 'chore', ?, ?, ?)",
                (wid, s["title"], s["owner_id"], s["id"]))
            events.record(con, source, "week_entries", c2.lastrowid, "draft",
                          None, events.snapshot(con, "week_entries", c2.lastrowid))
    return wid, start


def week_for(con, date_):
    start = dates.week_start(date_)
    r = con.execute("SELECT * FROM weeks WHERE start=?", (start,)).fetchone()
    return dict(r) if r else None


def entries(con, week_id):
    return [dict(r) for r in con.execute(
        "SELECT * FROM week_entries WHERE week_id=? ORDER BY kind, id",
        (week_id,))]


def _check_day(day):
    if day is not None and day not in dates.DAYS:
        raise SystemExit("invalid day: %r (expected mon..sun)" % day)


def add_entry(con, source, week_id, kind, title, owner=None, note=None,
              day=None, todo_id=None):
    _check_day(day)
    if kind not in ENTRY_KINDS:
        raise SystemExit("invalid entry kind: %r (chore|personal|oneoff)" % kind)
    if not con.execute("SELECT 1 FROM weeks WHERE id=?", (week_id,)).fetchone():
        raise SystemExit("no week #%s" % week_id)
    if todo_id is not None:
        _check_todo(con, todo_id)
    owner_id = people.get_id(con, owner) if owner else None
    with con:
        cur = con.execute(
            "INSERT INTO week_entries(week_id, kind, title, owner_id, note,"
            " day, todo_id) VALUES (?,?,?,?,?,?,?)",
            (week_id, kind, title, owner_id, note, day, todo_id))
        row = events.snapshot(con, "week_entries", cur.lastrowid)
        events.record(con, source, "week_entries", cur.lastrowid, "add",
                      None, row)
    return row


def skip_streaks(con, min_weeks=2):
    """Active standing chores skipped in min_weeks+ consecutive most-recent
    weeks. A 'skipped' status reads like resolution but repeated skips are
    neglect; pending entries are ignored (the current week isn't over)."""
    out = []
    for s in con.execute(
            "SELECT * FROM standing WHERE status='active' AND kind='chore'"
            " ORDER BY id"):
        streak = 0
        for r in con.execute(
                "SELECT e.status FROM week_entries e JOIN weeks w"
                " ON e.week_id = w.id WHERE e.standing_id=?"
                " ORDER BY w.start DESC", (s["id"],)):
            if r["status"] == "skipped":
                streak += 1
            elif r["status"] == "done":
                break
        if streak >= min_weeks:
            out.append({"title": s["title"], "standing_id": s["id"],
                        "weeks_skipped": streak})
    return out


def set_day(con, source, eid, day):
    _check_day(day)
    before = events.snapshot(con, "week_entries", eid)
    if before is None:
        raise SystemExit("no week entry #%s" % eid)
    with con:
        con.execute("UPDATE week_entries SET day=? WHERE id=?", (day, eid))
        after = events.snapshot(con, "week_entries", eid)
        events.record(con, source, "week_entries", eid, "day", before, after)
    return after


def _check_todo(con, todo_id):
    t = con.execute("SELECT status FROM todos WHERE id=?",
                    (todo_id,)).fetchone()
    if t is None:
        raise SystemExit("no todo #%s" % todo_id)
    if t["status"] not in ("open", "deferred"):
        raise SystemExit("todo #%s is already %s — link an open todo"
                         % (todo_id, t["status"]))


def set_todo(con, source, eid, todo_id):
    _check_todo(con, todo_id)
    before = events.snapshot(con, "week_entries", eid)
    if before is None:
        raise SystemExit("no week entry #%s" % eid)
    with con:
        con.execute("UPDATE week_entries SET todo_id=? WHERE id=?",
                    (todo_id, eid))
        after = events.snapshot(con, "week_entries", eid)
        events.record(con, source, "week_entries", eid, "link", before, after)
    return after


STAGES = ("wash", "dry", "fold")
STUCK_STAGE_DAYS = 2


def set_stage(con, source, eid, stage, date=None):
    """Track a multi-step entry mid-pipeline (laundry: wash → dry → fold).
    Finishing is fam week done — there is no terminal stage."""
    if stage not in STAGES:
        raise SystemExit("invalid stage: %r (expected wash|dry|fold;"
                         " finished = fam week done)" % stage)
    before = events.snapshot(con, "week_entries", eid)
    if before is None:
        raise SystemExit("no week entry #%s" % eid)
    if before["status"] != "pending":
        raise SystemExit("week entry #%s is %s — stages only apply to"
                         " pending entries" % (eid, before["status"]))
    d = date or dates.today()
    dates.parse(d)
    with con:
        con.execute("UPDATE week_entries SET stage=?, stage_date=?"
                    " WHERE id=?", (stage, d, eid))
        after = events.snapshot(con, "week_entries", eid)
        events.record(con, source, "week_entries", eid, "stage",
                      before, after)
    return after


def stuck_stages(con, today, min_days=STUCK_STAGE_DAYS):
    """Pending entries sitting in a pipeline stage too long — a load
    in the dryer for days looks started but is silently stalled."""
    out = []
    for e in con.execute(
            "SELECT * FROM week_entries WHERE status='pending'"
            " AND stage IS NOT NULL ORDER BY id"):
        days = dates.days_until(e["stage_date"], today)
        if days >= min_days:
            out.append({"id": e["id"], "title": e["title"],
                        "stage": e["stage"], "days": days,
                        "since": e["stage_date"]})
    return out


def set_note(con, source, eid, note):
    before = events.snapshot(con, "week_entries", eid)
    if before is None:
        raise SystemExit("no week entry #%s" % eid)
    with con:
        con.execute("UPDATE week_entries SET note=? WHERE id=?", (note, eid))
        after = events.snapshot(con, "week_entries", eid)
        events.record(con, source, "week_entries", eid, "note", before, after)
    return after


def _set_entry(con, source, eid, status, date_=None):
    before = events.snapshot(con, "week_entries", eid)
    if before is None:
        raise SystemExit("no week entry #%s" % eid)
    if before["status"] == "done":
        raise SystemExit("week entry #%s is already done — use fam undo"
                         " to reverse" % eid)
    if before["status"] == status:
        raise SystemExit("week entry #%s is already %s" % (eid, status))
    with con:
        con.execute("UPDATE week_entries SET status=?, done_date=? WHERE id=?",
                    (status, date_, eid))
        after = events.snapshot(con, "week_entries", eid)
        events.record(con, source, "week_entries", eid, status, before, after)
    return after


def entry_done(con, source, eid, date=None):
    d = date or dates.today()
    after = _set_entry(con, source, eid, "done", d)
    if after["kind"] == "chore":
        chores.touch(con, source, after["title"], d)
    if after["todo_id"]:
        t = con.execute("SELECT status FROM todos WHERE id=?",
                        (after["todo_id"],)).fetchone()
        if t and t["status"] in ("open", "deferred"):
            todos.done(con, source, after["todo_id"], today=d)
    return after


def entry_skip(con, source, eid):
    return _set_entry(con, source, eid, "skipped")
