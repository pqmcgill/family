import argparse
import json
import shutil
import sys
from datetime import datetime

from famlib import (calendar_items, chores, daily, dates, db, events, journal,
                    observations, people, pulses, reports, standing,
                    time_log, todos, weeks)

RITUAL_TEMPLATE = """\
# Our Check-in Ritual

This file is read by /checkin and /weekly and evolves through use.
It is GITIGNORED — personal details are safe here.

## Current shape (loose by design — we'll converge over time)

- Open with whatever most needs attention from `fam checkin`.
- Make sure before closing: week plan progress, new todos/calendar items,
  pulse for each adult.
- Keep it conversational. The system facilitates; we do the work.

## Preferences we've settled on

(none yet — they'll accumulate here)
"""


def echo(entity, row):
    print("WROTE %s #%d: %s" % (entity, row["id"],
                                json.dumps(row, ensure_ascii=False)))


def main(argv=None):
    p = argparse.ArgumentParser(prog="fam",
                                description="family stress management CLI")
    p.add_argument("--source", default="manual",
                   choices=["manual", "nightly", "weekly", "transcript",
                            "capture"])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("backup")
    sub.add_parser("check")
    u = sub.add_parser("undo")
    u.add_argument("--n", type=int, default=1)

    sub.add_parser("checkin")
    sub.add_parser("today")
    sub.add_parser("horizon")
    sub.add_parser("report")
    f = sub.add_parser("fair")
    f.add_argument("--weeks", type=int, default=4)
    rc = sub.add_parser("recall")
    rc.add_argument("term")

    pp = sub.add_parser("person").add_subparsers(dest="sub", required=True)
    pa = pp.add_parser("add")
    pa.add_argument("alias")
    pa.add_argument("--role", required=True)
    pa.add_argument("--pattern", action="append", default=[])
    pp.add_parser("list")

    tp = sub.add_parser("todo").add_subparsers(dest="sub", required=True)
    ta = tp.add_parser("add")
    ta.add_argument("title")
    ta.add_argument("--who")
    ta.add_argument("--due")
    for name in ("done", "drop"):
        x = tp.add_parser(name)
        x.add_argument("id", type=int)
    td = tp.add_parser("defer")
    td.add_argument("id", type=int)
    td.add_argument("--to")
    tp.add_parser("list")

    cp = sub.add_parser("cal").add_subparsers(dest="sub", required=True)
    ca = cp.add_parser("add")
    ca.add_argument("title")
    ca.add_argument("--date", required=True)
    ca.add_argument("--time")
    ca.add_argument("--who")
    for name in ("done", "cancel"):
        x = cp.add_parser(name)
        x.add_argument("id", type=int)
    cp.add_parser("list")

    sp = sub.add_parser("standing").add_subparsers(dest="sub", required=True)
    sa = sp.add_parser("add")
    sa.add_argument("title")
    sa.add_argument("--kind", required=True)
    sa.add_argument("--group", dest="grp")
    sa.add_argument("--who")
    sa.add_argument("--day")
    sa.add_argument("--time")
    for name in ("pause", "resume", "retire"):
        x = sp.add_parser(name)
        x.add_argument("id", type=int)
    sp.add_parser("list")

    wp = sub.add_parser("week").add_subparsers(dest="sub", required=True)
    wn = wp.add_parser("new")
    wn.add_argument("--start")
    wa = wp.add_parser("add")
    wa.add_argument("title")
    wa.add_argument("--kind", required=True)
    wa.add_argument("--who")
    wa.add_argument("--note")
    wa.add_argument("--day")
    wa.add_argument("--todo", type=int,
                    help="link to an open todo; done cascades")
    wa.add_argument("--week-start")
    wd = wp.add_parser("done")
    wd.add_argument("id", type=int)
    wd.add_argument("--date")
    wno = wp.add_parser("note")
    wno.add_argument("id", type=int)
    wno.add_argument("text")
    wdy = wp.add_parser("day")
    wdy.add_argument("id", type=int)
    wdy.add_argument("day")
    wl = wp.add_parser("link")
    wl.add_argument("id", type=int)
    wl.add_argument("todo_id", type=int)
    wst = wp.add_parser("stage")
    wst.add_argument("id", type=int)
    wst.add_argument("stage")
    wst.add_argument("--date")
    ws = wp.add_parser("skip")
    ws.add_argument("id", type=int)
    wsh = wp.add_parser("show")
    wsh.add_argument("--start")

    chp = sub.add_parser("chore").add_subparsers(dest="sub", required=True)
    cc = chp.add_parser("cadence")
    cc.add_argument("name")
    cc.add_argument("days", type=float)
    chp.add_parser("list")

    plp = sub.add_parser("pulse").add_subparsers(dest="sub", required=True)
    pl = plp.add_parser("log")
    pl.add_argument("alias")
    pl.add_argument("rating", type=int)
    pl.add_argument("--note")
    pl.add_argument("--date")
    pll = plp.add_parser("list")
    pll.add_argument("--days", type=int, default=7)

    tmp = sub.add_parser("time").add_subparsers(dest="sub", required=True)
    tml = tmp.add_parser("log")
    tml.add_argument("kind")
    tml.add_argument("who", nargs="?")
    tml.add_argument("--level")
    tml.add_argument("--date")
    tml.add_argument("--note")
    tmll = tmp.add_parser("list")
    tmll.add_argument("--days", type=int, default=14)

    jp = sub.add_parser("journal").add_subparsers(dest="sub", required=True)
    ja = jp.add_parser("add")
    ja.add_argument("--session", required=True)
    ja.add_argument("--kind", required=True)
    ja.add_argument("--text", help="text; omit to read from stdin")
    ja.add_argument("--date")
    jl = jp.add_parser("list")
    jl.add_argument("--days", type=int)

    op = sub.add_parser("obs").add_subparsers(dest="sub", required=True)
    oa = op.add_parser("add")
    oa.add_argument("text")
    oa.add_argument("--date")
    ox = op.add_parser("archive")
    ox.add_argument("id", type=int)
    op.add_parser("list")

    dp = sub.add_parser("daily").add_subparsers(dest="sub", required=True)
    dda = dp.add_parser("add")
    dda.add_argument("name")
    ddl = dp.add_parser("log")
    ddl.add_argument("name")
    ddl.add_argument("--date")
    ddl.add_argument("--note")
    ddr = dp.add_parser("retire")
    ddr.add_argument("name")
    dp.add_parser("list")

    a = p.parse_args(argv)
    src = a.source
    today = dates.today()

    if a.cmd == "init":
        root = db.root()
        (root / "data" / "backups").mkdir(parents=True, exist_ok=True)
        if not (root / "ritual.md").exists():
            (root / "ritual.md").write_text(RITUAL_TEMPLATE)
        db.connect().close()
        print("initialized: data/family.db, ritual.md")
        return 0

    con = db.connect()
    try:
        if a.cmd == "backup":
            dest = (db.root() / "data" / "backups" / ("family-%s.db"
                    % datetime.now().strftime("%Y%m%d-%H%M%S")))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(db.db_path()), str(dest))
            print("backed up to %s" % dest)
        elif a.cmd == "check":
            problems = events.check(con)
            if problems:
                print("DRIFT in tables: %s" % ", ".join(problems))
                return 1
            print("OK — event log replays to current state")
        elif a.cmd == "undo":
            undone = events.undo(con, a.n)
            for ev in undone:
                print("UNDID %s #%s %s" % (ev["entity"], ev["entity_id"],
                                           ev["action"]))
            if not undone:
                print("nothing to undo")
        elif a.cmd == "checkin":
            print(reports.checkin(con, today))
        elif a.cmd == "today":
            print(reports.today_report(con, today))
        elif a.cmd == "horizon":
            print(reports.horizon(con, today))
        elif a.cmd == "report":
            print(reports.report(con, today))
        elif a.cmd == "fair":
            print(reports.fair(con, today, weeks_back=a.weeks))
        elif a.cmd == "recall":
            print(reports.recall(con, a.term))
        elif a.cmd == "person":
            if a.sub == "add":
                echo("people", people.add(con, src, a.alias, a.role,
                                          patterns=a.pattern))
            else:
                for r in people.list_people(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "todo":
            if a.sub == "add":
                echo("todos", todos.add(con, src, a.title, owner=a.who,
                                        due=a.due, today=today))
            elif a.sub == "done":
                echo("todos", todos.done(con, src, a.id, today=today))
            elif a.sub == "drop":
                echo("todos", todos.drop(con, src, a.id, today=today))
            elif a.sub == "defer":
                echo("todos", todos.defer(con, src, a.id, to=a.to))
            else:
                for r in todos.list_open(con) + todos.list_parked(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "cal":
            if a.sub == "add":
                echo("calendar", calendar_items.add(
                    con, src, a.title, date=a.date, time=a.time, who=a.who,
                    today=today))
            elif a.sub == "done":
                echo("calendar", calendar_items.done(con, src, a.id))
            elif a.sub == "cancel":
                echo("calendar", calendar_items.cancel(con, src, a.id))
            else:
                for r in calendar_items.upcoming(con, today, days=None):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "standing":
            if a.sub == "add":
                echo("standing", standing.add(
                    con, src, a.title, kind=a.kind, grp=a.grp, owner=a.who,
                    day=a.day, time=a.time, today=today))
            elif a.sub in ("pause", "retire"):
                status = "paused" if a.sub == "pause" else "retired"
                echo("standing", standing.set_status(con, src, a.id, status))
            elif a.sub == "resume":
                echo("standing", standing.set_status(con, src, a.id, "active"))
            else:
                for r in standing.list_items(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "week":
            if a.sub == "new":
                wid, start = weeks.new_week(con, src, start=a.start,
                                            today=today)
                print("WROTE weeks #%d: week of %s" % (wid, start))
                for e in weeks.entries(con, wid):
                    echo("week_entries", e)
            elif a.sub == "add":
                wk = weeks.week_for(con, a.week_start or today)
                if wk is None:
                    raise SystemExit("no week plan for that date — run:"
                                     " fam week new")
                echo("week_entries", weeks.add_entry(
                    con, src, wk["id"], kind=a.kind, title=a.title,
                    owner=a.who, note=a.note, day=a.day, todo_id=a.todo))
            elif a.sub == "done":
                echo("week_entries", weeks.entry_done(con, src, a.id,
                                                      date=a.date))
            elif a.sub == "skip":
                echo("week_entries", weeks.entry_skip(con, src, a.id))
            elif a.sub == "note":
                echo("week_entries", weeks.set_note(con, src, a.id, a.text))
            elif a.sub == "day":
                echo("week_entries", weeks.set_day(con, src, a.id, a.day))
            elif a.sub == "link":
                echo("week_entries", weeks.set_todo(con, src, a.id,
                                                    a.todo_id))
            elif a.sub == "stage":
                echo("week_entries", weeks.set_stage(con, src, a.id, a.stage,
                                                     date=a.date))
            else:  # show
                wk = weeks.week_for(con, a.start or today)
                if wk is None:
                    print("no week plan for %s" % (a.start or today))
                else:
                    print("week of %s" % wk["start"])
                    for e in weeks.entries(con, wk["id"]):
                        print(json.dumps(e, ensure_ascii=False))
        elif a.cmd == "chore":
            if a.sub == "cadence":
                echo("chore_memory", chores.set_cadence(con, src, a.name,
                                                        a.days))
            else:
                for r in chores.list_all(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "pulse":
            if a.sub == "log":
                echo("pulses", pulses.log(con, src, a.alias, a.rating,
                                          note=a.note, date=a.date))
            else:
                for r in pulses.recent(con, today, days=a.days):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "time":
            if a.sub == "log":
                echo("time_log", time_log.add(con, src, a.kind, who=a.who,
                                              level=a.level, date=a.date,
                                              note=a.note))
            else:
                for r in time_log.recent(con, today, days=a.days):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "journal":
            if a.sub == "add":
                text = a.text if a.text is not None else sys.stdin.read()
                row = journal.add(con, src, session=a.session,
                                  kind=a.kind, text=text, date=a.date)
                echo("journal", row)
            else:  # list
                for r in journal.list_entries(con, days=a.days, today=today):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "obs":
            if a.sub == "add":
                echo("observations", observations.add(con, src, a.text,
                                                      date=a.date))
            elif a.sub == "archive":
                echo("observations", observations.archive(con, src, a.id))
            else:
                for r in observations.list_active(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "daily":
            if a.sub == "add":
                echo("daily_habits", daily.add_habit(con, src, a.name,
                                                     today=today))
            elif a.sub == "log":
                echo("daily_log", daily.log(con, src, a.name, date=a.date,
                                            note=a.note))
            elif a.sub == "retire":
                echo("daily_habits", daily.retire_habit(con, src, a.name))
            else:
                for r in daily.list_habits(con):
                    print(json.dumps(r, ensure_ascii=False))
        return 0
    finally:
        con.close()
