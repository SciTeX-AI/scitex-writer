#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scitex_writer._annotations._emit (the emit seam).

Both rails are isolated by the SAME throwaway PostgreSQL schema (``pg_schema``
repoints ``SCITEX_STORE_DSN`` and ``SCITEX_CARDS_DB``), because a tmp YAML path
CANNOT isolate the cards rail: ``scitex_cards`` falls back to
``$SCITEX_CARDS_DB`` whenever the explicit store it is handed does not exist,
which is how these tests used to comment on the live fleet board. The rail
itself is OPTIONAL, so the card tests still ``pytest.importorskip``. NO mock of
scitex_cards (STX-NM002). One assert per test (STX-TQ007); no monkeypatch
(PA-306).
"""

from __future__ import annotations

import pytest

from scitex_writer._annotations._emit import default_card_id, emit, render_summary
from scitex_writer._annotations._record import Annotation
from scitex_writer._annotations._store import list_annotations


def _annotation(text: str = "fix this claim") -> Annotation:
    return Annotation.from_post(
        {"page": 3, "doc_type": "manuscript", "payload": {"text": text}}
    )


@pytest.fixture
def seeded_card(seed_card):
    """The owning card, on the throwaway board `pg_schema` points at."""
    return seed_card("writer-annotations-proj", "annotations for proj")


def test_render_summary_includes_text():
    # Arrange
    record = _annotation("rewrite abstract").to_dict()
    # Act
    summary = render_summary(record)
    # Assert
    assert "rewrite abstract" in summary


def test_default_card_id_uses_the_project_basename():
    """The store scope is a path; a card id has to stay human-typeable."""
    # Arrange
    project = "/home/someone/manuscripts/proj"
    # Act
    card_id = default_card_id(project)
    # Assert
    assert card_id == "writer-annotations-proj"


def test_emit_persists_even_when_notify_fails(pg_schema: str, tmp_path):
    # Arrange — no card / no rail → notify fails soft, persist still happens
    empty_store = tmp_path / "empty.yaml"
    # Act
    emit(_annotation(), project="/tmp/missing", store=empty_store)
    # Assert
    assert len(list_annotations(project="/tmp/missing")) == 1


def test_emit_reports_persisted_true(pg_schema: str, tmp_path):
    # Arrange
    empty_store = tmp_path / "empty.yaml"
    # Act
    result = emit(_annotation(), project="/tmp/missing", store=empty_store)
    # Assert
    assert result["persisted"] is True


def test_emit_surfaces_notify_error_when_rail_unavailable(pg_schema: str, tmp_path):
    # Arrange — missing card (or absent rail) is surfaced, never silent
    empty_store = tmp_path / "empty.yaml"
    # Act
    result = emit(_annotation(), project="/tmp/missing", store=empty_store)
    # Assert
    assert result["notify_error"] is not None


def test_emit_reports_notified_true_with_seeded_card(seeded_card: str):
    # Arrange
    project = "/tmp/proj"
    # Act
    result = emit(_annotation(), project=project)
    # Assert
    assert result["notified"] is True


def test_emit_posts_comment_to_owning_card(seeded_card: str):
    # Arrange
    from scitex_cards import get_task

    emit(_annotation("rewrite the abstract"), project="/tmp/proj")
    # Act
    card = get_task(None, seeded_card)
    texts = " ".join(c.get("text", "") for c in card.get("comments", []))
    # Assert
    assert "rewrite the abstract" in texts
