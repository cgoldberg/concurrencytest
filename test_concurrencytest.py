#!/usr/bin/env python
#
# Corey Goldberg, 2013
#   License: GPLv2+


import unittest

from testtools import ConcurrentTestSuite, try_imports, iterate_tests
from concurrencytest import fork_for_tests, partition_tests


StringIO = try_imports(['StringIO.StringIO', 'io.StringIO'])


class BothPass(unittest.TestCase):
    def test_pass_1(self):
        self.assertTrue(True)

    def test_pass_2(self):
        self.assertTrue(True)


class OneError(unittest.TestCase):
    def test_error(self):
        raise Exception('ouch')

    def test_pass(self):
        self.assertTrue(True)


class OneFail(unittest.TestCase):
    def test_fail(self):
        self.assertTrue(False)

    def test_pass(self):
        self.assertTrue(True)


class OneSkip(unittest.TestCase):
    @unittest.skip('skipping')
    def test_skip(self):
        self.assertTrue(True)

    def test_pass(self):
        self.assertTrue(True)


class ForkingWorkersTestCase(unittest.TestCase):

    def run_tests(self, suite):
        runner = unittest.TextTestRunner(stream=StringIO())
        # Run tests across 2 processes
        concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(2))
        result = runner.run(concurrent_suite)
        self.assertEqual(result.testsRun, suite.countTestCases())
        return result

    def test_run_all_pass(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(BothPass)
        result = self.run_tests(suite)
        self.assertEqual(result.testsRun, suite.countTestCases())
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(result.skipped, [])

    def test_run_with_error(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneError)
        result = self.run_tests(suite)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_fail(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneFail)
        result = self.run_tests(suite)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.skipped), 0)

    def test_run_with_skip(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneSkip)
        result = self.run_tests(suite)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 1)


class PartitionTestCase(unittest.TestCase):

    def setUp(self):
        suite1 = unittest.TestLoader().loadTestsFromTestCase(BothPass)
        suite2 = unittest.TestLoader().loadTestsFromTestCase(OneError)
        suite3 = unittest.TestLoader().loadTestsFromTestCase(OneFail)
        suite4 = unittest.TestLoader().loadTestsFromTestCase(OneSkip)
        self.suite = unittest.TestSuite([suite1, suite2, suite3, suite4])

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


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    suite1 = unittest.TestLoader().loadTestsFromTestCase(ForkingWorkersTestCase)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(PartitionTestCase)
    alltests = unittest.TestSuite([suite1, suite2])
    result = runner.run(alltests)
    return len(result.errors) + len(result.failures)


if __name__ == '__main__':
    import sys
    sys.exit(main())
