"""Registers all MCP tool modules on the shared FastMCP instance (mcp_server.mcp)
and builds the Streamable HTTP ASGI app. Imported exactly once, from main.py, so
tool registration happens before the app is built."""
from . import (  # noqa: F401 - imported for the side effect of registering tools
    mcp_tools_build,
    mcp_tools_chores,
    mcp_tools_consumables,
    mcp_tools_costs,
    mcp_tools_homes,
    mcp_tools_inventory,
    mcp_tools_kb,
    mcp_tools_locations,
    mcp_tools_properties,
    mcp_tools_settings,
    mcp_tools_works,
)
from .mcp_server import mcp

mcp_asgi_app = mcp.streamable_http_app()
