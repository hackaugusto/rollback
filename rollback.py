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

from collections import namedtuple
from contextlib import contextmanager
from random import choice


Callback = namedtuple('Callback', ('callback', 'success', 'failure'))


class State(object):
    def __init__(self):
        self.stack = [Callback([], [], [])]

    def failure(self, c):
        self.stack[-1].failure.append(c)

    def success(self, c):
        self.stack[-1].success.append(c)

    def callback(self, c):
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
