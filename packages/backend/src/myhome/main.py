from pathlib import Path
from fastapi import FastAPI
from .routes import house, svg, ha

app = FastAPI(title="MyHome Backend", version="0.1.0")
app.include_router(house.router)
app.include_router(svg.router)
app.include_router(ha.router)

# Serve built Svelte frontend (only present in production Docker image)
_static_dir = Path(__file__).parent.parent.parent / "static"
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
