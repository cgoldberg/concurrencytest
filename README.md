concurrencytest
===============

![testing goats](https://raw.github.com/cgoldberg/concurrencytest/master/testing-goats.png "testing goats")

### Python - Run unittest test suites concurrently

----

- Development: [GitHub](https://github.com/cgoldberg/concurrencytest)
- Download/Install: [PyPI](https://pypi.org/project/concurrencytest)
- License: [GPLv2+](https://raw.githubusercontent.com/cgoldberg/concurrencytest/refs/heads/master/LICENSE)
- Copyright (c) 2013-2026 [Corey Goldberg](https://github.com/cgoldberg)

----

## About

`concurrencytest` allows you to parallelize a `unittest` tests across a
configurable number of worker processes. You can specify a partition strategy
and the number of worker processes to use. By default, tests are distributed
to worker processes in a round-robin fashion using 1 process per available CPU
core.

This module provides:

- `ConcurrentTestSuite` class: unittest-compatible `TestSuite` for running
  parallel tests.
- `fork_for_tests` function: fork-based `make_tests` implementation for use
  with `ConcurrentTestSuite`.
- `partition_tests` function: round-robin partition strategy for test
  distribution to worker processes.
- `partition_tests_by_class`: class-local partition strategy for test
  distribution to worker processes.

For more info about writing/running tests with the `unittest` testing
framework, see the
[official documentation](https://docs.python.org/library/unittest.html).

----

## Installation:

Install from [PyPI](https://pypi.org/project/concurrencytest):

```
pip install concurrencytest
```

----

## Requirements:

- Python 3.10+
- support for `os.fork()` (Unix-like systems only)
- [testtools](https://pypi.python.org/pypi/testtools) : `pip install testtools`
- [python-subunit](https://pypi.python.org/pypi/python-subunit) : `pip install python-subunit`

----

## Usage:

This module provides a `ConcurrentTestSuite` class that is used in place of the
`unittest.TestSuite` class from the standard library.

To use it:

1. write your tests in normal `unittest` style (test methods inside a
   `unittest.TestCase` class)
2. load a suite of tests using `unittest.TestLoader` (or `unittest.defaultTestLoader`):
  - `suite = unittest.TestLoader().discover("tests")`
  - `suite = unittest.TestLoader().loadTestsFromModule(my_tests)`
  - `suite = unittest.TestLoader().loadTestsFromTestCase(MyTests)`
  - `suite = unittest.TestLoader().loadTestsFromName("MyTests.test_1")`
  - `suite = unittest.TestLoader().loadTestsFromNames("MyTests.test_1", "MyTests.test_2")`
3. Instantiate a `ConcurrentTestSuite` with your test suite and (optionally) a
   `make_tests` implementation (partition strategy):
  - `concurrent_suite = ConcurrentTestSuite(suite)`
  - `concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(4))`
4. Run your test suite using a unittest-compatible runner:
  - `unittest.TextTestRunner().run(concurrent_suite)`

Specifying number of processes and partition strategy:

The `concurrencytest` module provides a `make_tests` implementation
(`fork_for_tests`). This allows you to specify the number of worker processes
to use and a partition strategy for defining how tests are distributed to
workers. If `ConcurrentTestSuite` is instantiated without a `make_tests`
argument, it defaults to forking one process per available CPU core, and
distributing tests using the round-robin strategy.

The `fork_for_tests` function is called with positional or keyword arguments
like this:

```
fork_for_tests(num_processes, partition_func)
```

- `num_processes` (optional): Number of worker processes to spawn. Defaults to
  the number of CPUs on the system.
- `partition_func` (optional): Function used to partition tests across workers.
  Defaults to `partition_tests` (round-robin partition strategy).

Available partition functions:

- `partition_tests` (round-robin):

  This is the default strategy.

  This function splits a test suite into its individual test cases and assigns
  them in a round-robin fashion to distribute load evenly across workers. This
  helps avoid situations where one worker gets all slow tests while others
  finish quickly. One potential drawback is that if you have a
  `setUpClass`/`tearDownClass` defined in a `TestCase`, it may be run multiple
  times if tests from the same class are run on different workers.

- `partition_tests_by_class` (class-local):

  This function groups all tests belonging to the same test case class and
  assigns them as a block to the worker with the current smallest number of
  tests already assigned. This ensures that all tests from a single class run
  in the same worker, which preserves `setUpClass`/`tearDownClass` lifecycle
  semantics.

Examples of creating a `ConcurrentTestSuite`:

- default concurrency and round-robin partition strategy:

  `ConcurrentTestSuite(suite)`

- 4 worker processes and round-robin partition strategy:

  `ConcurrentTestSuite(suite, fork_for_tests(4))`

- default concurrency and class-local partition strategy:

  ` ConcurrentTestSuite(suite, fork_for_tests(partition_func=partition_tests_by_class))`

- 4 worker processes and class-local partition strategy:

  `ConcurrentTestSuite(suite, fork_for_tests(4, partition_tests_by_class))`

----

## Examples:


#### Simple example:

```python
import time
import unittest

from concurrencytest import ConcurrentTestSuite

"""Dummy tests that sleep for demo."""


class ExampleTestCase(unittest.TestCase):

    def test_1(self):
        time.sleep(1)

    def test_2(self):
        time.sleep(1)

    def test_3(self):
        time.sleep(1)

    def test_4(self):
        time.sleep(1)


runner = unittest.TextTestRunner()

# Run the tests from above sequentially
suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExampleTestCase)
print("\nrunning sequential (without concurrencytest):")
runner.run(suite)

# Run same tests concurrently across multiple processes
# (1 process per available CPU core)
suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExampleTestCase)
print("\nrunning parallel:")
concurrent_suite = ConcurrentTestSuite(suite)
runner.run(concurrent_suite)
```

Output:

```

running sequential (without concurrencytest):
....
----------------------------------------------------------------------
Ran 4 tests in 4.002s

OK

running parallel:
....
----------------------------------------------------------------------
Ran 4 tests in 1.009s

OK
```

#### Advanced example:

```python
import time
import unittest

from concurrencytest import (
    ConcurrentTestSuite,
    fork_for_tests,
    partition_tests_by_class,
)

"""Dummy tests that sleep for demo."""


class ExampleTestCase1(unittest.TestCase):

    def test_1(self):
        time.sleep(1)

    def test_2(self):
        time.sleep(1)


class ExampleTestCase2(unittest.TestCase):
    """Dummy tests that sleep for demo."""

    def test_3(self):
        time.sleep(1)

    def test_4(self):
        time.sleep(1)


def load_test_suite(*test_cases):
    suite = unittest.TestSuite()
    for cls in test_cases:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    return suite


runner = unittest.TextTestRunner()

# Run the tests from above sequentially
suite = load_test_suite(ExampleTestCase1, ExampleTestCase2)
print("\nrunning sequential (without concurrencytest):")
runner.run(suite)

# Run same tests concurrently across multiple processes
# (1 process per available CPU core)
suite = load_test_suite(ExampleTestCase1, ExampleTestCase2)
concurrent_suite = ConcurrentTestSuite(suite)
print("\nrunning parallel:")
runner.run(concurrent_suite)

# Run same tests concurrently across 4 processes
suite = load_test_suite(ExampleTestCase1, ExampleTestCase2)
concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests(2))
print("\nrunning parallel (2 processes):")
runner.run(concurrent_suite)

# Run same tests concurrently across multiple processes
# (1 process per available CPU core), keeping tests class-local
suite = load_test_suite(ExampleTestCase1, ExampleTestCase2)
concurrent_suite = ConcurrentTestSuite(
    suite, fork_for_tests(partition_func=partition_tests_by_class)
)
print("\nrunning parallel (grouped by class):")
runner.run(concurrent_suite)
```

Output:

```

running sequential (without concurrencytest):
....
----------------------------------------------------------------------
Ran 4 tests in 4.002s

OK

running parallel:
....
----------------------------------------------------------------------
Ran 4 tests in 1.010s

OK

running parallel (2 processes):
....
----------------------------------------------------------------------
Ran 4 tests in 2.006s

OK

running parallel (grouped by class):
....
----------------------------------------------------------------------
Ran 4 tests in 2.008s

OK
```
