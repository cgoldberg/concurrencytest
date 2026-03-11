# concurrencytest module
#
# Copyright (c) 2013-2026 Corey Goldberg (https://github.com/cgoldberg)
#  - License: GPLv2+
#
# Original code from:
#  - Bazaar (`bzrlib.tests.__init__.py`, v2.6, copied Jun 01 2013)
#  - Copyright (c) 2005-2011 Canonical Ltd
#  - License: GPLv2+


"""Python testtools extension for running unittest test suites concurrently.

The `testtools` project provides a `ConcurrentTestSuite` class, but does
not provide a `make_tests` implementation needed to use it.

This allows you to parallelize a test run across a configurable number
of worker processes. While this can speed up CPU-bound test runs, it is
mainly useful for IO-bound tests that spend most of their time waiting for
data to arrive from someplace else and can benefit from cocncurrency.

Unix-like systems only.
"""

__all__ = [
    "ConcurrentTestSuite",
    "fork_for_tests",
    "partition_tests",
    "partition_tests_by_class",
]


import os
import sys
import traceback
import unittest
from collections.abc import Callable, Iterable
from itertools import cycle
from multiprocessing import cpu_count
from typing import BinaryIO

from subunit import ProtocolTestCase, TestProtocolClient
from subunit.test_results import AutoTimingTestResultDecorator
from testtools import ConcurrentTestSuite, iterate_tests

if not callable(getattr(os, "fork", None)):
    message = (
        "concurrencytest requires os.fork(), "
        "which is only available on Unix-like systems."
    )
    raise OSError(message)


CPU_COUNT = cpu_count()


def fork_for_tests(
    num_processes: int | None = None,
    partition_func: (
        Callable[[unittest.TestSuite, int], list[list[unittest.TestCase]]] | None
    ) = None,
) -> Callable[[unittest.TestSuite], Iterable[ProtocolTestCase]]:
    """Create a test runner that executes tests in multiple forked processes.

    This function returns a callable suitable for use as the `make_tests`
    argument to `testtools.ConcurrentTestSuite`. The returned callable
    partitions a test suite into groups and executes each group in a
    separate worker process using `os.fork()`.

    Args:
        num_processes:
            The number of worker processes to spawn. Defaults to the
            number of CPUs on the system.

        partition_func:
            Function used to partition tests across workers. It receives the
            test suite and the worker count and must return a list of test
            lists (one list per worker). If `None`, the default round-robin
            partition strategy is used.

    Returns:
        Callable function that takes a `TestSuite` and returns an iterable of
        test-like objects compatible with `ConcurrentTestSuite`.

    """
    if num_processes is None:
        num_processes = CPU_COUNT

    if partition_func is None:
        partition_func = partition_tests

    def do_fork(suite: unittest.TestSuite) -> list[ProtocolTestCase]:
        """Take a test suite and start up multiple runners by forking.

        Args:
            suite:
                `TestSuite` object.

        Returns:
            Iterable of TestCase-like objects which can each have `run(result)`
            called on them to feed tests to result.

        """
        result: list[ProtocolTestCase] = []
        test_blocks = partition_func(suite, num_processes)
        # Clear the tests from the original suite so it doesn't keep them alive
        suite._tests.clear()
        for worker_id, process_tests in enumerate(test_blocks):
            process_suite = unittest.TestSuite(process_tests)
            # Also clear each split list so new suite has only reference
            process_tests.clear()
            c2pread, c2pwrite = os.pipe()
            pid = os.fork()
            if pid == 0:
                os.environ["TEST_WORKER_ID"] = str(worker_id)
                try:
                    stream = os.fdopen(c2pwrite, "wb")
                    os.close(c2pread)
                    # Leave stderr and stdout open so we can see test noise
                    # Close stdin so that the child goes away if it decides to
                    # read from stdin (otherwise its a roulette to see what
                    # child actually gets keystrokes for pdb etc).
                    sys.stdin.close()
                    subunit_result = AutoTimingTestResultDecorator(
                        TestProtocolClient(stream)
                    )
                    process_suite.run(subunit_result)
                except Exception:
                    # Try and report traceback on stream, but exit with error
                    # even if stream couldn't be created or something else
                    # goes wrong.  The traceback is formatted to a string and
                    # written in one go to avoid interleaving lines from
                    # multiple failing children.
                    try:
                        stream.write(traceback.format_exc().encode())
                    finally:
                        os._exit(1)
                os._exit(0)
            else:
                os.close(c2pwrite)
                parent_stream: BinaryIO = os.fdopen(c2pread, "rb")
                test = ProtocolTestCase(parent_stream)
                result.append(test)
        return result

    return do_fork


def partition_tests(
    suite: unittest.TestSuite, count: int
) -> list[list[unittest.TestCase]]:
    """Partition a unittest suite into multiple lists of tests, using round-robin.

    This function takes a unittest TestSuite and splits its individual test
    cases into `count` separate lists. Tests are assigned in a round-robin
    fashion to distribute load evenly across workers. This helps avoid
    situations where one worker gets all slow tests while others finish quickly.

    Args:
        suite: `TestSuite` containing all test cases to partition.
        count: Number of partitions.

    Returns:
        List of `count` lists, where each inner list contains the tests assigned to
        that partition. The tests maintain their original order, distributed
        round-robin.

    """
    partitions: list[list[unittest.TestCase]] = [[] for _ in range(count)]
    tests = iterate_tests(suite)
    for partition, test in zip(cycle(partitions), tests):
        partition.append(test)
    return partitions


def partition_tests_by_class(
    suite: unittest.TestSuite, count: int
) -> list[list[unittest.TestCase]]:
    """Partition a unittest suite into multiple lists of tests, keeping class locality.

    This function groups all tests belonging to the same `TestCase` class and assigns
    each class as a block to the worker with the current smallest load. This ensures
    that all tests from a single class run in the same worker, which preserves
    `setUpClass`/`tearDownClass` lifecycle semantics. It also attempts to balance the
    number of tests across workers.

    Args:
        suite: `TestSuite` containing all test cases to partition.
        count: Number of partitions.

    Returns:
        List of `count` lists, where each inner list contains the tests assigned to
        that partition. Each class's tests are contained within a single partition,
        and partitions are balanced by total test count.

    """
    partitions: list[list[unittest.TestCase]] = [[] for _ in range(count)]
    loads: list[int] = [0] * count

    tests_by_class: dict[type, list[unittest.TestCase]] = {}

    for test in iterate_tests(suite):
        tests_by_class.setdefault(type(test), []).append(test)

    for tests in tests_by_class.values():
        idx = min(range(count), key=lambda i: loads[i])
        partitions[idx].extend(tests)
        loads[idx] += len(tests)

    return partitions
