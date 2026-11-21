"""Offline contract retrieval, clause tagging, and grounded answers.

The FastAPI pipeline keeps its own parsing and persistence path. This package is
the part a reviewer can run without Postgres, Redis, or an API key.
"""

from app.engine.pipeline import analyze_document, ask_document

__all__ = ["analyze_document", "ask_document"]
