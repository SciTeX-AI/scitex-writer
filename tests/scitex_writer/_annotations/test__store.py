#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_writer._annotations._store (persist / list on the store).

A REAL store in a throwaway PostgreSQL schema (``pg_schema``), never a mock
and never the live fleet store — see ``tests/conftest.py``. One assert per
test (STX-TQ007); no monkeypatch (PA-306).

The ``db_path`` argument is gone from every call: it named a file, and there
is no file. ``project`` replaces it — it is the store SCOPE, and the two
scoping tests below exist because that scope is the only thing standing
between one manuscript's feedback queue and another's now that a fleet-wide
table has replaced a per-manuscript one.
"""

from __future__ import annotations

from scitex_writer._annotations._record import Annotation
from scitex_writer._annotations._store import list_annotations, persist


def _annotation(text: str = "fix this claim") -> Annotation:
    return Annotation.from_post(
        {"page": 3, "doc_type": "manuscript", "payload": {"text": text}}
    )


def test_persist_then_list_returns_one_row(pg_schema: str):
    # Arrange
    persist(_annotation(), project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj")
    # Assert
    assert len(rows) == 1


def test_persist_round_trips_text_payload(pg_schema: str):
    # Arrange
    persist(_annotation("check figure 2"), project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj")
    # Assert
    assert rows[0]["payload"] == {"text": "check figure 2"}


def test_persist_round_trips_source_ref(pg_schema: str):
    # Arrange
    ann = _annotation()
    ann.source_ref = {"page": 3}
    persist(ann, project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj")
    # Assert
    assert rows[0]["source_ref"] == {"page": 3}


def test_listed_record_omits_the_store_scope(pg_schema: str):
    """Wire shape == stored shape == ``Annotation.to_dict()`` — no ``project``."""
    # Arrange
    persist(_annotation(), project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj")
    # Assert
    assert "project" not in rows[0]


def test_list_annotations_filters_by_status(pg_schema: str):
    # Arrange
    persist(_annotation(), project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj", status="resolved")
    # Assert
    assert rows == []


def test_list_annotations_filters_by_doc_type(pg_schema: str):
    # Arrange
    persist(_annotation(), project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj", doc_type="manuscript")
    # Assert
    assert len(rows) == 1


def test_another_projects_annotation_is_not_returned(pg_schema: str):
    """The scope the per-manuscript file used to provide for free."""
    # Arrange
    persist(_annotation("theirs"), project="/tmp/other")
    persist(_annotation("mine"), project="/tmp/proj")
    # Act
    rows = list_annotations(project="/tmp/proj")
    # Assert
    assert [r["payload"]["text"] for r in rows] == ["mine"]


def test_two_manuscripts_sharing_a_basename_stay_separate(pg_schema: str):
    """``/a/myproj`` and ``/b/myproj`` are two manuscripts, not one."""
    # Arrange
    persist(_annotation("in a"), project="/a/myproj")
    persist(_annotation("in b"), project="/b/myproj")
    # Act
    rows = list_annotations(project="/a/myproj")
    # Assert
    assert [r["payload"]["text"] for r in rows] == ["in a"]


def test_unscoped_listing_returns_every_project(pg_schema: str):
    """An unfiltered read must not lie about what the table holds."""
    # Arrange
    persist(_annotation("theirs"), project="/tmp/other")
    persist(_annotation("mine"), project="/tmp/proj")
    # Act
    rows = list_annotations()
    # Assert
    assert len(rows) == 2
