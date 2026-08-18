#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_writer/workspace_layout.py

"""Where things live inside a writer project — the single source of truth.

A writer project has TWO roots and they are not the same directory::

    <project_dir>/                       the project root the user names
    <project_dir>/.scitex/writer/        the writer WORKSPACE

Everything writer owns — ``scripts/``, ``01_manuscript/``, ``config/`` — hangs
off the WORKSPACE. That one hidden segment is the whole content of this module,
and it exists because it was being re-typed.

WHY THIS MODULE EXISTS (measured 2026-08-17, prod). Full compilation was dead
for every user with::

    bash: /workspace/scripts/shell/compile_manuscript.sh: No such file or directory

The script was real; it was at ``/workspace/.scitex/writer/scripts/shell/``.
The caller had spelled the path out by hand because writer published nothing to
import — so writer's layout became a string literal in somebody else's
codebase, and drifted the moment it was written. Publishing the layout is the
fix; a second copy of the string anywhere is the bug.

So: **if you need a path inside a writer project, compose it from here.** Do
not join ``"scripts"`` and ``"shell"`` yourself, in this package or any other.
This module is public (no leading underscore) precisely so downstream packages
— scitex-hub among them — can import it instead of guessing.

NOTHING HERE GUESSES WHICH ROOT YOU HOLD. :func:`workspace_dir` always appends
the segment and :func:`compile_script_relpath` is always relative to the
workspace, so composing them twice by mistake produces an obviously wrong path
rather than a plausible one. An "accepts either root" helper was considered and
rejected: the scitex-writer repository is itself a workspace that ALSO contains
a ``.scitex/writer/`` directory, so no heuristic can tell the two roots apart
from the path alone, and one that appeared to would be wrong exactly where it
was trusted most.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

__all__ = [
    "WORKSPACE_RELPATH",
    "SHELL_SCRIPTS_RELPATH",
    "COMPILE_SCRIPT_RELPATHS",
    "workspace_dir",
    "compile_script_relpath",
]

PathLike = Union[str, Path]

WORKSPACE_RELPATH = Path(".scitex") / "writer"
"""The writer workspace, relative to the project root.

Mirrors what :func:`scitex_writer.ensure_workspace` creates. Hidden by the
dotfile convention, which is exactly why callers forget the segment exists.
"""

SHELL_SCRIPTS_RELPATH = Path("scripts") / "shell"
"""The compile scripts' directory, relative to the WORKSPACE."""

COMPILE_SCRIPT_RELPATHS = {
    doc_type: SHELL_SCRIPTS_RELPATH / f"compile_{doc_type}.sh"
    for doc_type in ("manuscript", "supplementary", "revision")
}
"""doc_type -> compile script, relative to the WORKSPACE.

Derived from one pattern rather than written out three times: three literal
entries are three chances to update two of them.
"""


def workspace_dir(project_dir: PathLike) -> Path:
    """The writer workspace inside a PROJECT ROOT.

    Always appends :data:`WORKSPACE_RELPATH`. Pass a project root; passing a
    workspace gives you a nested path that does not exist, which is the
    intended failure — see the module docstring on why this does not try to
    detect which root it was handed.

    Parameters
    ----------
    project_dir : str or pathlib.Path
        The project root.

    Returns
    -------
    pathlib.Path
        The workspace directory. Not created, and not required to exist.

    Examples
    --------
    >>> workspace_dir("/tmp/paper").as_posix()
    '/tmp/paper/.scitex/writer'
    """
    return Path(project_dir) / WORKSPACE_RELPATH


def compile_script_relpath(doc_type: str) -> Path:
    """The compile script for ``doc_type``, relative to the WORKSPACE.

    Relative on purpose: a caller that already holds the workspace — a
    container bind, a remote path, a URL prefix — needs the tail, not an
    absolute path computed against whichever root this module guessed.

    Parameters
    ----------
    doc_type : str
        One of ``manuscript``, ``supplementary``, ``revision``.

    Returns
    -------
    pathlib.Path
        e.g. ``scripts/shell/compile_manuscript.sh``.

    Raises
    ------
    ValueError
        If ``doc_type`` is not a known document type. Names the valid set,
        because the caller supplying a bad one cannot see this dict.

    Examples
    --------
    >>> compile_script_relpath("manuscript").as_posix()
    'scripts/shell/compile_manuscript.sh'

    An absolute path, from a project root:

    >>> (workspace_dir("/tmp/paper") / compile_script_relpath("manuscript")).as_posix()
    '/tmp/paper/.scitex/writer/scripts/shell/compile_manuscript.sh'
    """
    try:
        return COMPILE_SCRIPT_RELPATHS[doc_type]
    except KeyError:
        raise ValueError(
            f"unknown doc_type {doc_type!r}; "
            f"choose from {sorted(COMPILE_SCRIPT_RELPATHS)}"
        ) from None


# EOF
