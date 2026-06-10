from tests.base import FamTest
from famlib import observations as obs


class TestObservations(FamTest):
    def test_add_and_list_active(self):
        obs.add(self.con, "nightly", "chores slip on Thursdays",
                date="2026-06-06")
        active = obs.list_active(self.con)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["text"], "chores slip on Thursdays")

    def test_archive_removes_from_active(self):
        row = obs.add(self.con, "nightly", "x", date="2026-06-06")
        obs.archive(self.con, "nightly", row["id"])
        self.assertEqual(obs.list_active(self.con), [])

    def test_archive_missing_fails(self):
        with self.assertRaises(SystemExit):
            obs.archive(self.con, "nightly", 99)

    def test_empty_text_refused(self):
        with self.assertRaises(SystemExit):
            obs.add(self.con, "nightly", "  ", date="2026-06-06")

    def test_double_archive_refused(self):
        row = obs.add(self.con, "nightly", "x", date="2026-06-06")
        obs.archive(self.con, "nightly", row["id"])
        with self.assertRaises(SystemExit):
            obs.archive(self.con, "nightly", row["id"])
