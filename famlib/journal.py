from famlib import dates, events

SESSIONS = ("nightly", "weekly", "capture")
KINDS = ("transcript", "summary")


def add(con, source, session, kind, text, date=None):
    if not text or not text.strip():
        raise SystemExit("journal text must not be empty")
    if session not in SESSIONS:
        raise SystemExit("invalid session: %r (nightly|weekly|capture)" % session)
    if kind not in KINDS:
        raise SystemExit("invalid kind: %r (transcript|summary)" % kind)
    d = date or dates.today()
    dates.parse(d)
    with con:
        cur = con.execute(
            "INSERT INTO journal(date, session, kind, text) VALUES (?,?,?,?)",
            (d, session, kind, text))
        row = events.snapshot(con, "journal", cur.lastrowid)
        events.record(con, source, "journal", cur.lastrowid, "add", None, row)
    return row


def last_session_date(con, session):
    return con.execute(
        "SELECT MAX(date) AS d FROM journal WHERE session=?",
        (session,)).fetchone()["d"]


def list_entries(con, days=None, today=None):
    """All journal entries oldest-first; optionally only the last N days."""
    if days is None:
        rows = con.execute("SELECT * FROM journal ORDER BY date, id")
    else:
        cutoff = dates.add_days(today or dates.today(), -days)
        rows = con.execute(
            "SELECT * FROM journal WHERE date >= ? ORDER BY date, id",
            (cutoff,))
    return [dict(r) for r in rows]


def search(con, term):
    """FTS5 search over journal text. Term is treated as plain words."""
    words = [w for w in term.replace('"', " ").split() if w]
    if not words:
        return []
    q = " ".join('"%s"' % w for w in words)
    return [dict(r) for r in con.execute(
        "SELECT j.* FROM journal_fts f JOIN journal j ON f.rowid = j.id"
        " WHERE journal_fts MATCH ? ORDER BY j.date, j.id", (q,))]
