import json
from tests.base import FamTest
from famlib import events


def insert_person(con, alias):
    with con:
        cur = con.execute(
            "INSERT INTO people(alias, role) VALUES (?, 'adult')", (alias,))
        row = events.snapshot(con, "people", cur.lastrowid)
        events.record(con, "manual", "people", cur.lastrowid, "add", None, row)
    return cur.lastrowid


class TestEvents(FamTest):
    def test_record_and_snapshot(self):
        pid = insert_person(self.con, "P1")
        ev = self.con.execute("SELECT * FROM events").fetchone()
        self.assertEqual(ev["entity"], "people")
        self.assertEqual(ev["action"], "add")
        self.assertIsNone(ev["before"])
        self.assertEqual(json.loads(ev["after"])["alias"], "P1")
        self.assertEqual(ev["entity_id"], pid)

    def test_undo_insert_deletes_row(self):
        pid = insert_person(self.con, "P1")
        undone = events.undo(self.con)
        self.assertEqual(len(undone), 1)
        self.assertIsNone(events.snapshot(self.con, "people", pid))
        # original event flagged; an 'undo' event was appended
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM events WHERE action='undo'").fetchone()[0], 1)

    def test_undo_update_restores_before(self):
        pid = insert_person(self.con, "P1")
        before = events.snapshot(self.con, "people", pid)
        with self.con:
            self.con.execute("UPDATE people SET role='kid' WHERE id=?", (pid,))
            after = events.snapshot(self.con, "people", pid)
            events.record(self.con, "manual", "people", pid, "edit", before, after)
        events.undo(self.con)
        self.assertEqual(events.snapshot(self.con, "people", pid)["role"], "adult")

    def test_undo_with_nothing_to_undo(self):
        self.assertEqual(events.undo(self.con), [])

    def test_check_clean(self):
        insert_person(self.con, "P1")
        events.undo(self.con)
        insert_person(self.con, "P2")
        self.assertEqual(events.check(self.con), [])

    def test_check_detects_drift(self):
        insert_person(self.con, "P1")
        with self.con:  # sneaky write that bypasses the event log
            self.con.execute("UPDATE people SET role='kid' WHERE alias='P1'")
        self.assertIn("people", events.check(self.con))
