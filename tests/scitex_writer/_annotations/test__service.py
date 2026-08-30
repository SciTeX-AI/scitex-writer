#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_writer._annotations._service (POST orchestration).

A REAL store in a throwaway PostgreSQL schema (``pg_schema``), which also
isolates the cards rail — a tmp YAML path cannot, because ``scitex_cards``
falls back to ``$SCITEX_CARDS_DB`` when the explicit store does not exist. The
rail is optional so the notified-True path ``pytest.importorskip``. No mocks
(STX-NM002); one assert per test (STX-TQ007); no monkeypatch (PA-306).
"""

from __future__ import annotations

import pytest

from scitex_writer._annotations._record import Annotation
from scitex_writer._annotations._service import add_annotation, resolve_source_ref


def _body(text: str = "please clarify") -> dict:
    return {"page": 2, "doc_type": "manuscript", "payload": {"text": text}}


@pytest.fixture
def seeded_card(seed_card):
    """The owning card, on the throwaway board `pg_schema` points at."""
    return seed_card("writer-annotations-proj", "annotations for proj")


def test_resolve_source_ref_is_page_only():
    # Arrange
    ann = Annotation.from_post(_body())
    # Act
    ref = resolve_source_ref(ann)
    # Assert
    assert ref == {"page": 2}


def test_add_annotation_returns_ok(pg_schema: str, tmp_path):
    # Arrange
    empty_store = tmp_path / "empty.yaml"
    # Act
    result = add_annotation(_body(), project="/tmp/proj", store=empty_store)
    # Assert
    assert result["ok"] is True


def test_add_annotation_assigns_annotation_id(pg_schema: str, tmp_path):
    # Arrange
    empty_store = tmp_path / "empty.yaml"
    # Act
    result = add_annotation(_body(), project="/tmp/proj", store=empty_store)
    # Assert
    assert result["annotation_id"]


def test_add_annotation_source_ref_is_page_only(pg_schema: str, tmp_path):
    # Arrange
    empty_store = tmp_path / "empty.yaml"
    # Act
    result = add_annotation(_body(), project="/tmp/proj", store=empty_store)
    # Assert
    assert result["source_ref"] == {"page": 2}


def test_add_annotation_persists_the_row(pg_schema: str, tmp_path):
    # Arrange
    from scitex_writer._annotations._store import list_annotations

    empty_store = tmp_path / "empty.yaml"
    add_annotation(_body(), project="/tmp/proj", store=empty_store)
    # Act
    rows = list_annotations(project="/tmp/proj")
    # Assert
    assert len(rows) == 1


def test_add_annotation_notifies_owning_card(seeded_card: str):
    # Arrange
    project = "/tmp/proj"
    # Act
    result = add_annotation(_body(), project=project)
    # Assert
    assert result["notified"] is True
