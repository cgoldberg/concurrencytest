#!/usr/bin/env python3
#
# Copyright (c) 2013-2026 Corey Goldberg (https://github.com/cgoldberg)
#  - License: GPLv2+


"""Test suite for concurrencytest."""

import importlib
import io
import os
import re
import sys
import types
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

from concurrencytest import (
    BothPass,
    ConcurrentTestSuite,
    OneError,
    OneFail,
    OneSkip,
    OneWithSetupTearDownClass,
    TwoWithSetupTearDownClass,
    WorkerCheck,
    fork_for_tests,
    partition_tests,
    partition_tests_by_class,
)


class ConcurrentTestSuiteTest(TestCase):
    def _verify_partition_strategy(self, partition_func=None):
        suite = defaultTestLoader.loadTestsFromTestCase(TestCase)
        if partition_func:
            make_tests = fork_for_tests(2, partition_func)
        else:
            make_tests = fork_for_tests(2)
        concurrent_suite = ConcurrentTestSuite(suite, make_tests)
        closure_vars = {
            name: cell.cell_contents
            for name, cell in zip(
                make_tests.__code__.co_freevars, make_tests.__closure__ or []
            )
        }
        self.assertIs(concurrent_suite._make_tests, make_tests)
        self.assertTrue(callable(concurrent_suite._make_tests))
        self.assertIsInstance(concurrent_suite._make_tests, types.FunctionType)
        func = closure_vars.get("partition_func")
        return func

    def test_partition_default_strategy(self):
        func = self._verify_partition_strategy()
        self.assertIs(func, partition_tests)

    def test_partition_round_robin_strategy(self):
        func = self._verify_partition_strategy(partition_tests)
        self.assertIs(func, partition_tests)

    def test_partition_by_class_strategy(self):
        func = self._verify_partition_strategy(partition_tests_by_class)
        self.assertIs(func, partition_tests_by_class)


class ForkingWorkersTest(TestCase):
    def _run_tests(self, test_classes, num_processes=None, partition_func=None):
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
        make_tests = fork_for_tests(
            num_processes=num_processes, partition_func=partition_func
        )

        if num_processes:
            make_tests = fork_for_tests(partition_func=partition_func)
        else:
            make_tests = fork_for_tests(num_processes, partition_func=partition_func)
        concurrent_suite = ConcurrentTestSuite(suite, make_tests)
        result = runner.run(concurrent_suite)
        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.testsRun, suite.countTestCases())
        return result

    def test_all_tests_run(self):
        test_classes = (
            BothPass,
            OneError,
            OneFail,
            OneSkip,
            OneWithSetupTearDownClass,
            TwoWithSetupTearDownClass,
        )
        self._run_tests(test_classes)

    def test_all_tests_run_with_partition(self):
        test_classes = (
            BothPass,
            OneError,
            OneFail,
            OneSkip,
            OneWithSetupTearDownClass,
            TwoWithSetupTearDownClass,
        )
        self._run_tests(test_classes, partition_tests_by_class)

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

    def test_run_default_concurrency(self):
        # Run 1 process per CPU core
        result = self._run_tests(BothPass)
        self.assertEqual(result.testsRun, 2)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_worker_id_env_var_is_assigned(self):
        result = self._run_tests(WorkerCheck)
        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

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


class SimpleTextTestResult(TextTestResult):
    def getDescription(self, test):
        return str(test._testMethodName)


def main():
    runner = TextTestRunner(
        stream=sys.stdout, verbosity=2, resultclass=SimpleTextTestResult
    )
    suite = TestSuite(
        (
            defaultTestLoader.loadTestsFromTestCase(ForkingWorkersTest),
            defaultTestLoader.loadTestsFromTestCase(ForkForTestsTest),
            defaultTestLoader.loadTestsFromTestCase(PartitionTest),
            defaultTestLoader.loadTestsFromTestCase(PartitionByClassTest),
        )
    )
    result = runner.run(suite)
    return len(result.errors) + len(result.failures)


if __name__ == "__main__":
    sys.exit(main())
