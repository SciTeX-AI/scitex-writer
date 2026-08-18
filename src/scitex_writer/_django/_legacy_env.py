#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_writer/_django/_legacy_env.py

"""Refuse to silently ignore the retired unprefixed env-var spellings.

The fleet convention is ``SCITEX_WRITER_<X>``. Two variables were once read
under a bare ``WRITER_<X>`` name as well, "for one deprecation cycle" — a
promise recorded only in a source comment, never in the CHANGELOG, so nobody
outside this file was ever told the clock had started. The fallbacks are gone
now (scitex-dev §6a rates the bare prefix an error), and the CHANGELOG says so.

What must NOT happen is the quiet version of that removal. Someone whose
launcher exports ``WRITER_WORKING_DIR`` would, after a plain deletion, get a
writer that starts fine and simply ignores the directory they asked for — a
setting accepted and discarded, which is the worst of the three possible
behaviours. So the names are still *recognised*; they are just no longer
*honoured*. Setting one and not its replacement is an error that names the
replacement.

This module holds no policy of its own. It exists so the check lives in one
place instead of at each of the three sites that used to read these.
"""

from __future__ import annotations

import os
from typing import Dict, List

__all__ = ["RETIRED_ENV_ALIASES", "legacy_env_complaint", "raise_on_legacy_env"]

RETIRED_ENV_ALIASES: Dict[str, str] = {
    "WRITER_WORKING_DIR": "SCITEX_WRITER_WORKING_DIR",
    "WRITER_DJANGO_SECRET": "SCITEX_WRITER_DJANGO_SECRET",
}
"""Retired spelling -> the name that replaced it."""


def legacy_env_complaint(environ) -> str:
    """The complaint for ``environ``, or ``""`` when there is nothing to say.

    A retired name is only a problem when its replacement is ABSENT. Exporting
    both is what a careful migration looks like mid-flight, and failing that
    case would punish exactly the people who did the right thing.

    Pure so it can be tested against real dicts rather than a patched process
    environment.

    Parameters
    ----------
    environ : Mapping[str, str]
        The environment to inspect.

    Returns
    -------
    str
        A multi-line complaint naming each offending variable and its
        replacement, or an empty string when the environment is clean.

    Examples
    --------
    >>> legacy_env_complaint({})
    ''
    >>> legacy_env_complaint({"SCITEX_WRITER_WORKING_DIR": "/tmp/p"})
    ''
    >>> "SCITEX_WRITER_WORKING_DIR" in legacy_env_complaint(
    ...     {"WRITER_WORKING_DIR": "/tmp/p"})
    True
    """
    stranded: List[str] = [
        f"  {old} is set but {new} is not — rename it to {new}"
        for old, new in RETIRED_ENV_ALIASES.items()
        if old in environ and new not in environ
    ]
    if not stranded:
        return ""
    return (
        "Retired environment variable(s) set, and they are no longer read:\n"
        + "\n".join(stranded)
        + "\n"
        "The fleet convention is SCITEX_WRITER_<X>. Writer stopped honouring "
        "the unprefixed spellings rather than accepting a setting and "
        "discarding it, which would have looked like the value never took "
        "effect. Export the prefixed name (both may be set during a "
        "migration) and re-run."
    )


def raise_on_legacy_env(environ=None) -> None:
    """Fail loudly when a retired spelling is stranded without its replacement.

    Parameters
    ----------
    environ : Mapping[str, str], optional
        Defaults to ``os.environ``.

    Raises
    ------
    RuntimeError
        With the text from :func:`legacy_env_complaint`.
    """
    complaint = legacy_env_complaint(os.environ if environ is None else environ)
    if complaint:
        raise RuntimeError(complaint)


# EOF
