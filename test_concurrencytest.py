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
        out = StringIO()
        runner = unittest.TextTestRunner(stream=out)
        # Run tests across 2 processes
        concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(2))
        result = runner.run(concurrent_suite)
        return result, out

    def test_run_pass(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(BothPass)
        result, out = self.run_tests(suite)
        self.assertEqual(result.testsRun, suite.countTestCases())
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(result.skipped, [])
        self.assertIn('Ran 2 tests', out.getvalue())
        self.assertIn('OK', out.getvalue())

    def test_run_with_fail(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneFail)
        result, out = self.run_tests(suite)
        self.assertEqual(len(result.failures), 1)
        self.assertIn('FAILED (failures=1)', out.getvalue())

    def test_run_with_error(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneError)
        result, out = self.run_tests(suite)
        self.assertEqual(len(result.errors), 1)
        self.assertIn('Exception: ouch', out.getvalue())
        self.assertIn('FAILED (errors=1)', out.getvalue())

    def test_run_with_skip(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(OneSkip)
        result, out = self.run_tests(suite)
        self.assertEqual(len(result.skipped), 1)
        self.assertIn('OK (skipped=1)', out.getvalue())


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(ForkedTestCase)
    result = runner.run(suite)
    return len(result.errors) + len(result.failures)


if __name__ == '__main__':
    import sys
    sys.exit(main())

