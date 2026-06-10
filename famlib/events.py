import json
import sqlite3
from datetime import datetime, timezone

from famlib import db

# Allowlist: events.entity must be one of these table names.
TABLES = ["people", "todos", "calendar", "standing", "weeks", "week_entries",
          "chore_memory", "pulses", "journal", "observations", "time_log",
          "daily_habits", "daily_log"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot(con, table, rowid):
    assert table in TABLES, table
    r = con.execute("SELECT * FROM %s WHERE id=?" % table, (rowid,)).fetchone()
    return dict(r) if r else None


def record(con, source, entity, entity_id, action, before, after):
    assert entity in TABLES, entity
    con.execute(
        "INSERT INTO events(ts, source, entity, entity_id, action, before, after)"
        " VALUES (?,?,?,?,?,?,?)",
        (now(), source, entity, entity_id, action,
         json.dumps(before) if before is not None else None,
         json.dumps(after) if after is not None else None))


def _restore(con, entity, entity_id, state):
    assert entity in TABLES, entity
    if state is None:
        con.execute("DELETE FROM %s WHERE id=?" % entity, (entity_id,))
    else:
        cols = ",".join(state)
        ph = ",".join("?" * len(state))
        con.execute("INSERT OR REPLACE INTO %s(%s) VALUES (%s)" % (entity, cols, ph),
                    tuple(state.values()))


def undo(con, count=1):
    """Reverse the latest <count> events via compensating events. Returns them."""
    undone = []
    for _ in range(count):
        ev = con.execute(
            "SELECT * FROM events WHERE undone=0 AND action!='undo'"
            " ORDER BY id DESC LIMIT 1").fetchone()
        if ev is None:
            break
        before = json.loads(ev["before"]) if ev["before"] else None
        # NOTE: undo() owns its transaction — never call it inside `with con:`
        # (sqlite3's context manager doesn't nest; it would commit the outer tx).
        with con:
            current = snapshot(con, ev["entity"], ev["entity_id"])
            _restore(con, ev["entity"], ev["entity_id"], before)
            record(con, "manual", ev["entity"], ev["entity_id"], "undo",
                   current, before)
            con.execute("UPDATE events SET undone=1 WHERE id=?", (ev["id"],))
        undone.append(dict(ev))
    return undone


def check(con):
    """Replay the event log into a fresh DB; return list of drifted tables."""
    mem = sqlite3.connect(":memory:")
    mem.row_factory = sqlite3.Row
    mem.executescript(db.SCHEMA)
    for ev in con.execute("SELECT * FROM events ORDER BY id"):
        after = json.loads(ev["after"]) if ev["after"] else None
        with mem:
            _restore(mem, ev["entity"], ev["entity_id"], after)
    problems = []
    for t in TABLES:
        live = [dict(r) for r in con.execute("SELECT * FROM %s ORDER BY id" % t)]
        replayed = [dict(r) for r in mem.execute("SELECT * FROM %s ORDER BY id" % t)]
        if live != replayed:
            problems.append(t)
    mem.close()
    return problems
