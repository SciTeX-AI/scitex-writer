#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal standalone Django settings for `scitex-writer gui`.

Used only by the standalone launcher; cloud deployments ignore this
module and mount `scitex_writer._django.urls` under their own prefix.

Mirrors the `figrecipe._django.settings` pattern: bare-minimum installed
apps, optional `scitex_ui` for the shared workspace shell, and a SQLite
database so any future models (chat sessions, comments, versions) work
out of the box.
"""

from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Fleet env-var convention is SCITEX_WRITER_<X>. The unprefixed spelling is
# retired, not silently dropped -- see ._legacy_env, which turns a stranded
# WRITER_DJANGO_SECRET into an error naming its replacement.
SECRET_KEY = os.environ.get("SCITEX_WRITER_DJANGO_SECRET") or secrets.token_urlsafe(32)
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
# Loopback is always allowed; anything else must be STATED, either by binding to
# it (see _server.run, which contributes its --host) or by naming it here.
#
# THIS USED TO BE A HARDCODED LIST, and the failure it caused is invisible from
# the code: `serve --host <non-loopback>` started cleanly, printed a correct URL,
# and then answered 400 Bad Request to every caller. Nothing in the banner was
# wrong, so it read as a firewall problem. Reported by scitex-scholar 2026-08-23,
# who found the identical list in figrecipe, storage and scholar — a shared
# ancestor in the scitex-app SDK, not four independent mistakes.
#
# NO WILDCARD, DELIBERATELY. Scholar's fix additionally maps DEBUG -> ["*"], which
# they ruled for scholar specifically. DJANGO_DEBUG defaults to "true" directly
# above, and writer ships no authentication of its own, so a DEBUG wildcard here
# would make the permissive branch the DEFAULT branch and every reachable address
# an unauthenticated reader of the operator's manuscripts. scitex-app kept the
# wildcard out of the SDK for the same reason. Changing that is an operator
# decision, not a consistency fix.
_ALLOWED_HOSTS_BASE = ["127.0.0.1", "localhost", "0.0.0.0", "testserver"]
ALLOWED_HOSTS = list(_ALLOWED_HOSTS_BASE)
for _h in os.environ.get("SCITEX_WRITER_ALLOWED_HOSTS", "").split(","):
    _h = _h.strip()
    if _h and _h not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_h)

# "hub" | "standalone" — the browser tab alone must distinguish the two
# (operator request; scitex-hub PR #357 reads the same setting and defaults
# to "hub"). These settings only boot the STANDALONE server
# (`scitex-writer gui`), so standalone is the default here.
SCITEX_APP_MODE = os.environ.get("SCITEX_APP_MODE", "standalone")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "scitex_writer._django.apps.WriterEditorConfig",
]

# Optional: scitex-ui supplies the workspace shell (template + CSS/JS assets)
try:
    import scitex_ui  # noqa: F401

    INSTALLED_APPS.append("scitex_ui")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "scitex_writer._django._standalone_urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                # Enables scitex-ui's element inspector (Alt+I / Ctrl+I) in the
                # standalone editor: sets `stx_element_inspector_enabled` so the
                # shared shell's `_element_inspector.html` partial injects the
                # inspector script (gated on DEBUG/staff, and DEBUG defaults on
                # for the local `scitex-writer gui` server). Without this the
                # partial emits only its placeholder comment and Alt+I/Ctrl+I
                # are no-ops.
                "scitex_ui.context_processors.element_inspector",
            ],
        },
    },
]

# SQLite lives in the temp dir so local runs don't pollute the project
_DB_DIR = Path(tempfile.gettempdir()) / "scitex_writer"
_DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_DB_DIR / "db.sqlite3"),
    }
}

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

WRITER_TEMP_DIR = _DB_DIR
