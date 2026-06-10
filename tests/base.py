import os
import tempfile
import unittest


class FamTest(unittest.TestCase):
    """Every test gets a throwaway FAM_HOME so real data is never touched."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["FAM_HOME"] = self.tmp.name
        self.addCleanup(lambda: os.environ.pop("FAM_HOME", None))
        from famlib import db
        self.con = db.connect()
        self.addCleanup(self.con.close)
