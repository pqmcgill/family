import json
import sqlite3

from famlib import events

ROLES = ("adult", "kid", "other")


def add(con, source, alias, role, patterns=None):
    if role not in ROLES:
        raise SystemExit("invalid role: %r (expected adult|kid|other)" % role)
    for term in [alias] + list(patterns or []):
        existing = resolve(con, term)
        if existing is not None:
            raise SystemExit(
                "%r already refers to %s — aliases and patterns must be"
                " unambiguous" % (term, existing["alias"]))
    try:
        with con:
            cur = con.execute(
                "INSERT INTO people(alias, role, patterns) VALUES (?,?,?)",
                (alias, role, json.dumps(patterns or [])))
            row = events.snapshot(con, "people", cur.lastrowid)
            events.record(con, source, "people", cur.lastrowid, "add", None, row)
    except sqlite3.IntegrityError:
        raise SystemExit("person alias already exists: %s" % alias)
    return row


def list_people(con):
    return [dict(r) for r in con.execute("SELECT * FROM people ORDER BY id")]


def resolve(con, term):
    """Match alias or reference pattern, case-insensitive. None if unknown."""
    t = term.strip().lower()
    for r in con.execute("SELECT * FROM people WHERE active=1"):
        if r["alias"].lower() == t:
            return dict(r)
        if t in [p.lower() for p in json.loads(r["patterns"])]:
            return dict(r)
    return None


def get_id(con, term):
    r = resolve(con, term)
    if r is None:
        raise SystemExit(
            "unknown person: %r — add with: fam person add <alias>"
            " --role <adult|kid|other>" % term)
    return r["id"]
