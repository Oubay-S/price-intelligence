"""Repository-layer exceptions.

These are the only things repos raise upward. Routers map them to
HTTP status codes; tests assert against them. They never carry HTTP
context (no status codes, no headers) — the repo layer is HTTP-agnostic.
"""
from __future__ import annotations


class RepositoryError(Exception):
    """Base class for every repository-layer error."""


class DuplicateError(RepositoryError):
    """A unique-constraint violation (e.g. email already registered,
    product already in the user's watchlist)."""


class NotFoundError(RepositoryError):
    """A row the caller expected to exist could not be located."""
