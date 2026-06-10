from tests.base import FamTest
from famlib import people, todos


class TestTodos(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")

    def test_add_minimal(self):
        row = todos.add(self.con, "manual", "call plumber", today="2026-06-06")
        self.assertEqual(row["status"], "open")
        self.assertIsNone(row["owner_id"])
        self.assertEqual(row["created"], "2026-06-06")

    def test_add_with_owner_and_due(self):
        row = todos.add(self.con, "manual", "renew passport", owner="P1",
                        due="2026-10-01", today="2026-06-06")
        self.assertEqual(row["due"], "2026-10-01")
        self.assertEqual(row["owner_id"], 1)

    def test_add_unknown_owner_fails(self):
        with self.assertRaises(SystemExit):
            todos.add(self.con, "manual", "x", owner="ghost", today="2026-06-06")

    def test_add_bad_due_fails(self):
        with self.assertRaises(SystemExit):
            todos.add(self.con, "manual", "x", due="soon", today="2026-06-06")

    def test_done_sets_status_and_resolved(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        row = todos.done(self.con, "manual", row["id"], today="2026-06-07")
        self.assertEqual((row["status"], row["resolved"]), ("done", "2026-06-07"))

    def test_done_missing_id_fails(self):
        with self.assertRaises(SystemExit):
            todos.done(self.con, "manual", 999, today="2026-06-06")

    def test_defer_to_date_keeps_open_and_counts(self):
        row = todos.add(self.con, "manual", "x", due="2026-06-10", today="2026-06-06")
        row = todos.defer(self.con, "manual", row["id"], to="2026-06-20")
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["due"], "2026-06-20")
        self.assertEqual(row["defer_count"], 1)

    def test_defer_without_date_parks(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        row = todos.defer(self.con, "manual", row["id"])
        self.assertEqual(row["status"], "deferred")

    def test_list_open_excludes_resolved(self):
        a = todos.add(self.con, "manual", "a", today="2026-06-06")
        todos.add(self.con, "manual", "b", today="2026-06-06")
        todos.done(self.con, "manual", a["id"], today="2026-06-06")
        self.assertEqual([t["title"] for t in todos.list_open(self.con)], ["b"])

    def test_drop_sets_status(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        row = todos.drop(self.con, "manual", row["id"], today="2026-06-07")
        self.assertEqual(row["status"], "dropped")

    def test_terminal_status_transitions_refused(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        todos.done(self.con, "manual", row["id"], today="2026-06-06")
        with self.assertRaises(SystemExit):
            todos.done(self.con, "manual", row["id"], today="2026-06-07")
        with self.assertRaises(SystemExit):
            todos.defer(self.con, "manual", row["id"], to="2026-07-01")

    def test_defer_with_date_reopens_parked(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        todos.defer(self.con, "manual", row["id"])          # park it
        row = todos.defer(self.con, "manual", row["id"], to="2026-07-01")
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["due"], "2026-07-01")
