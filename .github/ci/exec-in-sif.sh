#!/usr/bin/env bash
# Outer apptainer-exec wrapper for scitex-tex's self-hosted (Spartan) CI.
#
# Runs ON THE RUNNER (outside the SIF). Resolves the apptainer shim + SIF image
# from the repo Actions Variables, then `apptainer exec`s the SIF and hands off
# to an INNER script (run inside the container). Keeps every workflow job's YAML
# down to one line — `bash .github/ci/exec-in-sif.sh <inner-script> [args...]` —
# and concentrates all the HPC/SIF plumbing (shim PATH, ~-expansion, scratch,
# binds) in one version-controlled place.
#
# Required env (set by the workflow from repo Actions Variables):
#   SCITEX_CI_APPTAINER   path to the apptainer shim   (e.g. ~/.env-3.11/bin/apptainer)
#   SCITEX_CI_SIF         path to the CI SIF image     (e.g. ~/.scitex/dev/containers/ci-cpu.sif)
#
# Usage:
#   bash .github/ci/exec-in-sif.sh run-in-sif.sh 3.12
#
# Fail-loud (operator directive): a missing shim or SIF is a HARD error — never
# a silent fallback to a bare-runner install.
set -euo pipefail

INNER="${1:?inner script name required (relative to .github/ci/)}"
shift || true

# The runner's job shell is --noprofile --norc (no Lmod), so the apptainer shim
# must be put on PATH explicitly; it execs the real Apptainer binary directly.
# ~-expand the Actions-Variable paths: a quoted "~/…" is NOT tilde-expanded by
# the shell, so substitute a leading ~ with $HOME ourselves.
APPTAINER="${SCITEX_CI_APPTAINER:?SCITEX_CI_APPTAINER not set (repo Actions Variable)}"
SIF="${SCITEX_CI_SIF:?SCITEX_CI_SIF not set (repo Actions Variable)}"
APPTAINER="${APPTAINER/#\~/$HOME}"
SIF="${SIF/#\~/$HOME}"
export PATH="$HOME/.env-3.11/bin:$PATH"

[ -x "$APPTAINER" ] || {
    echo "::error::apptainer shim not executable at $APPTAINER"
    exit 1
}
[ -f "$SIF" ] || {
    echo "::error::CI SIF missing at $SIF — rebuild it: scitex-container apptainer build ci-cpu"
    exit 1
}

# THIS SCRIPT IS SPARTAN-ONLY, and the next two guards are what say so out loud.
#
# The GPFS project root below is not a preference, it is a hard requirement: it
# holds the apptainer scratch AND is bind-mounted so that $HOME/.scitex (a
# symlink into it) resolves inside the container. On a host without it, this
# script cannot work at all.
#
# WHY THE CHECK EXISTS (measured 2026-08-18, release v2.42.0). The repo variable
# CI_RUNS_ON had been repointed from the Spartan pool to `scitex-org-cpu`. Those
# runners are perfectly healthy and carry a valid label — they simply do not
# have this filesystem. Every job died here with
#
#     mkdir: cannot create directory '/data': Permission denied
#
# because `mkdir -p` on an absent GPFS root walks up and tries to create /data
# at the filesystem root. That message names a permission problem at a path
# nobody configured, on a run whose actual fault was "wrong pool", and it cost
# two failed releases to read. The shim guard above had already fired first for
# the same underlying reason and sent me chasing a stale path instead.
#
# So: check the bind root BEFORE using it, and name the real cause. A wrong
# runner pool must announce itself as a wrong runner pool.
GPFS_ROOT="/data/gpfs/projects/punim0264"
[ -d "$GPFS_ROOT" ] || {
    echo "::error::$GPFS_ROOT is not present on this runner ($(hostname)), so the CI SIF cannot be exec'd here. This workflow is Spartan-only: it binds that GPFS root and puts apptainer scratch inside it. Set the repo Actions Variable CI_RUNS_ON to the Spartan pool ('[\"self-hosted\",\"Linux\",\"X64\",\"scitex-ci\"]') — a healthy runner from another pool will still fail here, because the fault is the filesystem, not the machine."
    exit 1
}

# apptainer scratch on the shared FS — keeps HOME clean.
export APPTAINER_TMPDIR="$GPFS_ROOT/ywatanabe/ci/apptainer-tmp"
mkdir -p "$APPTAINER_TMPDIR" || {
    echo "::error::cannot create apptainer scratch at $APPTAINER_TMPDIR — $GPFS_ROOT exists but is not writable by $(whoami) on $(hostname)."
    exit 1
}

# --bind punim0264: $HOME/.scitex is a symlink into punim0264; bind it so the
# symlink resolves inside the container. --pwd "$PWD" keeps the checkout as cwd.
exec "$APPTAINER" exec --pwd "$PWD" --bind "$GPFS_ROOT" \
    "$SIF" bash ".github/ci/$INNER" "$@"
