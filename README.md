concurrencytest
===============

![testing goats](https://raw.github.com/cgoldberg/concurrencytest/master/testing-goats.png "testing goats")

### Python testtools extension for running unittest test suites concurrently.

----

- Development: [GitHub](https://github.com/cgoldberg/concurrencytest)
- Download/Install: [PyPI](https://pypi.org/project/concurrencytest)
- License: [GPLv2+](https://raw.githubusercontent.com/cgoldberg/concurrencytest/refs/heads/master/LICENSE)
- Copyright (c) 2013-2026 [Corey Goldberg](https://github.com/cgoldberg)
- Original code from:
  - Bazaar (`bzrlib.tests.__init__.py`, v2.6, copied Jun 01 2013)
  - Copyright (c) 2005-2011 Canonical Ltd

----

## About

`concurrencytest` allows you to parallelize a `unittest` tests across a configurable
number of worker processes. Tests are assigned to worker processes in a round-robin
fashion.

This module provides the `ConcurrentTestSuite` class from `testtools` and the
`fork_for_tests` function (`make_tests` implementation needed to use
`ConcurrentTestSuite`).

You can specify the number of worker process to use when calling `fork_for_tests`, or
use the default concurrecy (1 process per available CPU core).

----

Install from PyPI:
```
pip install concurrencytest
```

----

Requires:

- support for `os.fork()` (Unix-like systems only)
- [testtools](https://pypi.python.org/pypi/testtools) : `pip install testtools`
- [python-subunit](https://pypi.python.org/pypi/python-subunit) : `pip install python-subunit`

----

Example:

```python
import time
import unittest

from concurrencytest import ConcurrentTestSuite, fork_for_tests


class ExampleTestCase(unittest.TestCase):
    """Dummy tests that sleep for demo."""

    def test_me_1(self):
        time.sleep(0.5)

    def test_me_2(self):
        time.sleep(0.5)

    def test_me_3(self):
        time.sleep(0.5)

    def test_me_4(self):
        time.sleep(0.5)


runner = unittest.TextTestRunner()

# Run the tests from above sequentially
suite = unittest.TestLoader().loadTestsFromTestCase(ExampleTestCase)
runner.run(suite)

# Run same tests concurrently across 4 processes
suite = unittest.TestLoader().loadTestsFromTestCase(ExampleTestCase)
concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(4))
runner.run(concurrent_suite)

# Run same tests concurrently using 1 process per available CPU core
suite = unittest.TestLoader().loadTestsFromTestCase(ExampleTestCase)
concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests())
runner.run(concurrent_suite)
```
Output:

```
.....
----------------------------------------------------------------------
Ran 4 tests in 2.002s

OK
....
----------------------------------------------------------------------
Ran 4 tests in 0.510s

OK
....
----------------------------------------------------------------------
Ran 4 tests in 0.507s

OK
```
