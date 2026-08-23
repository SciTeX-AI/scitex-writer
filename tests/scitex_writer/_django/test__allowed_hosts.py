#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Test file for: src/scitex_writer/_django/_server.py (ALLOWED_HOSTS contribution)

"""Binding an address must permit it, and must not permit anything else.

Why this file exists: ALLOWED_HOSTS was a hardcoded loopback list, so
`serve --host <non-loopback>` started cleanly, printed a correct-looking URL,
and then answered 400 Bad Request to every caller. Nothing in the banner was
wrong, which is why it read as a firewall problem rather than a bug. Reported
by scitex-scholar 2026-08-23, who found the identical list in figrecipe,
storage and scholar -- a shared ancestor in the scitex-app SDK.

The pairing matters more than either half: the fix must open the bound address
AND leave everything else shut. Writer ships no authentication, so a wildcard
would turn every reachable address into an unauthenticated reader.
"""

import os

import pytest

from scitex_writer._django._server import (
    contribute_allowed_host,
    warn_if_wildcard_bind,
)

_ENV = "SCITEX_WRITER_ALLOWED_HOSTS"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)


def test_bound_host_becomes_allowed():
    # Arrange / Act
    allowed = contribute_allowed_host("writer.example.test")
    # Assert
    assert "writer.example.test" in allowed


def test_bound_host_is_exported_for_settings_to_read():
    """settings.py reads the env var, so contributing to the list is not
    enough -- it has to reach the environment before Django imports."""
    # Arrange / Act
    contribute_allowed_host("writer.example.test")
    # Assert
    assert "writer.example.test" in os.environ[_ENV].split(",")


def test_operator_entries_are_kept(monkeypatch):
    """Appended, never assigned: a value the operator set must survive."""
    # Arrange
    monkeypatch.setenv(_ENV, "proxy.example.test")
    # Act
    allowed = contribute_allowed_host("writer.example.test")
    # Assert
    assert allowed == ["proxy.example.test", "writer.example.test"]


def test_nothing_else_is_permitted():
    """The negative half. A fix that opened everything would pass every test
    above and be far worse than the defect it replaced."""
    # Arrange / Act
    allowed = contribute_allowed_host("writer.example.test")
    # Assert
    assert "*" not in allowed


def test_repeated_bind_does_not_duplicate():
    # Arrange
    contribute_allowed_host("writer.example.test")
    # Act
    allowed = contribute_allowed_host("writer.example.test")
    # Assert
    assert allowed.count("writer.example.test") == 1


def test_wildcard_bind_with_no_named_host_warns():
    """0.0.0.0 names no host, so bind-implies-permission cannot resolve it."""
    # Arrange
    allowed = contribute_allowed_host("0.0.0.0")
    # Act
    warning = warn_if_wildcard_bind("0.0.0.0", allowed)
    # Assert
    assert warning is not None


def test_wildcard_warning_names_the_remedy():
    """An error that only states what broke is half-written."""
    # Arrange
    allowed = contribute_allowed_host("0.0.0.0")
    # Act
    warning = warn_if_wildcard_bind("0.0.0.0", allowed)
    # Assert
    assert _ENV in warning


def test_wildcard_bind_with_a_named_host_is_silent(monkeypatch):
    """Positive control: the warning must be able to NOT fire, or it is noise
    that trains people to ignore it."""
    # Arrange
    monkeypatch.setenv(_ENV, "writer.example.test")
    allowed = contribute_allowed_host("0.0.0.0")
    # Act
    warning = warn_if_wildcard_bind("0.0.0.0", allowed)
    # Assert
    assert warning is None


def test_loopback_bind_does_not_warn():
    # Arrange
    allowed = contribute_allowed_host("127.0.0.1")
    # Act
    warning = warn_if_wildcard_bind("127.0.0.1", allowed)
    # Assert
    assert warning is None


# EOF
