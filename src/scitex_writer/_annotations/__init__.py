#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Writer-owned annotation persist + emit (spike 0).

Framework-agnostic core of the PDF-annotation → agent-feedback loop.
See ``docs/04_DESIGN_PDF_ANNOTATION_FEEDBACK_LOOP.md``. The Django
handler (``_django/handlers/annotation.py``) is a thin wrapper over
``add_annotation`` / ``list_annotations`` here, so the same logic is
reusable from CLI/MCP later.

Spike 0 (§6.1): POST + GET only, ``kind=text_comment`` only,
``source_ref`` = page-only (no SyncTeX / claim resolution yet).
"""

from __future__ import annotations

from ._emit import default_card_id, emit, render_summary
from ._record import Annotation
from ._service import add_annotation, resolve_source_ref
from ._store import (
    annotation_store_target,
    list_annotations,
    open_annotation_store,
    persist,
)

__all__ = [
    "Annotation",
    "add_annotation",
    "annotation_store_target",
    "default_card_id",
    "emit",
    "list_annotations",
    "open_annotation_store",
    "persist",
    "render_summary",
    "resolve_source_ref",
]
