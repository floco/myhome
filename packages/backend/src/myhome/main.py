import os
from pathlib import Path
from fastapi import FastAPI
from .routes import house, svg, ha, chores, inventory, settings, costs

app = FastAPI(title="MyHome Backend", version="0.1.0")
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)
app.include_router(chores.router)
app.include_router(inventory.router)
app.include_router(settings.router)
app.include_router(costs.router)

# Serve built Svelte frontend (only present in production Docker image).
# Path is explicit so it works whether myhome is installed into site-packages or run from source.
_static_dir = Path(os.environ.get("STATIC_DIR", "/app/static"))
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
