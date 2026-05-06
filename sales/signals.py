# sales/signals.py

"""
Sales notification signals.

Currently, sales due-date notifications are handled by:

    common.management.commands.notify_due_items

This file is intentionally kept clean because these notification types
should NOT be triggered on every save:

- Deal expected close date
- Proposal due date
- Contract end date
- Invoice due date

Those are date reminders, so they belong in a scheduled daily command.

Later, if you want instant notifications such as:
- proposal accepted
- contract signed
- payment received

then add those post_save receivers here.
"""