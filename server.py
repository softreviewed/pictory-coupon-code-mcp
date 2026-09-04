#!/usr/bin/env python
"""Pictory MCP Server - Stdio/SSE Entrypoint."""
from pictory_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
