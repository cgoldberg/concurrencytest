"""Tests used internally by `test_concurrencytest.py`.

Not to be run on their own.
"""

import os
import unittest


class BothPass(unittest.TestCase):
    def test_pass_1(self):
        self.assertTrue(True)

    def test_pass_2(self):
        self.assertTrue(True)


class OneError(unittest.TestCase):
    def test_error(self):
        raise Exception("ouch")

    def test_pass(self):
        self.assertTrue(True)


class OneFail(unittest.TestCase):
    def test_fail(self):
        self.assertTrue(False)

    def test_pass(self):
        self.assertTrue(True)


class OneSkip(unittest.TestCase):
    @unittest.skip("skipping")
    def test_skip(self):
        self.assertTrue(True)

    def test_pass(self):
        self.assertTrue(True)


class OneWithSetupTearDownClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_1(self):
        pass


class TwoWithSetupTearDownClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_2(self):
        pass

    def test_3(self):
        pass


class WorkerIDCheck(unittest.TestCase):
    def test_worker_id(self):
        worker_id = os.environ.get("TEST_WORKER_ID")
        self.assertIsNotNone(worker_id)
        self.assertGreaterEqual(int(worker_id), 0)
