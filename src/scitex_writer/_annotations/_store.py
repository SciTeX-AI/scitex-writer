#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Annotation persistence, on the shared ``scitex_dev.store`` primitive (§2.3).

There is no writer-owned database layer here and no file on disk. This module
declares a :class:`~scitex_dev.store.Schema` and calls
:class:`~scitex_dev.store.Store` DIRECTLY — the fleet's one storage primitive,
which resolves to the per-host PostgreSQL. A host whose PostgreSQL is
unreachable raises ``StoreTargetError`` naming the target, which is intended:
annotations written to a private local file nobody reads are worse than an
annotation that fails loudly and can be retried.

WHY ``project`` IS PART OF THE IDENTITY
=======================================
The previous persistence was ONE FILE PER MANUSCRIPT, so the file did the
scoping and no code had to: an unfiltered listing meant "this manuscript's
annotations" for free. The store is FLEET-WIDE — every manuscript on every
host shares one ``annotations_rows`` table. Ported without a scope,
``list_annotations()`` would hand one manuscript's annotations to another and
NOTHING would raise; the answers would just quietly become wrong, in the
direction of "there are more annotations than I made", which reads as data
rather than as a bug.

``project`` is therefore the FIRST identity field — a reader asks "whose?"
before it asks "which one?" — and callers pass the manuscript project
DIRECTORY (absolute where they know it), not its basename, because two
manuscripts may share a basename on one machine.

A LISTING IS O(n), STATED RATHER THAN HIDDEN
============================================
``Store`` exposes ``get``/``put``/``rows``, not SQL — no WHERE clause and no
index to lean on — so a filtered listing materialises the table and filters in
Python where the old code pushed a WHERE clause at an index. The WRITE path
stays O(1): one keyed ``put``, never a scan. Annotations are hand-made by an
operator reading a PDF, so the row count is small by construction; if a
dashboard ever polls this, it wants an indexed query and that is a gap in the
primitive, not something to work around here.
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ._record import Annotation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from scitex_dev.store import Row, Schema, Store, StoreTarget

#: The logical store name. ``scitex_dev.store`` renders it as four physical
#: tables (``annotations_rows``, ``_oplog``, ``_identity``, ``_cursor``).
STORE_NAME = "annotations"

#: Every write is attributed to one actor in the oplog.
ACTOR = "scitex-writer"

#: Identity fields, in order: scope first, then the record.
IDENTITY_FIELDS = ("project", "annotation_id")

#: The record fields, in wire order (§2.1). ``project`` is deliberately NOT
#: here: it is the store's scope, not part of the annotation. Wire shape ==
#: stored shape == ``Annotation.to_dict()``, as ``_record`` promises.
RECORD_FIELDS = (
    "annotation_id",
    "doc_type",
    "build_id",
    "page",
    "region",
    "kind",
    "payload",
    "source_ref",
    "author",
    "created_at",
    "status",
)

__all__ = [
    "ACTOR",
    "IDENTITY_FIELDS",
    "RECORD_FIELDS",
    "STORE_NAME",
    "annotation_schema",
    "annotation_store_target",
    "list_annotations",
    "open_annotation_store",
    "persist",
]


def _ident(kind: Any) -> Any:
    from scitex_dev.store import FieldPolicy, FieldRole, MergeRule

    return FieldPolicy(
        kind=kind,
        role=FieldRole.IDENTITY,
        required=True,
        merge=MergeRule.IMMUTABLE,
        indexed=False,
    )


def _fact(kind: Any, *, required: bool = False) -> Any:
    """A field recording what was annotated — IMMUTABLE.

    No merge may rewrite which page an operator marked, what they wrote, or
    when. ``created_at`` in particular ORDERS the listing; a rule that could
    move it would silently reorder the feedback queue.
    """
    from scitex_dev.store import FieldPolicy, FieldRole, MergeRule

    return FieldPolicy(
        kind=kind,
        role=FieldRole.DATA,
        required=required,
        merge=MergeRule.IMMUTABLE,
        indexed=False,
    )


def _moving(kind: Any) -> Any:
    """``status`` is the only field that moves: open -> resolved/…"""
    from scitex_dev.store import FieldPolicy, FieldRole, MergeRule

    return FieldPolicy(
        kind=kind,
        role=FieldRole.DATA,
        required=True,
        merge=MergeRule.LAST_WRITER_WINS,
        indexed=False,
    )


def annotation_schema() -> "Schema":
    """The annotations schema (§2.3).

    Built lazily so importing this module does not import scitex-dev's store
    machinery — the Django handler imports ``_annotations`` on every request
    path, including the ones that never persist.
    """
    from scitex_dev.store import FieldKind, Schema

    return Schema(
        name=STORE_NAME,
        fields={
            "project": _ident(FieldKind.TEXT),
            "annotation_id": _ident(FieldKind.TEXT),
            "doc_type": _fact(FieldKind.TEXT, required=True),
            "build_id": _fact(FieldKind.TEXT),
            "page": _fact(FieldKind.INTEGER, required=True),
            "region": _fact(FieldKind.JSON),
            "kind": _fact(FieldKind.TEXT, required=True),
            "payload": _fact(FieldKind.JSON),
            "source_ref": _fact(FieldKind.JSON),
            "author": _fact(FieldKind.TEXT),
            "created_at": _fact(FieldKind.TEXT, required=True),
            "status": _moving(FieldKind.TEXT),
        },
    )


def annotation_store_target() -> "StoreTarget":
    """Resolve WHERE annotations live. Pure — does not connect."""
    from scitex_dev.store import host_store

    return host_store(pkg="scitex_writer", name=STORE_NAME)


def open_annotation_store() -> "Store":
    """Open the annotations store. RAISES if PostgreSQL is unreachable.

    The caller owns closing it; every verb below opens and closes one per
    call, which mirrors the request-scoped lifetime the Django handler wants.

    MULTI_WRITER because one shared table is written by every host that runs
    a writer server, so the single-owner check would refuse legitimate writes
    from the second host onward.
    """
    from scitex_dev.store import Store, WriterPolicy

    return Store(
        annotation_store_target(),
        annotation_schema(),
        node=socket.gethostname(),
        writer_policy=WriterPolicy.MULTI_WRITER,
        actor=ACTOR,
    )


def _to_record(row: "Row") -> Dict[str, Any]:
    """One stored row as the wire-shaped annotation record (no ``project``)."""
    values = row.values
    return {field: values.get(field) for field in RECORD_FIELDS}


def _sort_key(row: "Row") -> tuple:
    """Listing order, made TOTAL. :func:`list_annotations` reverses it.

    ``created_at`` preserves the old ``ORDER BY created_at DESC``. The hybrid
    logical clock breaks ties, because two hosts can mint the same ISO
    timestamp and wall-clock alone would order them by whichever machine's
    clock ran fast.
    """
    hlc = row.hlc
    return (str(row.values.get("created_at") or ""), hlc.wall_us, hlc.logical, hlc.node)


def persist(annotation: Annotation, *, project: str) -> Dict[str, Any]:
    """Write one annotation into ``project``'s scope; return the record.

    One keyed ``put`` — no whole-table rewrite — so concurrent POSTs from the
    Django server do not contend. ``annotation_id`` is a fresh uuid4, so the
    write is a creation and a repeat of the same id is a
    ``RevisionMismatchError`` rather than a silent overwrite.
    """
    from scitex_dev.store import NEW_RECORD

    record = annotation.to_dict()
    store = open_annotation_store()
    try:
        store.put(
            {"project": str(project), **{f: record.get(f) for f in RECORD_FIELDS}},
            expected_revision=NEW_RECORD,
        )
    finally:
        store.close()
    return record


def list_annotations(
    *,
    project: Optional[str] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    build_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return annotations matching the given predicate, newest first.

    ``project=None`` is UNSCOPED and returns every manuscript's annotations.
    That is deliberate rather than an oversight — an unfiltered read should
    not lie about what the table holds — but no request path uses it: the
    Django handler always names the manuscript it is serving.
    """
    store = open_annotation_store()
    try:
        rows = store.rows()
    finally:
        store.close()

    wanted = {
        "project": str(project) if project is not None else None,
        "doc_type": doc_type or None,
        "status": status or None,
        "build_id": build_id or None,
    }
    matched = [
        row
        for row in rows
        if all(v is None or row.values.get(k) == v for k, v in wanted.items())
    ]
    return [_to_record(row) for row in sorted(matched, key=_sort_key, reverse=True)]
