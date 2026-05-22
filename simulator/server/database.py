"""Compatibility shim for the simulator service.

The simulator no longer connects to ecommerce_db directly. Existing route
signatures still accept a db dependency while the migration is in progress, so
this dependency yields None.
"""
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def get_db():
    yield None
