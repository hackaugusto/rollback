Rollback
========

Rollback simplifies code that needs to handle multiple points of failure,
simulating D's scope statement.

Suppose you are writing code to keep three data points in sync, a log file, a
database and a third party service, here is one approach to handle errors:

```python
with db_transaction:
    db_save()
    webservice()
    log_file()
```

If the database fails nothing has to be undone, if the webservice or the
logging fails then the transaction is rolled back, so the database is covered,
but, the webservice is not covered if the `log_file()` fails (if the disk is
full, for instance), you might fix it with:

```python
with db_transaction:
    db_save()
    webservice()

    try:
        log_file()
    except:
        webservice_rollback()
```

If for misfortune of the universe you need to sync the new data point you code
might look:

```python
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
```

And here is the code with rollback:

```python
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
```

Simpler and more manageable.
