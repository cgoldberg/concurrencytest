#!/usr/bin/env python
#
# Corey Goldberg, 2013
#   License: GPLv2+


try:
    from StringIO import StringIO  # Py27
except ImportError:
    from io import StringIO  # Py3

import unittest

from testtools import ConcurrentTestSuite
from concurrencytest import fork_for_tests


class BothPass(unittest.TestCase):
    def test_pass_1(self):
        self.assertTrue(True)

    def test_pass_2(self):
        self.assertTrue(True)


class OneFail(unittest.TestCase):
    def test_fail(self):
        self.assertTrue(False)

    def test_pass(self):
        self.assertTrue(True)


class OneError(unittest.TestCase):
    def test_error(self):
        raise Exception('ouch')

    def test_pass(self):
        self.assertTrue(True)


class OneSkip(unittest.TestCase):
    @unittest.skip('skipping')
    def test_skip(self):
        self.assertTrue(True)

    def test_pass(self):
        self.assertTrue(True)


class ForkedTestCase(unittest.TestCase):

    def run_tests(self, suite):
        runner = unittest.TextTestRunner(stream=StringIO())
        # Run tests across 2 processes
        concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(2))
        result = runner.run(concurrent_suite)
        return result

    def test_run_pass(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(BothPass)
        result = self.run_tests(suite)
        self.assertEqual(result.testsRun, suite.countTestCases())
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(result.skipped, [])

    def test_run_with_fail(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneFail)
        result = self.run_tests(suite)
        self.assertEqual(len(result.failures), 1)

    def test_run_with_error(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneError)
        result = self.run_tests(suite)
        self.assertEqual(len(result.errors), 1)

    def test_run_with_skip(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneSkip)
        result = self.run_tests(suite)
        self.assertEqual(len(result.skipped), 1)


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(ForkedTestCase)
    result = runner.run(suite)
    return len(result.errors) + len(result.failures)


if __name__ == '__main__':
    import sys
    sys.exit(main())
