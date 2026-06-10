from famlib import (calendar_items, chores, daily, dates, journal,
                    observations, people, pulses, standing, time_log, todos,
                    weeks)

PERSONAL_DROUGHT_DAYS = 7
DOSE_STREAK_DAYS = 2
COUPLE_DROUGHT_DAYS = 30
FAMILY_WEEKLY_TARGET = 2
FAMILY_WINDOW_DAYS = 7


def _when(today, date_):
    n = dates.days_until(today, date_)
    return "overdue by %d days" % -n if n < 0 else "in %d days" % n


def _alias(con, pid):
    if pid is None:
        return "-"
    r = con.execute("SELECT alias FROM people WHERE id=?", (pid,)).fetchone()
    return r["alias"] if r else "?"


def _section(title, lines):
    n = len(lines)
    head = "%s (%d of %d shown)" % (title, n, n)
    return [head] + (["  " + l for l in lines] or ["  (none)"])


def _todo_line(con, t, today):
    bits = ["#%d %s" % (t["id"], t["title"]), "@" + _alias(con, t["owner_id"])]
    if t["due"]:
        bits.append("due %s (%s)" % (t["due"], _when(today, t["due"])))
    if t["defer_count"]:
        bits.append("deferred %dx" % t["defer_count"])
    return "  ".join(bits)


def _observation_horizon(con):
    """Earliest date the system was watching: first week start or first
    time_log entry, whichever is older. None -> nothing to measure against."""
    w = con.execute("SELECT MIN(start) AS m FROM weeks").fetchone()["m"]
    t = con.execute("SELECT MIN(date) AS m FROM time_log").fetchone()["m"]
    cands = [x for x in (w, t) if x is not None]
    return min(cands) if cands else None


def _last_personal(con, person_id, full_only):
    """Most recent personal time for an adult, unioned across done planned
    week entries (always count as full) and the ad-hoc time_log."""
    we = con.execute(
        "SELECT MAX(done_date) AS d FROM week_entries"
        " WHERE kind='personal' AND status='done' AND owner_id=?",
        (person_id,)).fetchone()["d"]
    q = "SELECT MAX(date) AS d FROM time_log WHERE kind='personal'" \
        " AND person_id=?"
    if full_only:
        q += " AND level='full'"
    tl = con.execute(q, (person_id,)).fetchone()["d"]
    return max(filter(None, (we, tl)), default=None)


def personal_droughts(con, today):
    """Adults whose last FULL personal-time block is too long ago.

    Full = a done planned personal week entry, or an ad-hoc time_log
    personal entry with level='full'. Returns [{"alias", "days_since",
    "since"}]; days_since is None when the adult has no qualifying record
    (since = observation horizon). No horizon yet -> no flags.
    """
    horizon = _observation_horizon(con)
    if horizon is None:
        return []
    horizon_days = dates.days_until(horizon, today)
    flags = []
    for a in con.execute(
            "SELECT * FROM people WHERE role='adult' AND active=1 ORDER BY id"):
        last_full = _last_personal(con, a["id"], full_only=True)
        if last_full is not None:
            days_since = dates.days_until(last_full, today)
            if days_since > PERSONAL_DROUGHT_DAYS:
                flags.append({"alias": a["alias"], "days_since": days_since,
                              "since": last_full})
        elif horizon_days > PERSONAL_DROUGHT_DAYS:
            flags.append({"alias": a["alias"], "days_since": None,
                          "since": horizon})
    return flags


def dose_streaks(con, today):
    """Adults with DOSE_STREAK_DAYS+ consecutive days since personal time of
    ANY level (planned-done or ad-hoc, partial counts)."""
    horizon = _observation_horizon(con)
    if horizon is None:
        return []
    horizon_days = dates.days_until(horizon, today)
    flags = []
    for a in con.execute(
            "SELECT * FROM people WHERE role='adult' AND active=1 ORDER BY id"):
        last = _last_personal(con, a["id"], full_only=False)
        if last is not None:
            days_since = dates.days_until(last, today)
            if days_since >= DOSE_STREAK_DAYS:
                flags.append({"alias": a["alias"], "days_since": days_since,
                              "since": last})
        elif horizon_days >= DOSE_STREAK_DAYS:
            flags.append({"alias": a["alias"], "days_since": None,
                          "since": horizon})
    return flags


def _dose_lines(streaks):
    lines = []
    for f in streaks:
        if f["days_since"] is not None:
            lines.append("%s — %d days without any personal time (even"
                         " partial)" % (f["alias"], f["days_since"]))
        else:
            lines.append("%s — no personal time of any kind on record"
                         " (since %s)" % (f["alias"], f["since"]))
    return lines


def together_droughts(con, today):
    """Couple drought (>COUPLE_DROUGHT_DAYS since last couple moment) and
    family slippage (<FAMILY_WEEKLY_TARGET moments in the trailing
    FAMILY_WINDOW_DAYS). Both respect the observation-horizon grace."""
    horizon = _observation_horizon(con)
    if horizon is None:
        return []
    horizon_days = dates.days_until(horizon, today)
    flags = []
    last = con.execute(
        "SELECT MAX(date) AS d FROM time_log WHERE kind='couple'"
        ).fetchone()["d"]
    if last is not None:
        days_since = dates.days_until(last, today)
        if days_since > COUPLE_DROUGHT_DAYS:
            flags.append({"kind": "couple", "days_since": days_since,
                          "since": last})
    elif horizon_days > COUPLE_DROUGHT_DAYS:
        flags.append({"kind": "couple", "days_since": None,
                      "since": horizon})
    if horizon_days >= FAMILY_WINDOW_DAYS:
        cutoff = dates.add_days(today, -FAMILY_WINDOW_DAYS)
        n = con.execute(
            "SELECT COUNT(*) AS n FROM time_log WHERE kind='family'"
            " AND date > ? AND date <= ?", (cutoff, today)).fetchone()["n"]
        if n < FAMILY_WEEKLY_TARGET:
            flags.append({"kind": "family", "count": n})
    return flags


def _together_lines(flags):
    lines = []
    for f in flags:
        if f["kind"] == "couple":
            if f["days_since"] is not None:
                lines.append("couple — %d days since last couple time"
                             % f["days_since"])
            else:
                lines.append("couple — no couple time on record (since %s)"
                             % f["since"])
        else:
            lines.append("family — %d of %d family moments in last %d days"
                         % (f["count"], FAMILY_WEEKLY_TARGET,
                            FAMILY_WINDOW_DAYS))
    return lines


def _drought_lines(droughts):
    lines = []
    for f in droughts:
        if f["days_since"] is not None:
            lines.append("%s — %d days since last personal time"
                         % (f["alias"], f["days_since"]))
        else:
            lines.append("%s — no personal time on record (since %s)"
                         % (f["alias"], f["since"]))
    return lines


def _habit_lines(flags):
    lines = []
    for f in flags:
        if f["logged_today"]:
            lines.append("%s — ✓ logged tonight" % f["name"])
        elif f["miss_streak"] == 0:
            lines.append("%s — not yet logged tonight" % f["name"])
        else:
            lines.append(
                "%s — not yet tonight; MISSED %d night%s running"
                " (%d of %d nights since %s)" % (
                    f["name"], f["miss_streak"],
                    "" if f["miss_streak"] == 1 else "s",
                    f["total_missed"], f["elapsed"], f["since"]))
    return lines


NIGHTLY_GAP_DAYS = 1
WEEKLY_GAP_DAYS = 8


def _session_lines(con, today):
    lines = []
    for session, limit, gap_fmt in (
            ("nightly", NIGHTLY_GAP_DAYS,
             lambda n: "GAP: %d night%s unrecorded"
             % (n - 1, "" if n - 1 == 1 else "s")),
            ("weekly", WEEKLY_GAP_DAYS,
             lambda n: "GAP: weekly review overdue")):
        last = journal.last_session_date(con, session)
        if last is None:
            lines.append("last %s: never — GAP: no %s session on record"
                         % (session, session))
            continue
        n = dates.days_until(last, today)
        line = "last %s: %s (%d day%s ago)" % (session, last, n,
                                               "" if n == 1 else "s")
        if n > limit:
            line += " — " + gap_fmt(n)
        lines.append(line)
    return lines


def _stage_tag(e):
    if e["status"] == "pending" and e["stage"]:
        return "  [%s since %s]" % (e["stage"], e["stage_date"])
    return ""


def _entry_line(con, e, suffix=""):
    return "#%d %s  @%s%s%s%s" % (
        e["id"], e["title"], _alias(con, e["owner_id"]), suffix,
        _stage_tag(e),
        "  (%s)" % e["note"] if e["note"] else "")


def _plan_split(con, wk, today):
    """Pending week entries bucketed against today's weekday: due today,
    behind plan (assigned day already passed this week), and unassigned.
    Together with done/skipped these cover every entry — closed world."""
    idx = dates.DAYS.index(dates.dow(today))
    pend = [e for e in weeks.entries(con, wk["id"])
            if e["status"] == "pending"]
    targets = [e for e in pend if e["day"] == dates.dow(today)]
    behind = [e for e in pend
              if e["day"] and dates.DAYS.index(e["day"]) < idx]
    unassigned = [e for e in pend if not e["day"]]
    return targets, behind, unassigned


def _week_rollup(con, wk, today):
    es = weeks.entries(con, wk["id"])
    done = sum(1 for e in es if e["status"] == "done")
    pending = sum(1 for e in es if e["status"] == "pending")
    _, behind, unassigned = _plan_split(con, wk, today)
    days_left = 7 - dates.DAYS.index(dates.dow(today))
    return ("WEEK: %d of %d done, %d pending (%d unscheduled),"
            " %d behind plan, %d day%s left"
            % (done, len(es), pending, len(unassigned), len(behind),
               days_left, "" if days_left == 1 else "s"))


def _plan_sections(con, wk, today):
    targets, behind, unassigned = _plan_split(con, wk, today)
    out = _section("TODAY'S TARGETS (%s)" % dates.dow(today),
                   [_entry_line(con, e) for e in targets])
    out.append("")
    out += _section("BEHIND PLAN (planned day passed, still pending)",
                    [_entry_line(con, e, "  (planned %s)" % e["day"])
                     for e in behind])
    out.append("")
    out += _section("NO DAY ASSIGNED (pending, unscheduled)",
                    [_entry_line(con, e) for e in unassigned])
    return out


def wins(con, today):
    """Positive momentum — celebrate what's working, not just punish
    what isn't. Only genuine wins; an empty list is honest."""
    lines = []
    wk = weeks.week_for(con, today)
    if wk is not None:
        done = sum(1 for e in weeks.entries(con, wk["id"])
                   if e["status"] == "done")
        if done:
            lines.append("%d plan item%s done this week"
                         % (done, "" if done == 1 else "s"))
    for s in daily.streaks(con, today):
        lines.append("%s — %d nights running" % (s["name"], s["nights"]))
    for c in chores.list_all(con):
        if c["last_done"] and c["cadence_days"]:
            since = dates.days_until(c["last_done"], today)
            if since <= c["cadence_days"]:
                lines.append("%s — on rhythm (%d days since, ~%s-day"
                             " cadence)" % (c["name"], since,
                                            round(c["cadence_days"])))
    for a in con.execute(
            "SELECT * FROM people WHERE role='adult' AND active=1 ORDER BY id"):
        last_full = _last_personal(con, a["id"], full_only=True)
        if last_full is not None:
            days = dates.days_until(last_full, today)
            if days <= PERSONAL_DROUGHT_DAYS:
                lines.append("%s — full personal reset %d day%s ago"
                             % (a["alias"], days, "" if days == 1 else "s"))
    # No observation-horizon gate here: that grace exists to avoid
    # phantom NEGLECT flags; logged moments are positive evidence.
    cutoff = dates.add_days(today, -FAMILY_WINDOW_DAYS)
    n = con.execute(
        "SELECT COUNT(*) AS n FROM time_log WHERE kind='family'"
        " AND date > ? AND date <= ?", (cutoff, today)).fetchone()["n"]
    if n >= FAMILY_WEEKLY_TARGET:
        lines.append("family time — %d moments in last %d days"
                     " (target met)" % (n, FAMILY_WINDOW_DAYS))
    return lines


def checkin(con, today):
    out = ["NIGHTLY CHECK-IN — %s" % today, ""]
    out += _section("SESSIONS", _session_lines(con, today))
    out.append("")
    out += _section("WINS", wins(con, today))
    out.append("")
    wk = weeks.week_for(con, today)
    if wk is None:
        out.append("NO WEEK PLAN for week of %s — run /weekly to plan one"
                   % dates.week_start(today))
    else:
        out.append(_week_rollup(con, wk, today))
        out.append("")
        es = weeks.entries(con, wk["id"])
        lines = ["[%s] #%d %s  @%s%s%s%s" % (e["status"], e["id"], e["title"],
                 _alias(con, e["owner_id"]),
                 "  day %s" % e["day"] if e["day"] else "",
                 _stage_tag(e),
                 "  (%s)" % e["note"] if e["note"] else "") for e in es]
        out += _section("WEEK PLAN (week of %s)" % wk["start"], lines)
        out.append("")
        out += _plan_sections(con, wk, today)
    out.append("")
    comm = standing.list_items(con, status="active", kind="commitment")
    out += _section("STANDING COMMITMENTS", [
        "#%d %s  %s %s  @%s" % (s["id"], s["title"], s["day"] or "?",
                                s["time"] or "", _alias(con, s["owner_id"]))
        for s in comm])
    out.append("")
    out += _section("OPEN TODOS",
                    [_todo_line(con, t, today) for t in todos.list_open(con)])
    out.append("")
    overdue = [dict(r) for r in con.execute(
        "SELECT * FROM calendar WHERE status='scheduled' AND date < ?"
        " ORDER BY date, id", (today,))]
    out += _section("UNRESOLVED CALENDAR (date passed, never marked done/cancelled)", [
        "#%d %s  %s %s  @%s  (%d days ago)" % (
            c["id"], c["title"], c["date"], c["time"] or "",
            _alias(con, c["who_id"]), -dates.days_until(today, c["date"]))
        for c in overdue])
    out.append("")
    out += _section("CALENDAR NEXT 14 DAYS", [
        "#%d %s  %s %s  @%s" % (c["id"], c["title"], c["date"],
                                c["time"] or "", _alias(con, c["who_id"]))
        for c in calendar_items.upcoming(con, today, days=14)])
    out.append("")
    out += _section("NEGLECT FLAGS", [
        "%s — %d days since last done (usual ~%s days)"
        % (f["name"], f["days_since"], f["cadence_days"])
        for f in chores.neglected(con, today)] + [
        "%s — never done since added %s (%d days)"
        % (f["title"], f["since"], f["days"])
        for f in chores.never_done(con, today)] + [
        "%s — skipped %d weeks running"
        % (s["title"], s["weeks_skipped"])
        for s in weeks.skip_streaks(con)] + [
        "%s — stuck in %s for %d days (since %s)"
        % (s["title"], s["stage"], s["days"], s["since"])
        for s in weeks.stuck_stages(con, today)])
    out.append("")
    out += _section("NIGHTLY HABITS",
                    _habit_lines(daily.neglect(con, today)))
    out.append("")
    out += _section("PERSONAL TIME DROUGHT",
                    _drought_lines(personal_droughts(con, today))
                    + _dose_lines(dose_streaks(con, today)))
    out.append("")
    out += _section("TOGETHERNESS",
                    _together_lines(together_droughts(con, today)))
    out.append("")
    out += _section("PULSES LAST 7 DAYS", [
        "%s %s: %d%s" % (p["date"], p["alias"], p["rating"],
                         "  (%s)" % p["note"] if p["note"] else "")
        for p in pulses.recent(con, today, days=7)])
    out.append("")
    out += _section("OBSERVATIONS", [
        "#%d %s" % (o["id"], o["text"]) for o in observations.list_active(con)])
    return "\n".join(out)


def horizon(con, today):
    out = ["FULL HORIZON — %s (everything open, no matter how far out)" % today,
           ""]
    wk = weeks.week_for(con, today)
    if wk is not None:
        pend = [e for e in weeks.entries(con, wk["id"])
                if e["status"] == "pending"]
        out += _section("WEEK PLAN PENDING (week of %s)" % wk["start"], [
            _entry_line(con, e, "  day %s" % e["day"] if e["day"] else "")
            for e in pend])
        out.append("")
    dated = []
    for t in todos.list_open(con):
        if t["due"]:
            dated.append((t["due"], "todo #%d %s  @%s  due %s (%s)"
                          % (t["id"], t["title"], _alias(con, t["owner_id"]),
                             t["due"], _when(today, t["due"]))))
    for c in con.execute(
            "SELECT * FROM calendar WHERE status='scheduled' ORDER BY date, id"):
        dated.append((c["date"], "cal  #%d %s  %s %s  @%s (%s)"
                      % (c["id"], c["title"], c["date"], c["time"] or "",
                         _alias(con, c["who_id"]),
                         _when(today, c["date"]))))
    dated.sort(key=lambda x: x[0])
    out += _section("DATED ITEMS", [d[1] for d in dated])
    out.append("")
    out += _section("UNDATED OPEN TODOS", [
        _todo_line(con, t, today) for t in todos.list_open(con)
        if not t["due"]])
    out.append("")
    out += _section("PARKED (deferred indefinitely)", [
        "#%d %s  @%s  deferred %dx" % (t["id"], t["title"],
                                       _alias(con, t["owner_id"]),
                                       t["defer_count"])
        for t in todos.list_parked(con)])
    out.append("")
    out += _section("STANDING ITEMS (active + paused)", [
        "#%d [%s] %s%s  @%s  %s" % (s["id"], s["status"], s["title"],
                                    " (%s)" % s["grp"] if s["grp"] else "",
                                    _alias(con, s["owner_id"]), s["kind"])
        for s in standing.list_items(con) if s["status"] != "retired"])
    out.append("")
    out += _section("CHORE MEMORY", [
        "%s — last done %s, ~every %s days, %dx total"
        % (c["name"], c["last_done"] or "never",
           round(c["cadence_days"], 1) if c["cadence_days"] else "?",
           c["times_done"])
        for c in chores.list_all(con)])
    out.append("")
    out += _section("TIME LOG (last 14 days)", [
        "%s %s%s%s%s" % (t["date"], t["kind"],
                         " (%s)" % t["level"] if t["level"] else "",
                         "  @" + t["alias"] if t["alias"] else "",
                         "  (%s)" % t["note"] if t["note"] else "")
        for t in time_log.recent(con, today, days=14)])
    out.append("")
    out += _section("OBSERVATIONS", [
        "#%d %s" % (o["id"], o["text"]) for o in observations.list_active(con)])
    return "\n".join(out)


def fair(con, today, weeks_back=4):
    cutoff = dates.week_start(dates.add_days(today, -7 * weeks_back))
    out = ["FAIRNESS — trailing %d weeks (weeks starting %s or later)" % (weeks_back, cutoff), ""]
    for a in con.execute(
            "SELECT * FROM people WHERE role='adult' AND active=1 ORDER BY id"):
        row = con.execute(
            "SELECT COUNT(*) AS planned,"
            " SUM(CASE WHEN e.status='done' THEN 1 ELSE 0 END) AS done"
            " FROM week_entries e JOIN weeks w ON e.week_id = w.id"
            " WHERE e.kind='personal' AND e.owner_id=? AND w.start >= ?",
            (a["id"], cutoff)).fetchone()
        pr = con.execute(
            "SELECT AVG(rating) AS avg FROM pulses WHERE person_id=?"
            " AND date >= ?", (a["id"], cutoff)).fetchone()
        tl = con.execute(
            "SELECT SUM(CASE WHEN level='full' THEN 1 ELSE 0 END) AS full_n,"
            " SUM(CASE WHEN level='partial' THEN 1 ELSE 0 END) AS part_n"
            " FROM time_log WHERE kind='personal' AND person_id=?"
            " AND date >= ?", (a["id"], cutoff)).fetchone()
        out.append("%s: %d/%d personal blocks done, %d full + %d partial"
                   " ad-hoc, avg pulse %s"
                   % (a["alias"], row["done"] or 0, row["planned"],
                      tl["full_n"] or 0, tl["part_n"] or 0,
                      round(pr["avg"], 1) if pr["avg"] is not None else "n/a"))
    droughts = personal_droughts(con, today)
    if droughts:
        out.append("")
        out += _drought_lines(droughts)
    return "\n".join(out)


def today_report(con, today):
    """Compact answer to "what's on today": targets, slippage, today's
    calendar, due/overdue todos, habits — with session-gap banner."""
    out = ["TODAY — %s (%s)" % (today, dates.dow(today)), ""]
    out += _section("SESSIONS", _session_lines(con, today))
    out.append("")
    out += _section("WINS", wins(con, today))
    out.append("")
    wk = weeks.week_for(con, today)
    if wk is None:
        out.append("NO WEEK PLAN for week of %s — run /weekly to plan one"
                   % dates.week_start(today))
    else:
        out.append(_week_rollup(con, wk, today))
        out.append("")
        out += _plan_sections(con, wk, today)
    out.append("")
    cal = [c for c in calendar_items.upcoming(con, today, days=0)]
    out += _section("CALENDAR TODAY", [
        "#%d %s  %s  @%s" % (c["id"], c["title"], c["time"] or "",
                             _alias(con, c["who_id"])) for c in cal])
    out.append("")
    due = [t for t in todos.list_open(con)
           if t["due"] and t["due"] <= today]
    out += _section("TODOS DUE TODAY OR OVERDUE",
                    [_todo_line(con, t, today) for t in due])
    out.append("")
    out += _section("NIGHTLY HABITS",
                    _habit_lines(daily.neglect(con, today)))
    return "\n".join(out)


def recall(con, term):
    out = ['RECALL: "%s"' % term, ""]
    like = "%" + term + "%"
    tds = [dict(r) for r in con.execute(
        "SELECT * FROM todos WHERE title LIKE ? ORDER BY id", (like,))]
    out += _section("TODOS", [
        "#%d [%s] %s" % (t["id"], t["status"], t["title"]) for t in tds])
    out.append("")
    obs_hits = [dict(r) for r in con.execute(
        "SELECT * FROM observations WHERE text LIKE ? ORDER BY id", (like,))]
    out += _section("OBSERVATIONS", [
        "#%d [%s] %s" % (o["id"], o["status"], o["text"]) for o in obs_hits])
    out.append("")
    jhits = journal.search(con, term)
    out += _section("JOURNAL", [
        "%s [%s/%s] %s" % (j["date"], j["session"], j["kind"],
                           j["text"].replace("\n", " "))
        for j in jhits])
    return "\n".join(out)


def report(con, today):
    """Human-readable markdown snapshot."""
    return "# Family status — %s\n\n```\n%s\n```\n\n```\n%s\n```\n" % (
        today, checkin(con, today), fair(con, today))
