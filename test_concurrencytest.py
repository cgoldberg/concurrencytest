#!/usr/bin/env python3
#
# Test suite for concurrencytest
#
# Corey Goldberg, 2013-2026
#   License: GPLv2+

import importlib
import os
import re
import sys
import unittest
from io import StringIO
from unittest.mock import patch

from testtools import iterate_tests

from concurrencytest import ConcurrentTestSuite, fork_for_tests, partition_tests

# Dummy test classses used by internal tests. Not to be run on their own.
# -----------------------------------------------------------------------


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


class WorkerCheck(unittest.TestCase):
    def test_worker_id(self):
        worker_id = os.environ.get("TEST_WORKER_ID")
        self.assertIsNotNone(worker_id)


# End of dummy test classes
# ------------------------------------------------------------------------


class ForkingWorkersTestCase(unittest.TestCase):
    def run_tests(self, suite, num_processes=None):
        """Run a suite using ConcurrentTestSuite with specified number of processes.

        If a number is given for `num_processes`, run tests across N processes.
        Otherwise, use default concurrency (one process per available CPU core).
        """
        runner = unittest.TextTestRunner(stream=StringIO())
        if num_processes:
            concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(num_processes))
        else:
            concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests())
        result = runner.run(concurrent_suite)
        self.assertEqual(result.testsRun, suite.countTestCases())
        return result

    def test_run_all_pass(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(BothPass)
        result = self.run_tests(suite, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_error(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneError)
        result = self.run_tests(suite, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_fail(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneFail)
        result = self.run_tests(suite, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_skip(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneSkip)
        result = self.run_tests(suite, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 1)

    def test_run_default_concurrency(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(BothPass)
        # Run 1 process per CPU corec
        result = self.run_tests(suite)
        self.assertEqual(result.testsRun, 2)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_worker_id_env_var_is_assigned(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(WorkerCheck)
        result = self.run_tests(suite)
        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)


class PartitionTestCase(unittest.TestCase):
    def setUp(self):
        self.suite = unittest.TestSuite(
            [
                unittest.TestLoader().loadTestsFromTestCase(BothPass),
                unittest.TestLoader().loadTestsFromTestCase(OneError),
                unittest.TestLoader().loadTestsFromTestCase(OneFail),
                unittest.TestLoader().loadTestsFromTestCase(OneSkip),
            ]
        )

    def test_num_tests(self):
        num_tests = len(list(iterate_tests(self.suite)))
        self.assertEqual(num_tests, 8)

    def test_partition_even_groups(self):
        parted_tests = partition_tests(self.suite, 4)
        self.assertEqual(len(parted_tests), 4)
        self.assertEqual(len(parted_tests[0]), 2)
        self.assertEqual(len(parted_tests[1]), 2)

    def test_partition_one_in_each(self):
        parted_tests = partition_tests(self.suite, 8)
        self.assertEqual(len(parted_tests), 8)
        self.assertEqual(len(parted_tests[0]), 1)

    def test_partition_all_in_one(self):
        parted_tests = partition_tests(self.suite, 1)
        self.assertEqual(len(parted_tests), 1)
        self.assertEqual(len(parted_tests[0]), 8)


class ForkForTestsTestCase(unittest.TestCase):
    def test_fork_for_tests_returns_function(self):
        worker_func = fork_for_tests()
        self.assertTrue(callable(worker_func))

    def test_fork_for_tests_returns_function_when_num_procs_passed(self):
        worker_func = fork_for_tests(4)
        self.assertTrue(callable(worker_func))

    def test_fork_for_tests_creates_expected_workers(self):
        num_processes = 4
        worker_func = fork_for_tests(num_processes)
        workers = list(worker_func(unittest.TestSuite()))
        self.assertEqual(len(workers), num_processes)


@patch("platform.system", return_value="Windows")
class InvalidPlatformTestCase(unittest.TestCase):
    def test_import_exception_on_windows(self, _):
        message = (
            "concurrencytest is not supported on Windows. "
            "It requires `os.fork()` which only works on Unix-like systems."
        )
        sys.modules.pop("concurrencytest", None)
        with self.assertRaisesRegex(OSError, re.escape(message)):
            importlib.import_module("concurrencytest")


class SimpleTextTestResult(unittest.TextTestResult):
    def getDescription(self, test):
        return str(test._testMethodName)


def main():
    runner = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=2, resultclass=SimpleTextTestResult
    )
    suite = unittest.TestSuite(
        (
            unittest.TestLoader().loadTestsFromTestCase(ForkingWorkersTestCase),
            unittest.TestLoader().loadTestsFromTestCase(PartitionTestCase),
            unittest.TestLoader().loadTestsFromTestCase(ForkForTestsTestCase),
            unittest.TestLoader().loadTestsFromTestCase(InvalidPlatformTestCase),
        )
    )
    result = runner.run(suite)
    return len(result.errors) + len(result.failures)


if __name__ == "__main__":
    sys.exit(main())
