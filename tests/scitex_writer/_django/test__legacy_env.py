#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_writer/_django/test__legacy_env.py

"""The retired env-var spellings must fail loudly, not be ignored.

Deleting a fallback is easy; deleting it *safely* is the part with a test.
Someone whose launcher still exports ``WRITER_WORKING_DIR`` must not get a
writer that starts cleanly and quietly ignores the directory they asked for.
"""

from __future__ import annotations

import pytest

from scitex_writer._django._legacy_env import (
    RETIRED_ENV_ALIASES,
    legacy_env_complaint,
    raise_on_legacy_env,
)

RETIRED = sorted(RETIRED_ENV_ALIASES)


def test_a_clean_environment_has_no_complaint():
    # Arrange
    environ = {"PATH": "/usr/bin"}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert complaint == ""


@pytest.mark.parametrize("old", RETIRED)
def test_the_prefixed_name_alone_is_clean(old: str):
    # Arrange
    environ = {RETIRED_ENV_ALIASES[old]: "value"}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert complaint == ""


@pytest.mark.parametrize("old", RETIRED)
def test_both_names_set_is_clean(old: str):
    """Exporting both is a migration in flight — do not punish it."""
    # Arrange
    environ = {old: "value", RETIRED_ENV_ALIASES[old]: "value"}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert complaint == ""


@pytest.mark.parametrize("old", RETIRED)
def test_a_stranded_retired_name_produces_a_complaint(old: str):
    # Arrange
    environ = {old: "value"}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert complaint != ""


@pytest.mark.parametrize("old", RETIRED)
def test_the_complaint_names_the_offending_variable(old: str):
    # Arrange
    environ = {old: "value"}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert old in complaint


@pytest.mark.parametrize("old", RETIRED)
def test_the_complaint_names_the_replacement(old: str):
    """An error that only says what broke is half-written."""
    # Arrange
    environ = {old: "value"}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert RETIRED_ENV_ALIASES[old] in complaint


def test_one_complaint_covers_every_stranded_variable():
    # Arrange
    environ = {old: "value" for old in RETIRED}
    # Act
    complaint = legacy_env_complaint(environ)
    # Assert
    assert all(old in complaint for old in RETIRED)


def test_raise_on_legacy_env_is_silent_on_a_clean_environment():
    # Arrange
    environ: dict = {}
    # Act
    result = raise_on_legacy_env(environ)
    # Assert
    assert result is None


def test_raise_on_legacy_env_raises_on_a_stranded_name():
    # Arrange
    environ = {RETIRED[0]: "value"}

    def _call():
        return raise_on_legacy_env(environ)

    # Act
    raised = pytest.raises(RuntimeError)
    # Assert
    with raised:
        _call()


def test_every_retired_name_maps_to_the_prefixed_convention():
    """The fleet convention is SCITEX_WRITER_<X>; the table must obey it."""
    # Arrange
    replacements = list(RETIRED_ENV_ALIASES.values())
    # Act
    conforming = [name for name in replacements if name.startswith("SCITEX_WRITER_")]
    # Assert
    assert conforming == replacements


# EOF
