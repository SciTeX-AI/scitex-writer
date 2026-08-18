"""Canonical MCP server entry — re-exports from scitex_writer._mcp._server.

The ecosystem-wide audit (`scitex-dev ecosystem audit-mcp-tools`) probes
`<pkg>._mcp_server.mcp` to find each peer's FastMCP instance, so this
module must stay at the package root under this exact name.

The implementation lives in `scitex_writer._mcp._server`, next to the tools
it registers. It sat flat at `scitex_writer._server` until 2026-08-18, when
PS-108b (flat .py files at the package root over threshold) made the pair
worth tidying: two root-level files for one MCP server, one of which was
only a shim. Grouping the implementation with `_mcp/` is the topical move
the rule asks for, and it leaves exactly one MCP entry point at the root.
"""

from __future__ import annotations

from ._mcp._server import mcp, run_server

__all__ = ["mcp", "run_server"]
