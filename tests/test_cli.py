import io
import os
import pathlib
import contextlib
from tests.base import FamTest
from famlib import cli


def run(*argv):
    """Run the CLI capturing stdout; returns (exit_code, output)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = cli.main(list(argv))
    except SystemExit as e:
        return (e.code if isinstance(e.code, int) else 1), buf.getvalue()
    return code or 0, buf.getvalue()


class TestCli(FamTest):
    def test_init_creates_templates(self):
        code, out = run("init")
        self.assertEqual(code, 0)
        home = pathlib.Path(os.environ["FAM_HOME"])
        self.assertFalse((home / "private" / "names.txt").exists())
        self.assertTrue((home / "ritual.md").exists())
        self.assertTrue((home / "data" / "backups").is_dir())

    def test_person_add_echoes_wrote(self):
        code, out = run("person", "add", "P1", "--role", "adult",
                        "--pattern", "babe")
        self.assertEqual(code, 0)
        self.assertIn("WROTE people #1:", out)
        self.assertIn('"alias": "P1"', out)

    def test_todo_lifecycle_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("todo", "add", "call plumber", "--who", "P1",
                        "--due", "2026-07-01")
        self.assertIn("WROTE todos #1:", out)
        code, out = run("todo", "done", "1")
        self.assertIn('"status": "done"', out)

    def test_unknown_person_error_is_loud(self):
        code, out = run("todo", "add", "x", "--who", "ghost")
        self.assertNotEqual(code, 0)

    def test_source_flag_recorded(self):
        run("--source", "nightly", "person", "add", "P1", "--role", "adult")
        ev = self.con.execute("SELECT source FROM events").fetchone()
        self.assertEqual(ev["source"], "nightly")

    def test_checkin_and_horizon_run(self):
        run("person", "add", "P1", "--role", "adult")
        run("todo", "add", "far", "--due", "2027-01-01")
        code, out = run("checkin")
        self.assertEqual(code, 0)
        self.assertIn("OPEN TODOS (1 of 1 shown)", out)
        code, out = run("horizon")
        self.assertIn("far", out)

    def test_week_flow_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        run("standing", "add", "groceries", "--kind", "chore", "--who", "P1")
        code, out = run("week", "new", "--start", "2026-06-01")
        self.assertEqual(code, 0)
        self.assertIn("groceries", out)
        code, out = run("week", "done", "1", "--date", "2026-06-03")
        self.assertIn('"status": "done"', out)

    def test_journal_add_from_arg_and_recall(self):
        code, out = run("journal", "add", "--session", "capture", "--kind",
                        "transcript", "--text", "talked about gutters",
                        "--date", "2026-06-06")
        self.assertIn("WROTE journal #1:", out)
        code, out = run("recall", "gutters")
        self.assertIn("JOURNAL (1 of 1 shown)", out)

    def test_undo_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("undo")
        self.assertEqual(code, 0)
        self.assertIn("UNDID", out)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM people").fetchone()[0], 0)

    def test_check_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("check")
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_backup_creates_copy(self):
        run("init")
        code, out = run("backup")
        self.assertEqual(code, 0)
        home = pathlib.Path(os.environ["FAM_HOME"])
        backups = list((home / "data" / "backups").glob("family-*.db"))
        self.assertEqual(len(backups), 1)

    def test_pulse_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("pulse", "log", "P1", "7", "--note", "ok day",
                        "--date", "2026-06-06")
        self.assertIn("WROTE pulses #1:", out)

    def test_time_log_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("--source", "nightly", "time", "log", "personal",
                        "P1", "--level", "full", "--date", "2026-06-06")
        self.assertEqual(code, 0)
        self.assertIn("WROTE time_log #1:", out)
        self.assertIn('"level": "full"', out)
        code, out = run("time", "log", "family", "--date", "2026-06-06")
        self.assertIn("WROTE time_log #2:", out)
        code, out = run("time", "list")
        self.assertIn('"kind": "family"', out)

    def test_time_log_couple_with_alias_is_loud(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("time", "log", "couple", "P1")
        self.assertNotEqual(code, 0)

    def test_week_note_via_cli(self):
        run("week", "new", "--start", "2026-06-08")
        code, out = run("week", "add", "k2 laundry", "--kind", "chore",
                        "--week-start", "2026-06-08")
        code, out = run("week", "note", "1", "wed")
        self.assertEqual(code, 0)
        self.assertIn('"note": "wed"', out)
        code, out = run("week", "show", "--start", "2026-06-08")
        self.assertIn('"note": "wed"', out)

    def test_journal_list_via_cli(self):
        run("journal", "add", "--session", "nightly", "--kind", "summary",
            "--text", "k1 laundry re-drying, put away tomorrow",
            "--date", "2026-06-09")
        code, out = run("journal", "list")
        self.assertEqual(code, 0)
        self.assertIn("put away tomorrow", out)

    def test_week_day_via_cli(self):
        run("week", "new", "--start", "2026-06-08")
        run("week", "add", "k2 laundry", "--kind", "chore",
            "--week-start", "2026-06-08", "--day", "wed")
        code, out = run("week", "day", "1", "thu")
        self.assertEqual(code, 0)
        self.assertIn('"day": "thu"', out)

    def test_today_via_cli(self):
        code, out = run("today")
        self.assertEqual(code, 0)
        self.assertIn("TODAY —", out)

    def test_week_add_with_todo_link(self):
        run("todo", "add", "reset attic")
        run("week", "new", "--start", "2026-06-08")
        code, out = run("week", "add", "reset attic", "--kind", "oneoff",
                        "--week-start", "2026-06-08", "--todo", "1")
        self.assertEqual(code, 0)
        self.assertIn('"todo_id": 1', out)
        code, out = run("week", "done", "1", "--date", "2026-06-09")
        self.assertEqual(code, 0)
        code, out = run("todo", "list")
        self.assertNotIn("reset attic", out)  # open list no longer has it

    def test_week_link_via_cli(self):
        run("todo", "add", "reset attic")
        run("week", "new", "--start", "2026-06-08")
        run("week", "add", "reset attic", "--kind", "oneoff",
            "--week-start", "2026-06-08")
        code, out = run("week", "link", "1", "1")
        self.assertEqual(code, 0)
        self.assertIn('"todo_id": 1', out)

    def test_week_stage_via_cli(self):
        run("week", "new", "--start", "2026-06-08")
        run("week", "add", "laundry: k1", "--kind", "chore",
            "--week-start", "2026-06-08")
        code, out = run("week", "stage", "1", "dry", "--date", "2026-06-09")
        self.assertEqual(code, 0)
        self.assertIn('"stage": "dry"', out)
