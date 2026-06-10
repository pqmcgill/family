import os
import pathlib
from tests.base import FamTest
from famlib import people


class TestPeople(FamTest):
    def test_add_and_list(self):
        row = people.add(self.con, "manual", "P1", "adult", patterns=["babe"])
        self.assertEqual(row["alias"], "P1")
        self.assertEqual([p["alias"] for p in people.list_people(self.con)], ["P1"])

    def test_add_rejects_bad_role(self):
        with self.assertRaises(SystemExit):
            people.add(self.con, "manual", "P1", "wizard")

    def test_add_rejects_duplicate_alias(self):
        people.add(self.con, "manual", "P1", "adult")
        with self.assertRaises(SystemExit):
            people.add(self.con, "manual", "P1", "adult")

    def test_resolve_by_alias_and_pattern(self):
        people.add(self.con, "manual", "P2", "adult", patterns=["mama", "babe"])
        self.assertEqual(people.resolve(self.con, "p2")["alias"], "P2")
        self.assertEqual(people.resolve(self.con, "Babe")["alias"], "P2")
        self.assertIsNone(people.resolve(self.con, "stranger"))

    def test_get_id_unknown_person_message_suggests_add(self):
        with self.assertRaises(SystemExit) as cm:
            people.get_id(self.con, "stranger")
        self.assertIn("fam person add", str(cm.exception))


    def test_duplicate_pattern_across_people_refused(self):
        people.add(self.con, "manual", "P1", "adult", patterns=["babe"])
        with self.assertRaises(SystemExit) as cm:
            people.add(self.con, "manual", "P2", "adult", patterns=["babe"])
        self.assertIn("P1", str(cm.exception))

    def test_alias_colliding_with_pattern_refused(self):
        people.add(self.con, "manual", "P1", "adult", patterns=["mama"])
        with self.assertRaises(SystemExit):
            people.add(self.con, "manual", "mama", "adult")
