from famlib import dates, events


def add_habit(con, source, name, today=None):
    if not name or not name.strip():
        raise SystemExit("habit name must not be empty")
    dup = con.execute("SELECT status FROM daily_habits WHERE name=?",
                      (name,)).fetchone()
    if dup is not None:
        raise SystemExit("habit %r already exists (status: %s)"
                         % (name, dup["status"]))
    created = today or dates.today()
    dates.parse(created)
    with con:
        cur = con.execute(
            "INSERT INTO daily_habits(name, created) VALUES (?,?)",
            (name, created))
        row = events.snapshot(con, "daily_habits", cur.lastrowid)
        events.record(con, source, "daily_habits", cur.lastrowid, "add",
                      None, row)
    return row


def list_habits(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM daily_habits ORDER BY id")]


def log(con, source, name, date=None, note=None):
    h = con.execute(
        "SELECT * FROM daily_habits WHERE name=? AND status='active'",
        (name,)).fetchone()
    if h is None:
        raise SystemExit("no active habit named %r" % name)
    d = date or dates.today()
    dates.parse(d)
    existing = con.execute(
        "SELECT * FROM daily_log WHERE habit_id=? AND date=?",
        (h["id"], d)).fetchone()
    with con:
        if existing is None:
            cur = con.execute(
                "INSERT INTO daily_log(habit_id, date, note) VALUES (?,?,?)",
                (h["id"], d, note))
            row = events.snapshot(con, "daily_log", cur.lastrowid)
            events.record(con, source, "daily_log", cur.lastrowid, "log",
                          None, row)
        else:
            before = dict(existing)
            con.execute("UPDATE daily_log SET note=COALESCE(?, note) WHERE id=?",
                        (note, existing["id"]))
            row = events.snapshot(con, "daily_log", existing["id"])
            events.record(con, source, "daily_log", existing["id"], "log",
                          before, row)
    return row


def retire_habit(con, source, name):
    before = con.execute(
        "SELECT * FROM daily_habits WHERE name=?", (name,)).fetchone()
    if before is None:
        raise SystemExit("no habit named %r" % name)
    if before["status"] == "retired":
        raise SystemExit("habit %r is already retired" % name)
    with con:
        con.execute("UPDATE daily_habits SET status='retired' WHERE id=?",
                    (before["id"],))
        after = events.snapshot(con, "daily_habits", before["id"])
        events.record(con, source, "daily_habits", before["id"], "retire",
                      dict(before), after)
    return after


def streaks(con, today, min_nights=2):
    """Active habits on a roll: consecutive logged nights ending today
    (or yesterday — tonight may not be logged yet). The celebration
    counterpart to neglect()."""
    out = []
    for h in con.execute(
            "SELECT * FROM daily_habits WHERE status='active' ORDER BY id"):
        logged = {r["date"] for r in con.execute(
            "SELECT date FROM daily_log WHERE habit_id=?", (h["id"],))}
        d = today if today in logged else dates.add_days(today, -1)
        nights = 0
        while d in logged:
            nights += 1
            d = dates.add_days(d, -1)
        if nights >= min_nights:
            out.append({"name": h["name"], "nights": nights})
    return out


def neglect(con, today):
    """Per active habit: today's status, current miss-streak (consecutive
    missed nights ending yesterday — tonight isn't over yet), total missed
    nights since creation, and elapsed nights since creation. The creation
    date is the horizon, so a brand-new habit shows no phantom misses."""
    out = []
    for h in con.execute(
            "SELECT * FROM daily_habits WHERE status='active' ORDER BY id"):
        created = h["created"]
        logged = {r["date"] for r in con.execute(
            "SELECT date FROM daily_log WHERE habit_id=?", (h["id"],))}
        logged_today = today in logged
        elapsed = 0
        total_missed = 0
        d = created
        while dates.days_until(d, today) > 0:
            elapsed += 1
            if d not in logged:
                total_missed += 1
            d = dates.add_days(d, 1)
        miss_streak = 0
        d = dates.add_days(today, -1)
        while dates.days_until(created, d) >= 0:
            if d in logged:
                break
            miss_streak += 1
            d = dates.add_days(d, -1)
        out.append({"name": h["name"], "logged_today": logged_today,
                    "miss_streak": miss_streak, "total_missed": total_missed,
                    "elapsed": elapsed, "since": created})
    return out
