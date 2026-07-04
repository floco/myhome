from fastapi import APIRouter

from ..deps import require_auth
from ..models_mcp import McpConfig
from ..persistence_mcp import load_mcp_config, save_mcp_config

router = APIRouter()


@router.get("/api/mcp/config", response_model=McpConfig)
def get_mcp_config(current_user: tuple[str, str] = require_auth("admin")) -> McpConfig:
    return load_mcp_config()


@router.put("/api/mcp/config", response_model=McpConfig)
def put_mcp_config(body: McpConfig, current_user: tuple[str, str] = require_auth("admin")) -> McpConfig:
    save_mcp_config(body)
    return body
