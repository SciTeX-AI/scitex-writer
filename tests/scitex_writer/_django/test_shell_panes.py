#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_writer/_django/test_shell_panes.py

"""Writer declares its shell panes through scitex-ui's API, not its DOM.

Writer used to hide the shell's panes with a stylesheet aimed at
``.workspace-three-col > .ws-ai-pane`` and siblings — scitex-ui's PRIVATE class
names. A rename on their side would have broken writer silently, invisible to
both packages. By the time the selectors were deleted two of the five were
already wrong: ``.ws-apps-pane`` is emitted by nothing, and the pane spelled
``.ws-worktree-pane`` is keyed ``files`` in the API.

These tests pin the replacement, and the last one pins the deletion — because a
declaration that lands while the stylesheet survives is two implementations of
one decision, which is the state this change exists to leave.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scitex_writer._django.views import _SHELL_PANES

EDITOR_CSS = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "scitex_writer"
    / "_django"
    / "static"
    / "writer"
    / "css"
    / "editor.css"
)

#: scitex-ui's private class names. Writer must not target any of them.
SHELL_INTERNALS = (
    "workspace-three-col",
    "ws-ai-pane",
    "ws-worktree-pane",
    "ws-viewer-pane",
    "ws-apps-pane",
    "ws-module-pane",
    "mobile-active-pane",
)


def test_writer_declares_every_pane_scitex_ui_offers():
    """Leaving one out would silently leave that pane visible."""
    # Arrange
    from scitex_ui.branding import PANE_NAMES

    # Act
    declared = set(_SHELL_PANES)
    # Assert
    assert declared == set(PANE_NAMES)


@pytest.mark.parametrize("pane", sorted(_SHELL_PANES))
def test_every_declared_pane_is_unused(pane: str):
    """Writer fills only the module pane; hub does not embed this app at all."""
    # Arrange
    expected = "unused"
    # Act
    state = _SHELL_PANES[pane]
    # Assert
    assert state == expected


def test_the_declaration_is_accepted_by_scitex_ui():
    """shell_context raises on an unknown pane name or state — so call it."""
    # Arrange
    from scitex_ui.branding import shell_context

    # Act
    context = shell_context("Writer", panes=_SHELL_PANES)
    # Assert
    assert context["panes"] == _SHELL_PANES


@pytest.mark.parametrize("internal", SHELL_INTERNALS)
def test_writer_css_does_not_target_scitex_ui_internals(internal: str):
    """The stylesheet must not come back in another costume.

    scitex-ui is deleting the legacy ``.workspace-three-col`` architecture
    outright rather than deprecating it, so after their change these names
    cease to exist rather than changing meaning. A selector naming one is dead
    code at best and a silent layout break at worst.
    """
    # Arrange
    css = EDITOR_CSS.read_text(encoding="utf-8")
    # Act
    selectors = [
        line
        for line in css.splitlines()
        if internal in line and not line.lstrip().startswith("*")
    ]
    # Assert
    assert selectors == [], f"editor.css still targets {internal}: {selectors}"


# EOF
