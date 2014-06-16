# -*- coding: utf8 -*-
'''
Rollback simplifies code that needs to handle multiple points of failure,
simulating D's scope statement.

Suppose you are writing code to keep three data points in sync, a log file, a
database and a third party service, here is one approach to handle errors:

    with db_transaction:
        db_save()
        webservice()
        log_file()

If the database fails nothing has to be undone, if the webservice or the
logging fails then the transaction is rolled back, so the database is covered,
but, the webservice is not covered if the log_file() fails (if the disk is
full, for instance), you might fix it with:

    with db_transaction:
        db_save()
        webservice()

        try:
            log_file()
        except:
            webservice_rollback()

If for misfortune of the universe you need to sync the new data point you code
might look:

    with db_transaction:
        db_save()
        webservice()

        try:
            fourth()

            try:
                log_file()
            except:
                fourth_rollback()
        except:
            webservice_rollback()

And here is the code with rollback:

    with rollback:
        db_transaction()
        db_save()
        failure(db_rollback)
        success(db_commit)

        webservice()
        failure(webservice_rollback)

        fourth()
        failure(fourth_rollback)

        log_file()

Simpler and more manageable.
'''
from __future__ import print_function

import unittest

from collections import namedtuple
from contextlib import contextmanager
from random import choice

__all__ = (
    'Callback',
    'State',
    'success',
    'failure',
    'callback',
    'rollback',
)
Callback = namedtuple('Callback', ('callback', 'success', 'failure'))


class State(object):
    '''
    State is a context manager responsable to execute the appropriate
    callbacks. State can handle nested contexts.
    '''
    def __init__(self):
        self.stack = [Callback([], [], [])]

    def failure(self, c):
        ''' Register a function to be executed on any failure '''
        self.stack[-1].failure.append(c)

    def success(self, c):
        ''' Register a function to be executed with a success '''
        self.stack[-1].success.append(c)

    def callback(self, c):
        ''' Register a function to be executed unconditionally '''
        self.stack[-1].callback.append(c)

    def __enter__(self):
        self.stack.append(Callback([], [], []))

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type is None:
            for callback in reversed(self.stack[-1].failure):
                callback()
        else:
            for callback in reversed(self.stack[-1].success):
                callback()

        for callback in reversed(self.stack[-1].callback):
            callback()

        self.stack.pop()


_state = State()
success = _state.success
failure = _state.failure
callback = _state.callback
rollback = _state


class RollbackTestCase(unittest.TestCase):
    def setUp(self):
        from decimal import Decimal
        _state = {'success': 0, 'failure': 0, 'callback': 0}

        def success(): _state['success'] += 1
        def failure(): _state['failure'] += 1
        def callback(): _state['callback'] += 1

        self.success = success
        self.failure = failure
        self.callback = callback
        self.result = lambda: (_state['success'], _state['failure'], _state['callback'])

    def test_success(self):
        with rollback:
            success(self.success)

        self.assertEquals(self.result(), (1, 0, 0))

        with self.assertRaises(Exception):
            with rollback:
                success(self.success)
                raise

        self.assertEquals(self.result(), (1, 0, 0))

    def test_failure(self):
        with rollback:
            failure(self.failure)

        self.assertEquals(self.result(), (0, 0, 0))

        with self.assertRaises(Exception):
            with rollback:
                failure(self.failure)
                raise

        self.assertEquals(self.result(), (0, 1, 0))

    def test_callback(self):
        with rollback:
            callback(self.callback)

        self.assertEquals(self.result(), (0, 0, 1))

        with self.assertRaises(Exception):
            with rollback:
                callback(self.callback)
                raise

        self.assertEquals(self.result(), (0, 0, 2))

    def test_nested(self):
        with rollback:
            success(self.success)
            callback(self.callback)

            with self.assertRaises(Exception):
                with rollback:
                    success(self.success)
                    failure(self.failure)
                    callback(self.callback)
                    raise

            self.assertEquals(self.result(), (0, 1, 1))
            failure(self.failure)

        self.assertEquals(self.result(), (1, 1, 2))

    def test_order(self):
        with rollback:
            failure(self.failure)
            callback(self.callback)
            success(self.success)
            callback(self.callback)
            failure(self.failure)

            self.assertEquals(self.result(), (0, 0, 0), 'the callbacks must not be called before we exit the context manager')

        self.assertEquals(self.result(), (1, 0, 2))

        with self.assertRaises(Exception):
            with rollback:
                callback(self.callback)
                failure(self.failure)

                callback(self.callback)
                success(self.success)

                callback(self.callback)
                failure(self.failure)

                raise

        self.assertEquals(self.result(), (1, 2, 5))


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', default=False, help='flag to run the tests')
    parser.add_argument('--failfast', action='store_true', default=False, help='unittest failfast')
    args = parser.parse_args()

    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(RollbackTestCase)
        result = unittest.TextTestRunner(failfast=args.failfast).run(suite)

        if result.errors or result.failures:
            sys.exit(len(result.errors) + len(result.failures))
