# container_recipes — Apptainer recipes shipped as package data

Apptainer `.def` recipes for the sub-tool SIFs that `scitex-writer containers
install <target>` builds. `_cli/install.py:_SUB_TOOLS` maps each CLI target to
one filename in this directory.

## Why they live inside the package

Because a user is not a developer with a checkout.

These recipes used to sit at the repository root in `scripts/containers/`, and
`install.py` found them by walking `__file__` up four levels. That arithmetic
describes the *source tree* and nothing else. Installed, the same four hops land
on `.../python3.12/scripts/containers` — and the wheel packages
`src/scitex_writer` only, so the recipes were never in the distribution at any
path. Measured 2026-08-18 against a real pip install:

```
$ scitex-writer containers install texlive --dry-run
Error: recipe not found: /opt/venv-sac/lib/python3.12/scripts/containers/texlive.def
```

The verb was dead for everyone without a checkout and perfect for everyone with
one — which is also why no test caught it: CI installs with `pip install -e .`,
so the tests resolved the source tree and passed. A gate that cannot fail.

Package data is what makes the installed program and the developed program the
same program. The `sdist-wheel-import` workflow now resolves a recipe from a
wheel installed into a clean venv, which is the only place this can be checked
honestly.

## Adding a recipe

1. Drop `<name>.def` in this directory.
2. Register it in `_cli/install.py:_SUB_TOOLS` — that dict is the single source
   of truth, and adding a key lights up the CLI choice and the tests together.
3. Do not add a path anywhere. If you find yourself writing one, this README is
   the bug report.

## What is NOT here

`scripts/containers/` still holds the repository's own build artifacts —
`Dockerfile`, `Dockerfile.gui`, `docker-compose.gui.yml`, `scitex-writer.def`.
Those build *this project*; they are run by maintainers from a checkout and have
no reason to travel in the wheel. The split is by audience, not by file type:
data the installed CLI reads lives here, and things you run from a clone live
there.
