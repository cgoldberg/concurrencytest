#!/usr/bin/env python3
#
# Copyright (c) 2013-2026 Corey Goldberg (https://github.com/cgoldberg)
#  - License: GPLv2+

"""Test suite for concurrencytest.

Don't try to discover tests from this file using `python -m unittest` or `pytest`
because it imports other tests that it uses internally. Instead, use the `main()`
entry-point function below that loads the proper test classes. You can just run
this file directly and it will do that.
"""

import importlib
import io
import os
import re
import sys
from unittest import (
    TestCase,
    TestResult,
    TestSuite,
    TextTestResult,
    TextTestRunner,
    defaultTestLoader,
    mock,
)

from testtools import iterate_tests

import concurrencytest_tests
from concurrencytest import (
    ConcurrentTestSuite,
    fork_for_tests,
    partition_tests,
    partition_tests_by_class,
)
from concurrencytest_tests import (
    BothPass,
    OneError,
    OneFail,
    OneSkip,
    OneWithSetupTearDownClass,
    TwoWithSetupTearDownClass,
    WorkerIDCheck,
)


class ForkingWorkersTest(TestCase):
    def _run_tests(self, test_classes, num_processes=None):
        """Run one or more test classes concurrently.

        If `num_processes` is given, run tests across N processes. Otherwise, use
        default concurrency (one process per available CPU core).

        If `partition_func` is given, run tests using that partition strategy.
        Otherwise, use default partitioning (round_robin).

        Args:
            test_classes: Single `TestCase` class or iterable of `TestCase` classes.
            num_processes: Number of worker processes.
            partition_func: Callable function (partition strategy for tests).

        Returns:
            Aggregated result from all tests.

        """
        if isinstance(test_classes, type) and issubclass(test_classes, TestCase):
            test_classes = (test_classes,)
        suite = TestSuite(
            [defaultTestLoader.loadTestsFromTestCase(tc) for tc in test_classes]
        )
        runner = TextTestRunner(stream=io.StringIO())
        concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(num_processes))
        result = runner.run(concurrent_suite)
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.testsRun, suite.countTestCases())
        return result

    def test_all_tests_run_with_default_concurrency_and_default_partition(self):
        runner = TextTestRunner(stream=io.StringIO())
        suite = defaultTestLoader.loadTestsFromModule(concurrencytest_tests)
        make_tests = fork_for_tests()
        concurrent_suite = ConcurrentTestSuite(suite, make_tests)
        result = runner.run(concurrent_suite)
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.testsRun, suite.countTestCases())

    def test_all_tests_run_with_specified_workers_and_default_partition(self):
        runner = TextTestRunner(stream=io.StringIO())
        suite = defaultTestLoader.loadTestsFromModule(concurrencytest_tests)
        make_tests = fork_for_tests()
        concurrent_suite = ConcurrentTestSuite(suite, make_tests)
        result = runner.run(concurrent_suite)
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.testsRun, suite.countTestCases())

    def test_all_tests_run_with_default_concurrency_and_partition_by_class(self):
        runner = TextTestRunner(stream=io.StringIO())
        suite = defaultTestLoader.loadTestsFromModule(concurrencytest_tests)
        make_tests = fork_for_tests(partition_func=partition_tests_by_class)
        concurrent_suite = ConcurrentTestSuite(suite, make_tests)
        result = runner.run(concurrent_suite)
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.testsRun, suite.countTestCases())

    def test_all_tests_run_with_specified_workers_and_partition_by_class(self):
        runner = TextTestRunner(stream=io.StringIO())
        suite = defaultTestLoader.loadTestsFromModule(concurrencytest_tests)
        make_tests = fork_for_tests(2, partition_tests_by_class)
        concurrent_suite = ConcurrentTestSuite(suite, make_tests)
        result = runner.run(concurrent_suite)
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.testsRun, suite.countTestCases())

    def test_run_all_pass(self):
        result = self._run_tests(BothPass, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_error(self):
        result = self._run_tests(OneError, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_fail(self):
        result = self._run_tests(OneFail, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_skip(self):
        result = self._run_tests(OneSkip, 2)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 1)

    def test_worker_id_env_var_is_assigned(self):
        result = self._run_tests(WorkerIDCheck)
        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.wasSuccessful())

    def test_import_exception_on_platform_without_fork(self):
        message = (
            "concurrencytest requires os.fork(), "
            "which is only available on Unix-like systems."
        )
        sys.modules.pop("concurrencytest", None)
        # Simulate running on a platform without fork support
        with mock.patch.object(os, "fork", new=None):
            with self.assertRaisesRegex(OSError, re.escape(message)):
                importlib.import_module("concurrencytest")
        # Restore concurrencytest so other tests can use it
        sys.modules.pop("concurrencytest", None)
        importlib.import_module("concurrencytest")


class ForkForTestsTest(TestCase):
    def test_fork_for_tests_returns_function(self):
        worker_func = fork_for_tests()
        self.assertTrue(callable(worker_func))

    def test_fork_for_tests_returns_function_when_num_procs_passed(self):
        worker_func = fork_for_tests(4)
        self.assertTrue(callable(worker_func))

    def test_fork_for_tests_creates_expected_workers(self):
        num_processes = 4
        worker_func = fork_for_tests(num_processes)
        workers = list(worker_func(TestSuite()))
        self.assertEqual(len(workers), num_processes)


class PartitionTest(TestCase):
    def setUp(self):
        self.suite = TestSuite(
            [
                defaultTestLoader.loadTestsFromTestCase(BothPass),
                defaultTestLoader.loadTestsFromTestCase(OneError),
                defaultTestLoader.loadTestsFromTestCase(OneFail),
                defaultTestLoader.loadTestsFromTestCase(OneSkip),
            ]
        )

    def _verify_partitions_have_tests(self, partitions):
        self.assertTrue(
            all(isinstance(t, TestCase) for part in partitions for t in part)
        )

    def test_num_tests(self):
        num_tests = len(list(iterate_tests(self.suite)))
        self.assertEqual(num_tests, 8)

    def test_partition_even_groups(self):
        parted_tests = partition_tests(self.suite, 4)
        self.assertEqual(len(parted_tests), 4)
        self.assertTrue(all(len(part) == 2 for part in parted_tests))
        self._verify_partitions_have_tests(parted_tests)

    def test_partition_one_in_each(self):
        parted_tests = partition_tests(self.suite, 8)
        self.assertEqual(len(parted_tests), 8)
        self.assertTrue(all(len(part) == 1 for part in parted_tests))
        self._verify_partitions_have_tests(parted_tests)

    def test_partition_all_in_one(self):
        parted_tests = partition_tests(self.suite, 1)
        self.assertEqual(len(parted_tests), 1)
        self.assertTrue(all(len(part) == 8 for part in parted_tests))
        self._verify_partitions_have_tests(parted_tests)


class PartitionByClassTest(TestCase):
    def setUp(self):
        self.suite = TestSuite(
            [
                defaultTestLoader.loadTestsFromTestCase(OneWithSetupTearDownClass),
                defaultTestLoader.loadTestsFromTestCase(TwoWithSetupTearDownClass),
            ]
        )

    def _verify_partitions_have_tests(self, partitions):
        self.assertTrue(
            all(isinstance(t, TestCase) for part in partitions for t in part)
        )

    def test_num_tests(self):
        num_tests = len(list(iterate_tests(self.suite)))
        self.assertEqual(num_tests, 3)

    def test_partition_by_class_one_class_in_each(self):
        parted_tests = partition_tests_by_class(self.suite, 2)
        self.assertEqual(len(parted_tests), 2)
        self.assertEqual(len(parted_tests[0]), 1)
        self.assertEqual(len(parted_tests[1]), 2)
        self.assertEqual(len({type(test) for test in parted_tests[0]}), 1)
        self.assertEqual(len({type(test) for test in parted_tests[1]}), 1)
        self._verify_partitions_have_tests(parted_tests)

    def test_partition_by_class_all_in_one(self):
        parted_tests = partition_tests_by_class(self.suite, 1)
        self.assertEqual(len(parted_tests), 1)
        self.assertEqual(len(parted_tests[0]), 3)
        self.assertEqual(len({type(test) for test in parted_tests[0]}), 2)
        self._verify_partitions_have_tests(parted_tests)


def main():
    """Run the core concurrency and partitioning tests for concurrencytest.

    This function executes the following `TestCase` classes:

    - `ForkingWorkersTest`:
      - verifies that worker processes are correctly forked and tasks are distributed
        and run as expected.
    - `ForkForTestsTest`:
      - verifies forking logic.
    - `PartitionTest`:
      - verifies individual tests are partitioned correctly in groups using default
        round-robin strategy.
    - `PartitionByClassTest`:
      - validates tests are partitioned by class in groups where all tests in each
        `TestCase` class are assigned to the same group.
    """

    class SimpleTextTestResult(TextTestResult):
        def getDescription(self, test):
            return str(test._testMethodName)

    runner = TextTestRunner(
        stream=sys.stdout, verbosity=2, resultclass=SimpleTextTestResult
    )
    suite = TestSuite(
        defaultTestLoader.loadTestsFromTestCase(cls)
        for cls in (
            ForkingWorkersTest,
            ForkForTestsTest,
            PartitionTest,
            PartitionByClassTest,
        )
    )
    result = runner.run(suite)
    return len(result.errors) + len(result.failures)


if __name__ == "__main__":
    sys.exit(main())
