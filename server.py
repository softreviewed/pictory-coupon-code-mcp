#!/usr/bin/env python
"""Pictory MCP Server - Stdio/SSE Entrypoint."""
import os
import sys
import warnings
import logging

warnings.filterwarnings("ignore")
os.environ["FASTMCP_SHOW_BANNER"] = "false"
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logging.getLogger("docket").setLevel(logging.ERROR)

from pictory_mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
